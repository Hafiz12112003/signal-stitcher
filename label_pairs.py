"""
Step 4a: label signal pairs by hand. This is the answer key we use to measure
how good the clustering is.

    python label_pairs.py

It builds about 55 GitHub-vs-Play pairs (once), shows them one by one, and saves
each answer straight away to data/labels.jsonl. You can quit any time (q) and
continue later; answered pairs are not shown again.

THE RULE for answering:
    y = both describe the SAME specific problem, so one developer fix would solve both
        e.g. "auto upload stopped working"  +  "camera upload doesn't run in background"
    n = different problems, even if they are in the same area
        e.g. "auto upload stopped working"  +  "upload is slow for big files"
    s = skip (unclear, or one of them is not about a real problem)

Pairs come from four pools, shuffled, with no hint about which is which:
  15 most similar by embeddings, 15 most similar by TF-IDF,
  15 medium-similar (hard cases), 10 random.
"""
import json
import os
import random
import sys

import numpy as np

import cluster

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

PAIRS_FILE = "data/pairs.json"
LABELS_FILE = "data/labels.jsonl"
SEED = 42


def sid(signal):
    return f"{signal['source']}:{signal['source_id']}"


def build_pairs(signals, emb, tfidf):
    gh = [i for i, s in enumerate(signals) if s["source"] == "github_issues"]
    pl = [i for i, s in enumerate(signals) if s["source"] == "play_reviews"]
    rng = random.Random(SEED)
    seen, pairs = set(), []

    def add(i, j):
        if (i, j) in seen:
            return False
        seen.add((i, j))
        pairs.append((i, j))
        return True

    def ranked(vectors):
        sims = vectors[gh] @ vectors[pl].T
        order = np.argsort(sims, axis=None)[::-1]
        return [(gh[int(f) // len(pl)], pl[int(f) % len(pl)]) for f in order]

    emb_ranked = ranked(emb)
    # pool 1 and 2: most similar pairs according to each method
    for ranking in (emb_ranked, ranked(tfidf)):
        taken = 0
        for i, j in ranking:
            if add(i, j):
                taken += 1
            if taken >= 15:
                break
    # pool 3: medium similarity (ranks 200-800), the hard cases
    medium = emb_ranked[200:800]
    rng.shuffle(medium)
    taken = 0
    for i, j in medium:
        if add(i, j):
            taken += 1
        if taken >= 15:
            break
    # pool 4: random pairs
    taken = 0
    while taken < 10:
        if add(rng.choice(gh), rng.choice(pl)):
            taken += 1

    rng.shuffle(pairs)
    return [[sid(signals[i]), sid(signals[j])] for i, j in pairs]


def show(label, signal):
    stars = f" {signal['rating']}*" if signal["rating"] else ""
    print(f"  {label} [{signal['source']}{stars}]")
    print("    " + signal["clean_text"][:350].replace("\n", " | "))


def main():
    signals = cluster.load_signals()
    by_id = {sid(s): s for s in signals}

    if os.path.exists(PAIRS_FILE):
        pairs = json.load(open(PAIRS_FILE, encoding="utf-8"))
    else:
        texts = [s["clean_text"] for s in signals]
        pairs = build_pairs(signals, cluster.embed_texts(texts), cluster.tfidf_vectors(texts))
        json.dump(pairs, open(PAIRS_FILE, "w", encoding="utf-8"))
        print(f"Built {len(pairs)} pairs -> {PAIRS_FILE}")

    done = set()
    if os.path.exists(LABELS_FILE):
        done = {(r["a"], r["b"]) for r in map(json.loads, open(LABELS_FILE, encoding="utf-8"))}
    todo = [p for p in pairs if tuple(p) not in done]
    print(f"{len(done)} labeled, {len(todo)} to go.  y = same problem, n = different, s = skip, q = quit\n")

    for n, (a, b) in enumerate(todo, 1):
        print(f"--- pair {len(done) + n} of {len(pairs)} ---")
        show("A", by_id[a])
        show("B", by_id[b])
        while True:
            answer = input("Same specific problem? [y/n/s/q]: ").strip().lower()
            if answer in ("y", "n", "s", "q"):
                break
        if answer == "q":
            break
        with open(LABELS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"a": a, "b": b, "label": answer}) + "\n")
        print()
    print("Saved. Run again any time to continue.")


if __name__ == "__main__":
    main()
