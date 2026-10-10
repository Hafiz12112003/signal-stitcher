"""
Step 3: group related signals into themes.

    python cluster.py                       # embeddings method (main)
    python cluster.py --method tfidf        # word-count baseline (for comparison later)
    python cluster.py --threshold 0.50      # tune: lower = tighter, more clusters
    python cluster.py --max-size 40         # split any theme bigger than this

Reads  data/clean.jsonl           (only rows with keep = true)
Writes data/themes_<method>.json  (themes with size, sources, keywords, evidence quotes)

How it works
  1. Turn every text into a vector (embeddings, or TF-IDF for the baseline).
  2. Group vectors whose cosine distance is below the threshold (agglomerative clustering).
  3. A group bigger than MAX_THEME_SIZE is split again with a tighter threshold,
     so one giant "everything about upload" theme becomes several specific ones.
  4. A group with at least MIN_THEME_SIZE signals becomes a theme; the rest stay unclustered.
  5. For each theme: top keywords + the 3 signals closest to its centre as evidence.
"""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter

import numpy as np
from sklearn.cluster import AgglomerativeClustering
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.preprocessing import normalize

# Words that appear in almost every theme of this dataset and say nothing about the problem.
# Only used for theme keywords and titles, never for the grouping itself.
KEYWORD_STOPWORDS = {
    "nextcloud", "app", "apps", "android", "file", "files", "phone", "doesn", "don", "didn",
    "isn", "just", "like", "use", "using", "com", "org", "http", "https", "www", "ve",
}

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

IN_FILE = "data/clean.jsonl"
MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"   # handles English + German + many more
MIN_THEME_SIZE = 3
MAX_THEME_SIZE = 50
DEFAULT_THRESHOLD = {"embeddings": 0.55, "tfidf": 0.85}


def load_signals():
    rows = [json.loads(line) for line in open(IN_FILE, encoding="utf-8")]
    return [r for r in rows if r["keep"]]


def embedding_texts(signals, text_mode="full"):
    """The text we turn into vectors. 'title' uses only the first line of GitHub issues."""
    texts = []
    for s in signals:
        text = s["clean_text"]
        if text_mode == "title" and s["source"] == "github_issues":
            text = text.split("\n")[0]
        texts.append(text)
    return texts


def embed_texts(texts):
    """Sentence embeddings. Cached on disk so reruns are instant."""
    key = hashlib.sha1("\n".join(texts).encode()).hexdigest()[:12]
    cache = f"data/embeddings_{key}.npy"
    if os.path.exists(cache):
        print(f"Using cached embeddings ({cache})")
        return np.load(cache)
    from sentence_transformers import SentenceTransformer   # imported here so tfidf works without it
    print(f"Loading model {MODEL_NAME} ...")
    model = SentenceTransformer(MODEL_NAME)
    vectors = model.encode(texts, batch_size=32, show_progress_bar=True, normalize_embeddings=True)
    np.save(cache, vectors)
    return vectors


def tfidf_vectors(texts):
    vec = TfidfVectorizer(stop_words="english", min_df=2, sublinear_tf=True, ngram_range=(1, 2))
    return normalize(vec.fit_transform(texts)).toarray()


def cluster_vectors(vectors, threshold):
    model = AgglomerativeClustering(
        n_clusters=None, distance_threshold=threshold, metric="cosine", linkage="average"
    )
    return model.fit_predict(vectors)


def group_signals(vectors, threshold, max_size):
    """Cluster, then keep splitting any group that is bigger than max_size."""
    first = cluster_vectors(vectors, threshold)
    initial = {}
    for idx, label in enumerate(first):
        initial.setdefault(label, []).append(idx)

    done = []
    queue = [(members, threshold) for members in initial.values()]
    while queue:
        members, thr = queue.pop()
        if len(members) <= max_size or thr < 0.15:
            done.append(members)
            continue
        tighter = thr * 0.85
        labels = cluster_vectors(vectors[members], tighter)
        parts = {}
        for idx, label in zip(members, labels):
            parts.setdefault(label, []).append(idx)
        queue.extend((part, tighter) for part in parts.values())   # if nothing split, tries tighter again
    return done


def build_themes(signals, vectors, groups):
    # Keywords: terms that are strong inside a cluster (plain English stop words removed).
    kw_vec = TfidfVectorizer(stop_words=list(ENGLISH_STOP_WORDS | KEYWORD_STOPWORDS), min_df=2, sublinear_tf=True)
    kw_matrix = kw_vec.fit_transform([s["clean_text"] for s in signals])
    terms = np.array(kw_vec.get_feature_names_out())

    themes = []
    for members in groups:
        if len(members) < MIN_THEME_SIZE:
            continue
        centre = vectors[members].mean(axis=0)
        distance = 1 - normalize(vectors[members]) @ (centre / (np.linalg.norm(centre) + 1e-9))
        closest = [members[i] for i in np.argsort(distance)[:3]]
        mean_tfidf = np.asarray(kw_matrix[members].mean(axis=0)).ravel()
        keywords = [t for t in terms[np.argsort(mean_tfidf)[::-1][:6]]]
        themes.append({
            "size": len(members),
            "sources": dict(Counter(signals[i]["source"] for i in members)),
            "keywords": keywords,
            "quotes": [{
                "source": signals[i]["source"],
                "rating": signals[i]["rating"],
                "url": signals[i]["url"],
                "text": signals[i]["clean_text"][:300],
            } for i in closest],
            "signal_ids": [f"{signals[i]['source']}:{signals[i]['source_id']}" for i in members],
        })

    themes.sort(key=lambda t: t["size"], reverse=True)
    for n, theme in enumerate(themes, 1):
        theme["theme_id"] = f"theme_{n:03d}"
    return themes


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--method", choices=["embeddings", "tfidf"], default="embeddings")
    p.add_argument("--threshold", type=float, default=None)
    p.add_argument("--max-size", type=int, default=MAX_THEME_SIZE)
    p.add_argument("--text-mode", choices=["full", "title"], default="full",
                   help="title = embed only the GitHub issue title (closer in style to short reviews)")
    args = p.parse_args()
    threshold = args.threshold or DEFAULT_THRESHOLD[args.method]

    signals = load_signals()
    texts = embedding_texts(signals, args.text_mode)
    print(f"{len(signals)} signals, method = {args.method}, text = {args.text_mode}, "
          f"threshold = {threshold}, max theme size = {args.max_size}")

    vectors = embed_texts(texts) if args.method == "embeddings" else tfidf_vectors(texts)
    groups = group_signals(vectors, threshold, args.max_size)
    themes = build_themes(signals, vectors, groups)

    clustered = sum(t["size"] for t in themes)
    cross = [t for t in themes if len(t["sources"]) > 1]
    result = {
        "method": args.method, "threshold": threshold, "max_size": args.max_size,
        "n_signals": len(signals), "n_themes": len(themes), "n_clustered": clustered,
        "n_unclustered": len(signals) - clustered, "themes": themes,
    }
    out_file = f"data/themes_{args.method}{'_title' if args.text_mode == 'title' else ''}.json"
    json.dump(result, open(out_file, "w", encoding="utf-8"), indent=2)

    print(f"\nThemes (size >= {MIN_THEME_SIZE}): {len(themes)}")
    print(f"Signals in a theme: {clustered}   unclustered: {len(signals) - clustered}")
    print(f"Themes mixing GitHub + Play: {len(cross)}\n")
    for t in themes[:15]:
        print(f"{t['theme_id']}  size {t['size']}  {t['sources']}")
        print(f"   keywords: {', '.join(t['keywords'])}")
        for q in t["quotes"][:2]:
            print(f"   - [{q['source']}] {q['text'][:110]!r}")
        print()
    print(f"Wrote {out_file}")


if __name__ == "__main__":
    main()
