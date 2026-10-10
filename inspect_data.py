"""
Step 2: look at the data before building on it.

    python inspect_data.py

Prints, per source: how many signals, date range, text length, the shortest
texts (junk check), and how many mention sync/upload words (to check that our
demo theme really exists in the data).
"""
import json
import re
import sys
from collections import Counter, defaultdict
from statistics import median

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

DATA_FILE = "data/signals.jsonl"
THEME_WORDS = re.compile(r"\b(sync|syncing|auto.?upload|upload|uploads|background)\b", re.I)

rows = [json.loads(line) for line in open(DATA_FILE, encoding="utf-8")]
by_source = defaultdict(list)
for r in rows:
    by_source[r["source"]].append(r)

print(f"TOTAL signals: {len(rows)}\n")

for source, items in by_source.items():
    dates = sorted(i["created_at"] for i in items)
    lengths = [len(i["text"]) for i in items]
    mentions = sum(1 for i in items if THEME_WORDS.search(i["text"]))
    non_ascii = sum(1 for i in items if sum(c.isascii() for c in i["text"]) < 0.7 * max(len(i["text"]), 1))

    print("=" * 60)
    print(f"{source}: {len(items)} signals")
    print(f"  date range : {dates[0][:10]}  ->  {dates[-1][:10]}")
    print(f"  text length: median {int(median(lengths))} chars, shortest {min(lengths)}, longest {max(lengths)}")
    print(f"  mention sync/upload/background words: {mentions} ({100 * mentions // len(items)}%)")
    print(f"  probably not English: {non_ascii}")

    if source == "play_reviews":
        ratings = Counter(i["rating"] for i in items)
        print("  ratings    :", dict(sorted(ratings.items())))
    if source == "github_issues":
        labels = Counter(label for i in items for label in i["labels"])
        print("  top labels :", labels.most_common(6))

    print("  5 shortest texts (junk check):")
    for i in sorted(items, key=lambda x: len(x["text"]))[:5]:
        print("    -", repr(i["text"][:80]))
    print()
