"""
Step 5a: export the themes and their evidence for the web viewer.

    python export_viewer_data.py

Reads  data/themes_embeddings.json   (from cluster.py)
       data/clean.jsonl              (the signal texts)
Writes viewer/public/data.json       (what the viewer loads)
"""
import json
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # avoids Windows console errors

THEMES_FILE = "data/themes_embeddings.json"
CLEAN_FILE = "data/clean.jsonl"
OUT_FILE = "viewer/public/data.json"
MAX_TEXT = 600


def sid(row):
    return f"{row['source']}:{row['source_id']}"


def example_from(quote):
    """One readable line: the issue title, or the first sentence of the review."""
    text = quote["text"].strip()
    if quote["source"] == "github_issues":
        line = text.split("\n")[0]
    else:
        line = re.split(r"(?<=[.!?])\s|\n", text)[0]
    line = line.strip()
    return line if len(line) <= 90 else line[:87].rstrip() + "..."


def main():
    themes_data = json.load(open(THEMES_FILE, encoding="utf-8"))
    by_id = {}
    for line in open(CLEAN_FILE, encoding="utf-8"):
        row = json.loads(line)
        by_id[sid(row)] = row

    themes = []
    for t in themes_data["themes"]:
        featured_urls = {q["url"] for q in t["quotes"]}
        members = []
        for signal_id in t["signal_ids"]:
            row = by_id[signal_id]
            members.append({
                "id": signal_id,
                "source": row["source"],
                "rating": row["rating"],
                "url": row["url"],
                "created_at": row["created_at"],
                "text": row["clean_text"][:MAX_TEXT],
                "featured": row["url"] in featured_urls,
            })
        dates = sorted(m["created_at"] for m in members)
        themes.append({
            "theme_id": t["theme_id"],
            "title": " / ".join(t["keywords"][:3]),
            "example": example_from(t["quotes"][0]),
            "size": t["size"],
            "sources": t["sources"],
            "keywords": t["keywords"],
            "date_first": dates[0],
            "date_last": dates[-1],
            "members": members,
        })

    stats = {
        "n_signals": themes_data["n_signals"],
        "n_themes": themes_data["n_themes"],
        "n_clustered": themes_data["n_clustered"],
        "n_unclustered": themes_data["n_unclustered"],
        "cross_source_themes": sum(1 for t in themes if len(t["sources"]) > 1),
        "method": themes_data["method"],
        "threshold": themes_data["threshold"],
    }

    os.makedirs(os.path.dirname(OUT_FILE), exist_ok=True)
    json.dump({"stats": stats, "themes": themes}, open(OUT_FILE, "w", encoding="utf-8"))
    print(f"Wrote {OUT_FILE}: {len(themes)} themes, {sum(len(t['members']) for t in themes)} signals")


if __name__ == "__main__":
    main()
