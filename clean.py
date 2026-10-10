"""
Step 2: clean the collected signals.

    python clean.py

Reads  data/signals.jsonl
Writes data/clean.jsonl   (every signal, with: clean_text, keep, drop_reason)

Nothing is deleted. Dropped signals stay in the file with a reason, so every
cleaning choice can be checked later.

Rules (all easy to change at the top of the file):
  GitHub : remove issue-template boilerplate, keep title + first 1000 chars,
           drop internal tasks (technical debt, release trackers) and issues
           with almost no text.
           Boilerplate is found automatically: any line that appears (apart from
           digits) in BOILERPLATE_MIN_ISSUES or more issues is a template line.
  Play   : keep only 1-3 star reviews with at least 15 characters.
           Short praise like "ok" / "nice" tells us nothing about problems.
"""
import json
import re
import sys
from collections import Counter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

IN_FILE = "data/signals.jsonl"
OUT_FILE = "data/clean.jsonl"

MAX_CHARS = 1000
MIN_CHARS = 20            # GitHub: cleaned text shorter than this is dropped
MIN_PLAY_CHARS = 15       # Play: shorter reviews are dropped
MAX_PLAY_RATING = 3       # Play: only 1-3 star reviews describe problems
DROP_LABELS = {"technical debt"}   # internal developer tasks, not customer feedback
BOILERPLATE_MIN_ISSUES = 6         # a line seen in this many issues is template text

HTML_COMMENT = re.compile(r"<!--.*?-->", re.S)
CODE_BLOCK = re.compile(r"```.*?```", re.S)
URL = re.compile(r"https?://\S+")
IMAGE = re.compile(r"!\[.*?\]\(.*?\)")
HTML_TAG = re.compile(r"<[^>]+>")      # leftover <img ...> and similar tags
RELEASE_TITLE = re.compile(r"^\s*release\s+v?\d", re.I)   # maintainer release-tracking issues
# Device-info bullets from the bug template: "* Brand: `Xiaomi`", "* SDK: 33", ... (values differ
# per issue, so repetition-based removal cannot catch them)
DEVICE_LINE = re.compile(
    r"^[-*]\s*(id|version|build flavor|brand|device|model|product|sdk|release|incremental|"
    r"hardware|fingerprint|board|manufacturer)\s*:", re.I)


def body_lines(text: str):
    """Split a GitHub signal into (title, list of cleaned body lines)."""
    title, _, body = text.partition("\n\n")
    body = HTML_COMMENT.sub(" ", body)
    body = CODE_BLOCK.sub(" ", body)      # logs and stack traces
    body = IMAGE.sub(" ", body)
    body = HTML_TAG.sub(" ", body)        # must run before URLs, tags can contain URLs
    body = URL.sub(" ", body)
    lines = []
    for line in body.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):                          # template headings
            continue
        if re.match(r"^[-*]\s*\[[ xX]\]", s):          # template checkboxes
            continue
        if DEVICE_LINE.match(s):                       # device-info block
            continue
        lines.append(s)
    return title.strip(), lines


def normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"\d+", "#", line.lower())).strip()


def find_boilerplate(rows):
    """Lines that repeat across many different issues are template text."""
    counts = Counter()
    for r in rows:
        if r["source"] != "github_issues":
            continue
        _, lines = body_lines(r["text"])
        counts.update({normalize_line(l) for l in lines})   # set: count once per issue
    return {line for line, n in counts.items() if n >= BOILERPLATE_MIN_ISSUES}, counts


def decide(signal: dict, boilerplate: set):
    """Return (clean_text, keep, drop_reason)."""
    if signal["source"] == "github_issues":
        title, lines = body_lines(signal["text"])
        lines = [l for l in lines if normalize_line(l) not in boilerplate]
        text = (title + "\n" + " ".join(lines)).strip()[:MAX_CHARS]
        if RELEASE_TITLE.match(title):
            return text, False, "release tracker"
        if DROP_LABELS & set(signal["labels"]):
            return text, False, "internal task"
        if len(text) < MIN_CHARS:
            return text, False, "too short"
        return text, True, ""

    if signal["source"] == "play_reviews":
        text = " ".join(signal["text"].split())
        if signal["rating"] is not None and signal["rating"] > MAX_PLAY_RATING:
            return text, False, "4-5 star review"
        if len(text) < MIN_PLAY_CHARS:
            return text, False, "too short"
        return text, True, ""

    return signal["text"], True, ""   # unknown source: keep as is


def main():
    rows = [json.loads(line) for line in open(IN_FILE, encoding="utf-8")]
    boilerplate, counts = find_boilerplate(rows)
    kept = Counter()
    dropped = Counter()
    with open(OUT_FILE, "w", encoding="utf-8") as out:
        for r in rows:
            text, keep, reason = decide(r, boilerplate)
            r["clean_text"] = text
            r["keep"] = keep
            r["drop_reason"] = reason
            out.write(json.dumps(r) + "\n")
            if keep:
                kept[r["source"]] += 1
            else:
                dropped[(r["source"], reason)] += 1

    print(f"Read {len(rows)} signals -> kept {sum(kept.values())}\n")
    for source, n in kept.items():
        print(f"  kept    {source}: {n}")
    for (source, reason), n in dropped.items():
        print(f"  dropped {source}: {n}  ({reason})")

    print(f"\nTemplate lines removed automatically: {len(boilerplate)}  (most common, check they are really boilerplate)")
    for line in sorted(boilerplate, key=lambda l: -counts[l])[:8]:
        print(f"  {counts[line]:>3} issues: {line[:90]!r}")

    print("\nSample cleaned GitHub issues (check they still make sense):")
    shown = 0
    for line in open(OUT_FILE, encoding="utf-8"):
        r = json.loads(line)
        if r["source"] == "github_issues" and r["keep"]:
            print("  -", repr(r["clean_text"][:160]))
            shown += 1
            if shown == 4:
                break
    print(f"\nWrote {OUT_FILE}")


if __name__ == "__main__":
    main()
