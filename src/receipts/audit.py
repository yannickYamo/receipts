"""Audit prose written by any agent: how many specifics does it state, and how many can a reader check?

This reads a finished text (a battle card, a report, a reply) and finds the specifics a pattern can see:
money, percentages, ratings, counts, dates, quotations and attributions. For each it answers two things:

  linked   does the line it sits on carry a link a reader could follow?
  traced   given the pages the agent read, do the figures appear in one passage with the line's words?

It is a floor, not a census: a plain factual sentence with no figure ("X has no mobile app") is a
specific too, and no pattern sees it. The counts say "at least this many".
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field

from .core import Evidence
from .text import content_words, html_to_text, numbers_in, passages, sentences

_MONTH = "January|February|March|April|May|June|July|August|September|October|November|December"
_NOUN = (
    "customers?|users?|employees|people|staff|companies|businesses|organizations|teams?|integrations|apps|"
    "countries|offices|seats?|agents?|partners|developers|reviews|downloads|languages|templates|"
    "years?|months?|days?|hours?|minutes?"
)
PATTERNS: dict[str, re.Pattern[str]] = {
    "MONEY": re.compile(
        r"[$€£]\s?\d[\d,.]*\s?(?:k|m|bn|b|million|billion)?\b|\b\d[\d,.]*\s?(?:USD|EUR|dollars|euros)\b", re.I
    ),
    "PERCENT": re.compile(r"\b\d+(?:\.\d+)?\s?(?:%|percent\b)", re.I),
    "RATING": re.compile(r"\b\d(?:\.\d)?\s?/\s?(?:5|10)\b|\b\d(?:\.\d)?\s?(?:out of (?:5|10)|stars?)\b", re.I),
    "COUNT": re.compile(
        rf"\b\d[\d,]*(?:\.\d+)?\+?\s?(?:k|m|million|billion|thousand)?\+?\s+(?:\w+\s)?(?:{_NOUN})\b", re.I
    ),
    "DATE": re.compile(rf"\b(?:19|20)\d\d\b|\b(?:{_MONTH})\s+\d{{1,2}}\b|\bQ[1-4]\s?(?:19|20)\d\d\b"),
    "QUOTE": re.compile(r"[\"“][^\"”\n]{25,}[\"”]"),
    "ATTRIBUTION": re.compile(
        r"\b(?:according to|G2|Gartner|Forrester|Capterra|TrustRadius|IDC|analysts?|"
        r"surveys?|stud(?:y|ies)|reviewers?|reported(?:ly)?)\b",
        re.I,
    ),
}
_LINK = re.compile(r"https?://[^\s)\]>\"']+")
_ANCHOR = re.compile(r"<a\s[^>]*href=[\"'](https?://[^\"']+)[\"'][^>]*>(.*?)</a>", re.I | re.S)


@dataclass(frozen=True)
class Specific:
    """One specific found in a text: where it sits, what kind it is, and whether a reader could check it."""

    unit: int
    kind: str
    text: str
    line: str
    linked: bool
    traced_to: str | None  # the url of the page that carries it, when pages were given


@dataclass
class Audit:
    """The specifics found in one text, with counts."""

    units: int
    specifics: list[Specific] = field(default_factory=list)
    with_sources: bool = False

    @property
    def lines_with_specifics(self) -> int:
        """How many lines state at least one specific."""
        return len({s.unit for s in self.specifics})

    @property
    def linked(self) -> int:
        """How many specifics sit in a block with a link."""
        return sum(s.linked for s in self.specifics)

    @property
    def traced(self) -> int:
        """How many specifics were found on one of the pages given."""
        return sum(s.traced_to is not None for s in self.specifics)

    def to_dict(self) -> dict:
        """The counts as plain data, for JSON."""
        kinds: dict[str, int] = {}
        for s in self.specifics:
            kinds[s.kind] = kinds.get(s.kind, 0) + 1
        return {
            "lines": self.units,
            "lines_with_specifics": self.lines_with_specifics,
            "specifics": len(self.specifics),
            "linked": self.linked,
            "traced": self.traced if self.with_sources else None,
            "by_kind": kinds,
        }


def units_of(text: str) -> list[str]:
    """The lines a reader meets: sentences, bullets, headings and table rows. HTML is reduced to its text first."""
    return [u for u, _ in _units(text)]


def _units(text: str) -> list[tuple[str, str]]:
    """(unit, the block it sits in). A link anywhere in a bullet or paragraph serves every sentence of it."""
    if re.search(r"<(?:html|body|div|p|table|h[1-6])\b", text, re.I):
        text = _ANCHOR.sub(lambda m: f"{m.group(2)} ({m.group(1)})", text)
        text = html_to_text(text)[1]
    out: list[tuple[str, str]] = []
    for line in text.split("\n"):
        line = re.sub(r"^\s*(?:[-*+•]|\d+[.)]|#{1,6})\s+", "", line).strip()
        if not line or re.fullmatch(r"[\s|:-]+", line):
            continue
        out.extend((u, line) for u in ([line] if line.startswith("|") else sentences(line)))
    return out


def _trace(line: str, figures: list[str], sources: Iterable[Evidence]) -> str | None:
    cw = content_words(line)
    for ev in sources:
        for p in passages(ev.text, 2):
            if figures and not set(figures) <= set(numbers_in(p)):
                continue
            have = set(content_words(p))
            if cw and sum(w in have for w in cw) / len(cw) >= 0.4:
                return ev.url
    return None


def audit(text: str, sources: Iterable[Evidence] | None = None) -> Audit:
    """Count the specifics in `text`; with `sources`, say which ones the pages carry."""
    units = _units(text)
    srcs = list(sources) if sources is not None else None
    out = Audit(units=len(units), with_sources=srcs is not None)
    for i, (line, block) in enumerate(units):
        linked = bool(_LINK.search(block))
        seen: list[tuple[int, int]] = []
        for kind, pattern in PATTERNS.items():
            for m in pattern.finditer(line):
                if any(a <= m.start() < b for a, b in seen):
                    continue  # one stretch of text is one specific, under the first kind that reads it
                seen.append(m.span())
                traced = _trace(line, numbers_in(m.group(0)), srcs) if srcs is not None else None
                out.specifics.append(Specific(i, kind, m.group(0).strip(), line, linked, traced))
    return out
