"""Text handling for the check: normalising, numbers, content words, passages, HTML to text.

Everything here is deterministic and has no dependencies. The check in core.py is only as good as
these functions, so each one is small and tested on its own.
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

STOP = frozenset(
    [
        "a",
        "an",
        "the",
        "and",
        "or",
        "but",
        "if",
        "so",
        "of",
        "to",
        "in",
        "on",
        "at",
        "by",
        "for",
        "from",
        "with",
        "as",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "it",
        "its",
        "this",
        "that",
        "these",
        "those",
        "there",
        "here",
        "than",
        "then",
        "when",
        "what",
        "which",
        "who",
        "whom",
        "whose",
        "will",
        "would",
        "can",
        "could",
        "should",
        "may",
        "might",
        "must",
        "do",
        "does",
        "did",
        "have",
        "has",
        "had",
        "not",
        "no",
        "we",
        "us",
        "our",
        "you",
        "your",
        "they",
        "them",
        "their",
        "he",
        "she",
        "his",
        "her",
        "i",
        "me",
        "my",
        "also",
        "more",
        "most",
        "very",
        "into",
        "about",
        "over",
        "per",
        "via",
        "up",
        "out",
        "all",
        "any",
        "each",
        "both",
        "such",
        "only",
        "own",
        "same",
        "other",
        "some",
        "just",
        "now",
        "new",
    ]
)

_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-", "‑": "-", " ": " "})


def norm(s: str) -> str:
    """The text as compared: case, quote style, dash style, spacing and thousands separators aside."""
    t = s.translate(_QUOTES).lower()
    t = re.sub(r"(\d),(?=\d{3}\b)", r"\1", t)
    return re.sub(r"\s+", " ", t).strip()


def stem(w: str) -> str:
    """A crude stem, so "prices", "priced" and "pricing" meet. Not linguistics, only a meeting point."""
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        w = w[:-1]
    for suffix in ("ing", "ed"):
        if len(w) > 5 and w.endswith(suffix):
            w = w[: -len(suffix)]
            break
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def tokens(s: str) -> list[str]:
    """Lowercase word tokens, with contractions opened so a negation is always its own token."""
    t = norm(s).replace("cannot", "can not")
    t = re.sub(r"n't\b", " not", t)
    return re.findall(r"[a-z][a-z0-9+#]*", t)


def content_words(s: str) -> list[str]:
    """The stems that carry meaning: no stop words, no single letters."""
    return [stem(w) for w in tokens(s) if len(w) >= 2 and w not in STOP]


# ── Numbers ───────────────────────────────────────────────────────────────────────────────────────
#
# A figure is its value and its kind. "$1.5M", "1.5 million dollars" and "$1,500,000" are one figure;
# "25" is not "250"; "$19" is not "19 agents". A digit run glued to a letter ("G2", "Q3", "v2") is a
# name, not a figure, and is not read.

_SCALE = {"k": 1e3, "m": 1e6, "b": 1e9, "bn": 1e9, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_CURRENCY_CODE = re.compile(r"\b(?:US\$|USD|EUR|GBP|INR|Rs\.?)\s?(?=[\d.])", re.I)
_DIGITS = re.compile(
    r"(?<![\w.])([$€£]\s?)?(\d{1,3}(?:,\d{3})+|\d+)(\.\d+)?"
    r"(?:\s?(thousand|million|billion|trillion)\b|(k|m|bn|b)\b)?"
    r"(\s?%|\s?percent\b|\s(?:dollars|euros|pounds)\b)?",
    re.I,
)
_UNITS = {
    w: i
    for i, w in enumerate(
        [
            "zero",
            "one",
            "two",
            "three",
            "four",
            "five",
            "six",
            "seven",
            "eight",
            "nine",
            "ten",
            "eleven",
            "twelve",
            "thirteen",
            "fourteen",
            "fifteen",
            "sixteen",
            "seventeen",
            "eighteen",
            "nineteen",
        ]
    )
}
_TENS = {
    w: 10 * (i + 2)
    for i, w in enumerate(["twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"])
}
_WORD_SCALE = {"hundred": 100, "thousand": 1e3, "million": 1e6, "billion": 1e9, "trillion": 1e12}
_NUMBER_WORD = "|".join([*_UNITS, *_TENS, *_WORD_SCALE])
_WORDS = re.compile(rf"\b(?:{_NUMBER_WORD})(?:[\s-]+(?:and\s+)?(?:{_NUMBER_WORD}))*\b", re.I)


def _canon(v: float) -> str:
    return (f"{v:.6f}").rstrip("0").rstrip(".")


def figures_in(s: str) -> list[tuple[str, str]]:
    """Every figure `s` states, as (value, kind). Kind is "$" for money, "%" for a share, "" otherwise."""
    t = _CURRENCY_CODE.sub("$", s.translate(_QUOTES))
    t = re.sub(r"(?<![\w.])\.(?=\d)", "0.", t)  # ".5%" is 0.5%
    out: list[tuple[str, str]] = []
    taken: list[tuple[int, int]] = []
    for m in _DIGITS.finditer(t):
        value = float(m.group(2).replace(",", "") + (m.group(3) or ""))
        money = bool(m.group(1)) or (m.group(6) or "").strip().lower() in ("dollars", "euros", "pounds")
        scale = (m.group(4) or m.group(5) or "").lower()
        if scale in ("m", "b", "bn") and not money:
            scale = ""  # "5m" may be metres; a bare letter scales only money ("$5M")
        kind = "$" if money else "%" if (m.group(6) or "").strip().lower() in ("%", "percent") else ""
        out.append((_canon(value * _SCALE.get(scale, 1)), kind))
        taken.append(m.span())
    for m in _WORDS.finditer(t):
        if any(a <= m.start() < b for a, b in taken):
            continue  # the scale word of "3 million", already read with its digits
        parts = [p for p in re.split(r"[\s-]+", m.group(0).lower()) if p != "and"]
        if all(p in _WORD_SCALE for p in parts) or parts == ["one"]:
            continue  # "a hundred reasons", "no one": idiom far more often than a figure
        total = current = 0.0
        for p in parts:
            if p in _UNITS:
                current += _UNITS[p]
            elif p in _TENS:
                current += _TENS[p]
            elif p == "hundred":
                current = (current or 1) * 100
            else:
                total += (current or 1) * _WORD_SCALE[p]
                current = 0
        out.append((_canon(total + current), ""))
    return out


def numbers_in(s: str) -> list[str]:
    """The values of the figures in `s`, kinds aside."""
    return [v for v, _ in figures_in(s)]


def carries(figure: tuple[str, str], figures: list[tuple[str, str]]) -> bool:
    """Does a text with `figures` carry this one? Same value; and money or a share must stay money or a share."""
    value, kind = figure
    return any(value == v and (not kind or kind == k) for v, k in figures)


# ── Passages and quotes ───────────────────────────────────────────────────────────────────────────


def sentences(s: str) -> list[str]:
    """Split text into sentences, at sentence punctuation and at line breaks."""
    return [x for x in re.split(r"(?<=[.!?])\s+|\n+", s) if x.strip()]


def passages(source: str, span: int) -> list[str]:
    """Runs of `span` adjacent sentences inside one paragraph. Used by the audit to trace a line to a page."""
    out: list[str] = []
    for para in re.split(r"\n\s*\n|\n(?=\s*(?:[-*+]\s|\d+[.)]\s|#{1,6}\s|\|))", source):
        ss = sentences(para)
        for i in range(len(ss)):
            out.append(" ".join(ss[i : i + span]))
    return out


def _whole(hay: str, i: int, j: int) -> bool:
    """Is hay[i:j] a run of whole words and whole numbers? "$19" is not found in "$199", nor "supported" in "unsupported"."""
    before, first = (hay[i - 1] if i else " "), hay[i]
    last, after = hay[j - 1], (hay[j] if j < len(hay) else " ")
    if first.isalnum() and before.isalnum():
        return False
    if first.isdigit() and before in ".," and i >= 2 and hay[i - 2].isdigit():
        return False
    if last.isalnum() and after.isalnum():
        return False
    more_digits = after in ".," and j + 1 < len(hay) and hay[j + 1].isdigit()
    return not (last.isdigit() and (after == "%" or more_digits))


def norm_lines(s: str) -> str:
    """Like `norm`, but line breaks survive: a passage must not run from one table cell into the next."""
    return "\n".join(x for x in (norm(line) for line in s.split("\n")) if x)


def _span(hay: str, quote: str) -> tuple[int, int] | None:
    """Where `quote` sits in `hay` as whole words, its spaces allowed to fall on line breaks."""
    pattern = r"\s+".join(re.escape(w) for w in quote.split())
    for m in re.finditer(pattern, hay):
        if _whole(hay, m.start(), m.end()):
            return m.span()
    return None


# A quote joined by an ellipsis is for tables and tiles, where a name and its value sit on separate
# lines. Every part but the last must be a whole line of the page, the last must start a line, and the
# lines must be close together. Prose cannot be stitched: "Freshdesk ... was fined" finds nothing.
ELLIPSIS_LINES = 12
_SENTENCE_END = re.compile(r"[.!?]\s|\n")


def _table_passage(fragments: list[str], lines: list[str]) -> str | None:
    """The lines an ellipsis quote names, when each part is a line of the page and they sit close together."""
    for a, line in enumerate(lines):
        if line != fragments[0]:
            continue
        at, found = a, [line]
        for n, f in enumerate(fragments[1:], start=2):
            last = n == len(fragments)
            reach = range(at + 1, min(at + 1 + ELLIPSIS_LINES, len(lines)))
            at = next(
                (
                    b
                    for b in reach
                    if lines[b] == f or (last and lines[b].startswith(f) and _whole(lines[b], 0, len(f)))
                ),
                -1,
            )
            if at == -1:
                break
            found.append(lines[at])
        else:
            return " ".join(found)
    return None


def quote_passage(quote: str, source: str) -> str | None:
    """The whole sentences of the page that the quote sits in, or None when the quote is not on the page.

    A quote can be on the page and still mislead: "acquire Five9 for $14.7 billion" cut out of "announced
    plans to acquire Five9", "$425" cut out of "$425 million", "its systems were affected" cut out of a
    denial. So nothing downstream trusts the quote as given. The check and the reader both read the
    passage: the quote widened to the sentence boundaries of the page.
    """
    q = quote.strip().strip('"').strip()
    fragments = [f for f in (norm(x).strip() for x in re.split(r"\.{3,}|…|\[\.\.\.\]", q)) if f]
    if not fragments:
        return None
    src = norm_lines(source)
    if len(fragments) > 1:
        return _table_passage(fragments, src.split("\n"))
    span = _span(src, fragments[0].strip(" .") or fragments[0])
    if span is None:
        return None
    ends = [m.end() for m in _SENTENCE_END.finditer(src, 0, span[0])]
    nxt = _SENTENCE_END.search(src, max(span[1] - 1, span[0]))
    start, end = (ends[-1] if ends else 0), (nxt.start() + 1 if nxt else len(src))
    return src[start:end].replace("\n", " ").strip()


def quote_match(quote: str, source: str) -> str | None:
    """ "exact" when the quote is on the page, word for word (case, spacing and quote style aside), else None."""
    return "exact" if quote_passage(quote, source) is not None else None


# ── HTML ──────────────────────────────────────────────────────────────────────────────────────────

_SKIP = {"script", "style", "noscript", "svg", "template", "iframe"}
_BLOCK = {
    "p",
    "div",
    "section",
    "article",
    "li",
    "ul",
    "ol",
    "tr",
    "table",
    "br",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "footer",
    "main",
    "nav",
    "blockquote",
    "pre",
    "dd",
    "dt",
    "td",
    "th",
}


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.title: list[str] = []
        self._skip = 0
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        if tag == "title" and not self._skip:  # an <svg><title> is a label, not the page's title
            self._in_title = True
        elif tag in _SKIP:
            self._skip += 1
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        elif tag in _SKIP:
            self._skip = max(0, self._skip - 1)
        elif tag in _BLOCK:
            self.out.append("\n")

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        elif not self._skip:
            self.out.append(data)


def html_to_text(html: str) -> tuple[str, str]:
    """(title, visible text) of an HTML page. Scripts, styles and markup are dropped; blocks become lines."""
    p = _Text()
    p.feed(html)
    p.close()
    lines = [re.sub(r"[ \t\r\f\v]+", " ", x).strip() for x in "".join(p.out).split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return re.sub(r"\s+", " ", "".join(p.title)).strip(), text
