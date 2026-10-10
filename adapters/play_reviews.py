"""
Google Play reviews adapter.

Google has no official public API for reading reviews, so this uses the
unofficial `google-play-scraper` library. It can break if Google changes the
page, and it is a gray area under Google's terms. Fine for a small research
demo; mention this in the README.
"""
from datetime import datetime, timezone
from typing import Iterator, Optional

from .base import Adapter, Signal, now_iso


class PlayReviewsAdapter(Adapter):
    name = "play_reviews"

    def __init__(self, app_id: str, lang: str = "en", country: str = "us"):
        self.account = app_id  # e.g. "com.nextcloud.client"
        self.lang = lang
        self.country = country

    def fetch(self, since: Optional[str], limit: int) -> Iterator[dict]:
        try:
            from google_play_scraper import Sort, reviews
        except ImportError:
            raise SystemExit("Missing package. Run: pip install -r requirements.txt")

        since_dt = datetime.fromisoformat(since) if since else None
        got = 0
        token = None
        while got < limit:
            batch, token = reviews(
                self.account,
                lang=self.lang,
                country=self.country,
                sort=Sort.NEWEST,
                count=min(200, limit - got),
                continuation_token=token,
            )
            if not batch:
                return
            for review in batch:
                created = review["at"].replace(tzinfo=timezone.utc)
                if since_dt and created <= since_dt:   # newest first, so we can stop here
                    return
                yield review
                got += 1
                if got >= limit:
                    return
            if token is None:
                return

    def normalize(self, raw: dict) -> Optional[Signal]:
        text = raw.get("content") or ""
        if not text.strip():   # star-only reviews carry no usable text
            return None
        return Signal(
            source=self.name,
            source_id=raw["reviewId"],
            account=self.account,
            url=f"https://play.google.com/store/apps/details?id={self.account}&reviewId={raw['reviewId']}",
            author=raw.get("userName") or "anonymous",
            text=text,
            created_at=raw["at"].replace(tzinfo=timezone.utc).isoformat(),
            ingested_at=now_iso(),
            rating=raw.get("score"),
            engagement=raw.get("thumbsUpCount") or 0,
        )
