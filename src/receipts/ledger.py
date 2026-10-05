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
        """Record a page whose text the caller already holds (a tool result, a file, a test).

        A page read again with different text gets an id of its own. The earlier text stays, so a claim
        written against it is still checked against what it quoted.
        """
        digest = hashlib.sha256(text.encode()).hexdigest()
        key = "e" + hashlib.sha256(url.encode()).hexdigest()[:8]
        earlier = self._items.get(key)
        if earlier is not None and earlier.sha256 != digest:
            key = f"{key}.{digest[:6]}"
        when = fetched_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
        ev = Evidence(id=key, url=url, text=text, title=title, fetched_at=when, sha256=digest)
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
        """Read a ledger from a JSON file written by `save`.

        Each page must carry a hash and its text must still match it: a page with the hash removed is
        refused like one with the text changed. That catches a file edited by hand or damaged. It does
        not make the file evidence: whoever can edit the text can edit the hash, so a ledger file is
        trusted input, like the code that reads it.
        """
        raw = json.loads(Path(path).read_text())
        fields = ("id", "url", "text", "title", "fetched_at", "sha256")
        if not isinstance(raw, list) or not all(isinstance(e, dict) for e in raw):
            raise ValueError(f"{path}: not a ledger: expected a list of pages, each with id, url, text and sha256")
        items = []
        for e in raw:
            page = {k: e.get(k, "") for k in fields}  # fields this version does not know are left alone
            if not all(isinstance(v, str) for v in page.values()) or not page["id"] or "text" not in e:
                raise ValueError(f"{path}: not a ledger: a page needs an id and its text, and every field is text")
            if not page["sha256"]:
                raise ValueError(f"{path}: {page['url'] or page['id']} has no hash, so its text cannot be checked")
            if hashlib.sha256(page["text"].encode()).hexdigest() != page["sha256"]:
                raise ValueError(
                    f"{path}: the text of {page['url']} no longer matches its hash; it changed after the fetch"
                )
            items.append(Evidence(**page))
        return cls(items)
