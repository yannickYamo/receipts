"""The check. A model may point at evidence; only code may vouch for it.

A claim is a sentence someone will repeat to a customer. It carries a quote and the id of the page the
quote is said to come from. The page was fetched by code and its text is stored in the ledger. The
check never asks a model whether the claim is true. It asks seven things it can answer by itself:

  1. no_evidence          does the page exist in the ledger?
  2. no_quote             is there a quote at all?
  3. quote_not_in_source  is the quote really on that page, word for word?
     (from here on the check reads the passage: the quote widened to whole sentences of the page)
  4. wrong_subject        is the page, or the quote, about the product the claim names?
  5. figure_not_in_quote  does every figure in the claim appear in the quote, money as money?
  6. polarity_mismatch    does the claim negate something the page affirms there, or the reverse?
  7. beyond_quote         do the claim's words go past what the quote says?

A claim that fails any of them is unsupported, and the caller cuts it. Nothing is reworded.

What this does not decide: whether the page itself is right, and whether a quote that shares the
claim's words and figures really states it. The second is the reader's job (reader.py). The negation
check here is narrow on purpose, three words after a negator: it is a floor under the reader, not a
replacement for it.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

from .text import carries, content_words, figures_in, norm, numbers_in, quote_passage, stem, tokens

REASONS: dict[str, str] = {
    "ok": "the quote is on the page and carries the claim's figures and words",
    "no_evidence": "the claim names no page in the ledger",
    "no_quote": "the claim carries no quote",
    "quote_not_in_source": "the quote is not on the page it names",
    "wrong_subject": "neither the page nor the quote is about the product the claim names",
    "figure_not_in_quote": "the claim states a figure the quote does not",
    "polarity_mismatch": "the claim and the quote disagree on a negation",
    "beyond_quote": "the claim says more than the quote does",
}

_NEGATORS = frozenset(
    [
        "no",
        "not",
        "never",
        "without",
        "lack",
        "lacks",
        "lacking",
        "unavailable",
        "unsupported",
        "missing",
        "neither",
        "nor",
        "none",
    ]
)


@dataclass(frozen=True)
class Evidence:
    """One page, as code fetched it."""

    id: str
    url: str
    text: str
    title: str = ""
    fetched_at: str = ""  # ISO 8601, UTC
    sha256: str = ""


@dataclass(frozen=True)
class Claim:
    """One sentence someone will repeat, with the quote and the page it is said to rest on."""

    id: str
    text: str
    quote: str = ""
    evidence_id: str = ""
    subject: str = ""  # the product or company the claim is about
    topic: str = ""


@dataclass(frozen=True)
class Verdict:
    """The decision on one claim: supported or not, and the reason."""

    claim_id: str
    supported: bool
    reason: str
    detail: str = ""
    match: str | None = None  # "exact" when the quote was found on the page
    stale: bool = False
    url: str = ""

    @property
    def why(self) -> str:
        """The reason in words a person can act on."""
        return REASONS[self.reason] + (f" ({self.detail})" if self.detail else "")


@dataclass
class Report:
    """The verdicts on a set of claims."""

    verdicts: list[Verdict] = field(default_factory=list)

    @property
    def supported(self) -> list[Verdict]:
        """The verdicts of the claims that stand."""
        return [v for v in self.verdicts if v.supported]

    @property
    def cut(self) -> list[Verdict]:
        """The verdicts of the claims that were cut."""
        return [v for v in self.verdicts if not v.supported]

    @property
    def by_reason(self) -> dict[str, int]:
        """How many claims were cut for each reason."""
        out: dict[str, int] = {}
        for v in self.cut:
            out[v.reason] = out.get(v.reason, 0) + 1
        return out

    def to_dict(self) -> dict:
        """The report as plain data, for JSON."""
        return {
            "claims": len(self.verdicts),
            "supported": len(self.supported),
            "cut": len(self.cut),
            "by_reason": self.by_reason,
            "stale": sum(v.stale for v in self.verdicts),
            "verdicts": [asdict(v) | {"why": v.why} for v in self.verdicts],
        }


def _negated(text: str, shared: set[str]) -> set[str]:
    """The shared words that sit within three tokens after a negator in `text`."""
    toks = tokens(text)
    out: set[str] = set()
    for i, t in enumerate(toks):
        if t in _NEGATORS:
            out.update(s for s in (stem(x) for x in toks[i + 1 : i + 4]) if s in shared)
    return out


def polarity_mismatch(a: str, b: str) -> bool:
    """True when one text negates words the two share and the other does not negate any of them."""
    shared = set(content_words(a)) & set(content_words(b))
    if not shared:
        return False
    return bool(_negated(a, shared)) != bool(_negated(b, shared))


def overlap(text: str, support: str, ignore: str = "") -> float:
    """The share of `text`'s content words found in `support`. Words of `ignore` (a product name) don't count."""
    skip = set(content_words(ignore))
    cw = [w for w in content_words(text) if w not in skip]
    if not cw:
        return 1.0
    have = set(content_words(support))
    return sum(w in have for w in cw) / len(cw)


def _names(s: str) -> set[str]:
    """The words and numbers of a name, in any script: "3M", "Any.do" and "Яндекс" all have some."""
    return set(re.findall(r"[^\W_]+", norm(s)))


def _subject_problem(claim: Claim, ev: Evidence, quote: str) -> str | None:
    """Why the page cannot be held to this claim's subject, or None when it can.

    The page is about the subject when its title or its address names it, or when the quote does. The
    address counts without "www" and without its ending: "com" names nothing.
    """
    subject = _names(claim.subject)
    if not subject:
        return "the claim names no product"  # without a subject there is nothing to hold the page to
    try:
        address = urlsplit(ev.url)
        site = set((address.hostname or "").split(".")[:-1]) - {"www"}
        about = _names(ev.title) | site | _names(address.path)
    except ValueError:
        about = _names(ev.title)
    if subject <= about or subject <= _names(quote):
        return None
    return claim.subject


def _missing_figures(claim: Claim, ev: Evidence, quote: str, passage: str) -> list[str]:
    """The figures the claim states that the page does not carry in the quote.

    A figure must be in the quote, and be the same figure in the sentence the quote was cut from:
    "$425" clipped out of "$425 million" is in the quote and is not what the page says. A number inside
    the product's own name ("Microsoft 365") is a name, but only when the page writes the name that
    way: the caller cannot exempt a figure by putting it in the subject.
    """
    named = set(numbers_in(claim.subject)) if norm(claim.subject) in norm(f"{ev.title} {ev.text}") else set()
    in_quote, in_passage = figures_in(quote), figures_in(passage, folded=True)
    return [
        value
        for value, kind in figures_in(claim.text)
        if not (kind == "" and value in named)  # only a bare number can be part of a name: "$365" is a price
        and not (carries((value, kind), in_quote) and carries((value, kind), in_passage))
    ]


def _is_stale(ev: Evidence, max_age_days: int | None, now: datetime | None) -> bool:
    """Was the page read longer ago than `max_age_days`? A date without a time zone is read as UTC."""
    if max_age_days is None or not ev.fetched_at:
        return False
    fetched = datetime.fromisoformat(ev.fetched_at.replace("Z", "+00:00"))
    if fetched.tzinfo is None:
        fetched = fetched.replace(tzinfo=timezone.utc)
    return (now or datetime.now(timezone.utc)) - fetched > timedelta(days=max_age_days)


def _first_failure(claim: Claim, ev: Evidence, quote: str, passage: str, min_overlap: float) -> tuple[str, str] | None:
    """The first check the claim fails once its quote is found, as (reason, detail), or None."""
    problem = _subject_problem(claim, ev, quote)
    if problem:
        return "wrong_subject", problem
    missing = _missing_figures(claim, ev, quote, passage)
    if missing:
        return "figure_not_in_quote", ", ".join(missing)
    if polarity_mismatch(claim.text, passage):
        return "polarity_mismatch", ""
    share = overlap(claim.text, quote, ignore=claim.subject)
    if share < min_overlap:
        return "beyond_quote", f"{share:.0%} of its words are in the quote"
    return None


def check_claim(
    claim: Claim,
    ledger: Mapping[str, Evidence],
    *,
    min_overlap: float = 0.5,
    max_age_days: int | None = None,
    now: datetime | None = None,
) -> Verdict:
    """Decide one claim against the ledger. See the module docstring for the order of the checks."""
    ev = ledger.get(claim.evidence_id)
    if ev is None:
        return Verdict(claim.id, False, "no_evidence", claim.evidence_id)
    quote = claim.quote.strip()
    if len(tokens(quote)) < 3 and not numbers_in(quote):
        return Verdict(claim.id, False, "no_quote", url=ev.url)
    passage = quote_passage(quote, ev.text)
    if passage is None:
        return Verdict(claim.id, False, "quote_not_in_source", url=ev.url)
    failure = _first_failure(claim, ev, quote, passage, min_overlap)
    if failure:
        return Verdict(claim.id, False, failure[0], failure[1], match="exact", url=ev.url)
    return Verdict(claim.id, True, "ok", match="exact", stale=_is_stale(ev, max_age_days, now), url=ev.url)


def check_claims(claims: Iterable[Claim], ledger: Mapping[str, Evidence], **kw) -> Report:
    """Decide every claim against the ledger. Keyword arguments are passed to `check_claim`."""
    return Report([check_claim(c, ledger, **kw) for c in claims])
