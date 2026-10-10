"""
Step 4b: measure how good the clustering is, using YOUR hand labels.

    python evaluate.py

For every labeled pair (y = same problem, n = different) we ask: did the system
put both signals into the same theme?
    precision = of the pairs the system said "same", how many really were
    recall    = of the pairs that really were "same", how many the system found
    F1        = one number combining both

It compares three methods across many thresholds:
    tfidf              word-count baseline
    embeddings         sentence embeddings on the full text
    embeddings-title   sentence embeddings, GitHub issues by title only

Reads  data/clean.jsonl, data/labels.jsonl
"""
import json
import sys

import numpy as np

import cluster

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

LABELS_FILE = "data/labels.jsonl"
GRID = [round(float(x), 2) for x in np.arange(0.30, 0.96, 0.05)]


def sid(signal):
    return f"{signal['source']}:{signal['source_id']}"


def load_labels():
    rows = [json.loads(line) for line in open(LABELS_FILE, encoding="utf-8")]
    return [(r["a"], r["b"], r["label"] == "y") for r in rows if r["label"] in ("y", "n")]


def assignment(signals, vectors, threshold):
    """signal id -> theme number, only for groups big enough to count as a theme."""
    groups = cluster.group_signals(vectors, threshold, cluster.MAX_THEME_SIZE)
    mapping = {}
    for gid, members in enumerate(groups):
        if len(members) >= cluster.MIN_THEME_SIZE:
            for i in members:
                mapping[sid(signals[i])] = gid
    return mapping, sum(1 for g in groups if len(g) >= cluster.MIN_THEME_SIZE)


def score(labeled, mapping):
    tp = fp = fn = tn = 0
    for a, b, truth in labeled:
        predicted = a in mapping and b in mapping and mapping[a] == mapping[b]
        if truth and predicted:
            tp += 1
        elif truth:
            fn += 1
        elif predicted:
            fp += 1
        else:
            tn += 1
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return precision, recall, f1, (tp, fp, fn, tn)


def main():
    signals = cluster.load_signals()
    present = {sid(s) for s in signals}
    everything = load_labels()
    labeled = [(a, b, t) for a, b, t in everything if a in present and b in present]
    if len(labeled) < len(everything):
        print(f"Skipped {len(everything) - len(labeled)} labeled pairs whose signals cleaning dropped.")
    yes = sum(1 for _, _, t in labeled if t)
    print(f"Labeled pairs used: {len(labeled)}  (same: {yes}, different: {len(labeled) - yes})")
    if len(labeled) < 30 or yes < 8:
        print("WARNING: very few labels, so these numbers are rough. Label more pairs for a stronger result.\n")

    methods = {
        "tfidf": cluster.tfidf_vectors(cluster.embedding_texts(signals, "full")),
        "embeddings": cluster.embed_texts(cluster.embedding_texts(signals, "full")),
        "embeddings-title": cluster.embed_texts(cluster.embedding_texts(signals, "title")),
    }

    best = {}
    for name, vectors in methods.items():
        print(f"\n{name}")
        print("  threshold  themes  precision  recall    F1")
        for thr in GRID:
            mapping, n_themes = assignment(signals, vectors, thr)
            p, r, f1, _ = score(labeled, mapping)
            print(f"  {thr:>9.2f}  {n_themes:>6}  {p:>9.2f}  {r:>6.2f}  {f1:>4.2f}")
            if name not in best or f1 > best[name][0]:
                best[name] = (f1, thr, p, r)

    print("\n=== Best threshold per method (chosen on these same labels, so slightly optimistic) ===")
    for name, (f1, thr, p, r) in sorted(best.items(), key=lambda kv: -kv[1][0]):
        print(f"  {name:<18} F1 {f1:.2f}   precision {p:.2f}   recall {r:.2f}   at threshold {thr}")

    winner = max(best, key=lambda n: best[n][0])
    mapping, _ = assignment(signals, methods[winner], best[winner][1])
    by_id = {sid(s): s for s in signals}
    missed = [(a, b) for a, b, t in labeled if t and not (a in mapping and b in mapping and mapping[a] == mapping[b])]
    wrong = [(a, b) for a, b, t in labeled if not t and a in mapping and b in mapping and mapping[a] == mapping[b]]
    for title, pairs in (("Pairs you said SAME but the system split (misses)", missed),
                         ("Pairs you said DIFFERENT but the system joined (false joins)", wrong)):
        print(f"\n{title} [{winner}]: {len(pairs)}")
        for a, b in pairs[:3]:
            print("  A:", by_id[a]["clean_text"][:130].replace("\n", " | "))
            print("  B:", by_id[b]["clean_text"][:130].replace("\n", " | "))
            print()
    print("Note: the pairs were picked from similar-looking pools plus random ones, so recall here")
    print("means 'among these labeled pairs', not 'among all possible pairs'. Say so in the README.")


if __name__ == "__main__":
    main()
