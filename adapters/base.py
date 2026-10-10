"""
The two things every source must follow.

1. Signal  - the one common shape all feedback is converted into.
2. Adapter - the interface a source implements. To add a new source,
             write ONE file with a class that has fetch() and normalize().
             Nothing else in the project needs to change.
"""
import hashlib
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Iterator, List, Optional


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Signal:
    source: str          # "github_issues", "play_reviews", ...
    source_id: str       # the id used by the original source
    account: str         # which product this is about, e.g. "nextcloud/android"
    url: str             # link back to the original (our "evidence")
    author: str
    text: str            # what the customer actually said
    created_at: str      # when they said it (ISO 8601, UTC)
    ingested_at: str     # when we read it
    rating: Optional[int] = None   # stars, if the source has them
    engagement: int = 0            # likes / reactions / comments
    labels: List[str] = field(default_factory=list)
    content_hash: str = ""         # used to drop repeated text

    def __post_init__(self):
        self.text = (self.text or "").strip()[:4000]
        if not self.content_hash:
            normalized = " ".join(self.text.lower().split())
            self.content_hash = hashlib.sha1(normalized.encode()).hexdigest()

    def to_dict(self) -> dict:
        return asdict(self)


class Adapter(ABC):
    name: str = ""       # source name, e.g. "github_issues"
    account: str = ""    # product being collected, e.g. "nextcloud/android"

    @abstractmethod
    def fetch(self, since: Optional[str], limit: int) -> Iterator[dict]:
        """Yield raw records from the source, newest first.
        `since` is an ISO timestamp: only return things newer than it (or None)."""

    @abstractmethod
    def normalize(self, raw: dict) -> Optional[Signal]:
        """Turn one raw record into a Signal. Return None to skip it."""
