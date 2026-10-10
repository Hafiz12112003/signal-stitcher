"""
Step 1 runner: collect signals from every adapter into one file.

    python collect.py

Output:  data/signals.jsonl   (one Signal per line)
State:   data/state.json      (remembers the last run, so reruns only fetch new items)
"""
import argparse
import json
import os
from typing import List

from adapters.base import Adapter, now_iso
from adapters.github_issues import GitHubIssuesAdapter
from adapters.play_reviews import PlayReviewsAdapter

OUT_FILE = "data/signals.jsonl"
STATE_FILE = "data/state.json"


def run(adapters: List[Adapter], out_file: str = OUT_FILE, state_file: str = STATE_FILE, limit: dict = None):
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    state = json.load(open(state_file)) if os.path.exists(state_file) else {}
    limit = limit or {}

    # Load what we already have so reruns never create duplicates.
    seen_ids, seen_hashes = set(), set()
    if os.path.exists(out_file):
        for line in open(out_file):
            s = json.loads(line)
            seen_ids.add((s["source"], s["source_id"]))
            seen_hashes.add((s["source"], s["content_hash"]))

    with open(out_file, "a") as out:
        for adapter in adapters:
            key = f"{adapter.name}:{adapter.account}"
            run_started = now_iso()
            added = skipped = 0
            print(f"[{key}] collecting (since {state.get(key, 'the beginning')})")
            for raw in adapter.fetch(state.get(key), limit.get(adapter.name, 200)):
                signal = adapter.normalize(raw)
                if signal is None:
                    skipped += 1
                    continue
                id_key = (signal.source, signal.source_id)
                hash_key = (signal.source, signal.content_hash)
                if id_key in seen_ids or hash_key in seen_hashes:   # same id or same text: drop
                    skipped += 1
                    continue
                seen_ids.add(id_key)
                seen_hashes.add(hash_key)
                out.write(json.dumps(signal.to_dict()) + "\n")
                added += 1
            state[key] = run_started
            print(f"[{key}] added {added}, skipped {skipped}")

    json.dump(state, open(state_file, "w"), indent=2)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--github", default="nextcloud/android", help="GitHub repo, owner/name")
    p.add_argument("--play", default="com.nextcloud.client", help="Google Play app id")
    p.add_argument("--github-limit", type=int, default=200)
    p.add_argument("--play-limit", type=int, default=300)
    args = p.parse_args()

    run(
        [GitHubIssuesAdapter(args.github), PlayReviewsAdapter(args.play)],
        limit={"github_issues": args.github_limit, "play_reviews": args.play_limit},
    )
    print("Done. Check data/signals.jsonl")
