"""The evidence ledger: every page a run read, with when it was read and a hash of what it said."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from .core import Evidence
from .fetch import fetch


class Ledger(Mapping[str, Evidence]):
    """The pages a run read, by evidence id. Reads like a mapping; pages are added by address or as text."""

    def __init__(self, items: list[Evidence] | None = None) -> None:
        self._items: dict[str, Evidence] = {e.id: e for e in items or []}

    def __getitem__(self, key: str) -> Evidence:
        return self._items[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def add_text(self, url: str, text: str, title: str = "", fetched_at: str | None = None) -> Evidence:
        """Record a page whose text the caller already holds (a tool result, a file, a test)."""
        ev = Evidence(
            id="e" + hashlib.sha256(url.encode()).hexdigest()[:8],
            url=url,
            text=text,
            title=title,
            fetched_at=fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds"),
            sha256=hashlib.sha256(text.encode()).hexdigest(),
        )
        self._items[ev.id] = ev
        return ev

    def add_url(self, url: str, **kw) -> Evidence:
        """Fetch a page and record it. Raises fetch.FetchError when it cannot be read."""
        title, text = fetch(url, **kw)
        return self.add_text(url, text, title)

    def save(self, path: str | Path) -> None:
        """Write the ledger to a JSON file."""
        Path(path).write_text(json.dumps([asdict(e) for e in self._items.values()], indent=1, ensure_ascii=False))

    @classmethod
    def load(cls, path: str | Path) -> Ledger:
        """Read a ledger from a JSON file written by `save`."""
        return cls([Evidence(**e) for e in json.loads(Path(path).read_text())])
