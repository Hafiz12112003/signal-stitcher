"""GitHub Issues adapter. Uses only the standard library."""
import json
import os
import time
import urllib.error
import urllib.request
from typing import Iterator, Optional

from .base import Adapter, Signal, now_iso


def _http_get(url: str, retries: int = 4):
    """GET with retry and backoff. Waits when GitHub says we hit the rate limit."""
    headers = {"Accept": "application/vnd.github+json", "User-Agent": "signal-stitcher"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as e:
            if e.code in (403, 429) and attempt < retries - 1:
                reset = e.headers.get("X-RateLimit-Reset")
                wait = max(int(reset) - int(time.time()), 1) if reset else 2 ** attempt * 5
                wait = min(wait, 120)
                print(f"  GitHub rate limit hit, waiting {wait}s (set GITHUB_TOKEN to avoid this)")
                time.sleep(wait)
                continue
            raise
    return []


class GitHubIssuesAdapter(Adapter):
    name = "github_issues"

    def __init__(self, repo: str):
        self.account = repo  # e.g. "nextcloud/android"

    def fetch(self, since: Optional[str], limit: int) -> Iterator[dict]:
        got = 0
        page = 1
        while got < limit:
            url = (f"https://api.github.com/repos/{self.account}/issues"
                   f"?state=all&sort=created&direction=desc&per_page=100&page={page}")
            if since:
                url += f"&since={since}"
            batch = _http_get(url)
            if not batch:
                return
            for issue in batch:
                if "pull_request" in issue:   # this endpoint also returns pull requests; skip them
                    continue
                yield issue
                got += 1
                if got >= limit:
                    return
            page += 1

    def normalize(self, raw: dict) -> Optional[Signal]:
        text = f"{raw['title']}\n\n{raw.get('body') or ''}"
        if not text.strip():
            return None
        return Signal(
            source=self.name,
            source_id=str(raw["id"]),
            account=self.account,
            url=raw["html_url"],
            author=raw["user"]["login"],
            text=text,
            created_at=raw["created_at"],
            ingested_at=now_iso(),
            engagement=raw["reactions"]["total_count"] + raw["comments"],
            labels=[label["name"] for label in raw["labels"]],
        )
