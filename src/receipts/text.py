"""Text handling for the check: normalising, numbers, content words, passages, HTML to text.

Everything here is deterministic and has no dependencies. The check in core.py is only as good as
these functions, so each one is small and tested on its own.
"""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser

# fmt: off
STOP = frozenset(
    ["a", "an", "the", "and", "or", "but", "if", "so", "of", "to", "in", "on", "at", "by", "for", "from", "with", "as", "is", "are", "was", "were", "be", "been", "being", "it", "its", "this", "that", "these", "those", "there", "here", "than", "then", "when", "what", "which", "who", "whom", "whose", "will", "would", "can", "could", "should", "may", "might", "must", "do", "does", "did", "have", "has", "had", "not", "no", "we", "us", "our", "you", "your", "they", "them", "their", "he", "she", "his", "her", "i", "me", "my", "also", "more", "most", "very", "into", "about", "over", "per", "via", "up", "out", "all", "any", "each", "both", "such", "only", "own", "same", "other", "some", "just", "now", "new"]
)
# fmt: on

# An em dash stands between words, so it becomes a spaced hyphen; an en dash sits inside ranges ("5–15").
_QUOTES = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": " - ", "‑": "-", "\u00a0": " "})
_ZERO_WIDTH = dict.fromkeys(map(ord, "\u200b\u200c\u200d\u2060\ufeff"))


def norm(s: str) -> str:
    """The text as compared: case, quote and dash style, spacing, thousands separators and Unicode form aside."""
    t = unicodedata.normalize("NFC", s).translate(_ZERO_WIDTH).translate(_QUOTES).lower()
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
    return re.findall(r"[^\W\d_][\w+#]*", t)  # a letter of any script, then letters, digits, + or #


def content_words(s: str) -> list[str]:
    """The stems that carry meaning: no stop words, no single letters."""
    return [stem(w) for w in tokens(s) if len(w) >= 2 and w not in STOP]


# ── Numbers ───────────────────────────────────────────────────────────────────────────────────────
#
# A figure is its value and its kind. "$1.5M", "1.5 million dollars" and "$1,500,000" are one figure;
# "25" is not "250"; "$19" is not "19 agents" and not "€19". A digit run glued to a letter ("G2", "Q3",
# "v2") and a version ("1.2.3") are names, not figures, and are not read.

_SCALE = {"k": 1e3, "thousand": 1e3, "m": 1e6, "million": 1e6, "b": 1e9, "bn": 1e9, "billion": 1e9, "trillion": 1e12}
_CODE = {"us$": "$", "usd": "$", "eur": "€", "gbp": "£", "inr": "₹", "rs": "₹", "rs.": "₹"}
_MONEY_WORD = {
    "dollar": "$",
    "dollars": "$",
    "usd": "$",
    "euro": "€",
    "euros": "€",
    "eur": "€",
    "pounds": "£",
    "gbp": "£",
}
_CODE_BEFORE = re.compile(r"\b(US\$|USD|EUR|GBP|INR|Rs\.?)\s?(?=[\d.])", re.I)
_KIND_AFTER = r"(\s?%|\s?(?i:percent)\b|\s(?i:dollars?|euros?|pounds|usd|eur|gbp)\b)?"
_DIGITS = re.compile(
    r"(?<![\w.])([$€£₹]\s?)?(\d{1,3}(?:,\d{3})+|\d+)((?:\.\d+)*)"
    r"(?:[\s-]?((?i:thousand|million|billion|trillion))\b|([kK]|[mMbB]|[bB][nN])\b)?\+?" + _KIND_AFTER
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
_WORDS = re.compile(rf"\b(?:{_NUMBER_WORD})(?:[\s-]+(?:and\s+)?(?:{_NUMBER_WORD}))*\b" + _KIND_AFTER, re.I)
_RANGE = re.compile(r"\s?(?:-|to)\s?", re.I)


def _canon(v: float) -> str:
    return (f"{v:.6f}").rstrip("0").rstrip(".")


def _kind(before: str | None, after: str | None) -> str:
    """The kind a figure's surroundings give it: a currency symbol, "%", or "" for a plain count."""
    if before:
        return before.strip()
    word = (after or "").strip().lower()
    return "%" if word in ("%", "percent") else _MONEY_WORD.get(word, "")


def _digit_figures(t: str, folded: bool = False) -> list[dict]:
    """Figures written with digits, in order, each with where it sits, its value, kind and scale."""
    out = []
    for m in _DIGITS.finditer(t):
        if m.group(3).count(".") > 1:
            continue  # "1.2.3" is a version
        kind = _kind(m.group(1), m.group(6))
        letter = m.group(5) or ""
        # A capital M or B is a scale ("5M users"); a small one may be metres or bytes unless it is money.
        if letter.islower() and letter != "k" and kind in ("", "%") and not folded:
            letter = ""
        scale = (m.group(4) or letter).lower()
        value = float(m.group(2).replace(",", "") + m.group(3))
        out.append({"span": m.span(), "value": value, "kind": kind, "scale": _SCALE.get(scale, 1)})
    return out


def _share_across_ranges(t: str, figures: list[dict]) -> None:
    """In "5-15%", "$5 to 15" and "3 to 5 million", the kind and the scale belong to both ends."""
    for a, b in zip(figures, figures[1:], strict=False):
        if not _RANGE.fullmatch(t[a["span"][1] : b["span"][0]]):
            continue
        a["kind"] = b["kind"] = a["kind"] or b["kind"]
        if a["scale"] == 1:
            a["scale"] = b["scale"]


def _word_figures(t: str, taken: list[tuple[int, int]]) -> list[tuple[str, str]]:
    """Figures spelled out ("twenty-five", "three million dollars"). A lone "one" or "hundred" is idiom, not a figure."""
    out = []
    for m in _WORDS.finditer(t):
        if any(a <= m.start() < b for a, b in taken):
            continue  # the scale word of "3 million", already read with its digits
        words = m.group(0)[: len(m.group(0)) - len(m.group(1) or "")]
        parts = [p for p in re.split(r"[\s-]+", words.lower()) if p and p != "and"]
        if all(p in _WORD_SCALE for p in parts) or parts == ["one"]:
            continue
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
        out.append((_canon(total + current), _kind(None, m.group(1))))
    return out


def figures_in(s: str, folded: bool = False) -> list[tuple[str, str]]:
    """Every figure `s` states, as (value, kind). Kind is a currency symbol, "%" for a share, or "" for a count.

    `folded` says the text was lower-cased (a passage is), so "5m" may have been "5M" and is read as a scale.
    """
    t = _CODE_BEFORE.sub(lambda m: _CODE[m.group(1).lower()], s.translate(_QUOTES))
    t = re.sub(r"(?<![\w.])\.(?=\d)", "0.", t)  # ".5%" is 0.5%
    digits = _digit_figures(t, folded)
    _share_across_ranges(t, digits)
    out = [(_canon(f["value"] * f["scale"]), f["kind"]) for f in digits]
    return out + _word_figures(t, [f["span"] for f in digits])


def numbers_in(s: str) -> list[str]:
    """The values of the figures in `s`, kinds aside."""
    return [v for v, _ in figures_in(s)]


def carries(figure: tuple[str, str], figures: list[tuple[str, str]]) -> bool:
    """Does a text with `figures` carry this one? Same value and same kind: "$19" is not "19 agents", either way round."""
    return figure in figures


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
    """Is hay[i:j] a run of whole words and whole numbers?

    "$19" is not found in "$199", "supported" not in "unsupported", "compliant" not in "non-compliant".
    """
    before, first = (hay[i - 1] if i else " "), hay[i]
    earlier = hay[i - 2] if i >= 2 else " "
    last, after = hay[j - 1], (hay[j] if j < len(hay) else " ")
    if first.isalnum() and (before.isalnum() or (before == "-" and earlier.isalnum())):
        return False
    if first.isdigit() and before in ".," and earlier.isdigit():
        return False
    if last.isalnum() and (after.isalnum() or (after == "-" and j + 1 < len(hay) and hay[j + 1].isalnum())):
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
_STOP_MARK = re.compile(r"[.!?]\s|\n")
_ABBREVIATION = frozenset(
    [
        "inc",
        "incl",
        "corp",
        "ltd",
        "co",
        "vs",
        "etc",
        "approx",
        "est",
        "mr",
        "mrs",
        "ms",
        "dr",
        "st",
        "jr",
        "sr",
        "e.g",
        "i.e",
        "eg",
        "ie",
    ]
)


def _sentence_breaks(src: str) -> list[int]:
    """Where a sentence ends in `src`: after ". ", "! ", "? " or a line break, but not after "Inc." or "U.S."."""
    out = []
    for m in _STOP_MARK.finditer(src):
        if m.group(0)[0] == ".":
            word = re.search(r"([^\W\d_]+(?:\.[^\W\d_]+)*)$", src[max(0, m.start() - 40) : m.start()])
            if word and (word.group(1) in _ABBREVIATION or len(word.group(1).split(".")[-1]) == 1):
                continue
        out.append(m.start() + 1)
    return out


def _table_lines(fragments: list[str], lines: list[str]) -> list[int] | None:
    """Which lines an ellipsis quote names, when each part is a line of the page and they sit close together."""
    for a, line in enumerate(lines):
        if line != fragments[0]:
            continue
        found = [a]
        for n, f in enumerate(fragments[1:], start=2):
            last = n == len(fragments)
            reach = range(found[-1] + 1, min(found[-1] + 1 + ELLIPSIS_LINES, len(lines)))
            fits = (
                b for b in reach if lines[b] == f or (last and lines[b].startswith(f) and _whole(lines[b], 0, len(f)))
            )
            at = next(fits, -1)
            if at == -1:
                break
            found.append(at)
        else:
            return found
    return None


def _table_passage(fragments: list[str], lines: list[str]) -> str | None:
    """The lines an ellipsis quote names, joined, or None when the page has no such lines."""
    found = _table_lines(fragments, lines)
    return " ".join(lines[i] for i in found) if found else None


def _locate(quote: str, source: str) -> tuple[str, int, int, str] | None:
    """Where a quote sits: (the page as compared, start, end, passage), or None when it is not on the page.

    For a quote in prose, start and end are the bounds of its whole sentences. For lines joined by an
    ellipsis they run from the first quoted line to the last, the lines between them included.
    """
    q = norm(quote.strip().strip('"'))
    if not q:
        return None
    src = norm_lines(source)
    span = _span(src, q.strip(" .") or q)  # as written first: the page may have an ellipsis of its own
    if span is None:
        fragments = [f for f in (x.strip() for x in re.split(r"\.{3,}|…|\[\.\.\.\]", q)) if f]
        lines = src.split("\n")
        found = _table_lines(fragments, lines) if len(fragments) > 1 else None
        if not found:
            return None
        starts = [0]
        for line in lines:
            starts.append(starts[-1] + len(line) + 1)
        return src, starts[found[0]], starts[found[-1] + 1] - 1, " ".join(lines[i] for i in found)
    breaks = _sentence_breaks(src)
    start = max((b for b in breaks if b <= span[0]), default=0)
    end = min((b for b in breaks if b >= span[1]), default=len(src))
    return src, start, end, src[start:end].replace("\n", " ").strip()


def quote_passage(quote: str, source: str) -> str | None:
    """The whole sentences of the page that the quote sits in, or None when the quote is not on the page.

    A quote can be on the page and still mislead: "acquire Five9 for $14.7 billion" cut out of "announced
    plans to acquire Five9", "$425" cut out of "$425 million", "its systems were affected" cut out of a
    denial. So nothing downstream trusts the quote as given. The check and the reader both read the
    passage: the quote widened to the sentence boundaries of the page.
    """
    found = _locate(quote, source)
    return found[3] if found else None


LINE_BREAK = " | "  # how a line break of the page is shown in the text around a quote


def quote_context(quote: str, source: str, around: int = 3, limit: int = 400) -> tuple[str, str, str] | None:
    """What the page says around a quote: (before, between, after), or None when the quote is not on the page.

    `before` and `after` are up to `around` sentences or lines on each side, and at most `limit`
    characters. `between` is every line from the first quoted line to the last when the quote joins
    table lines and skips some; otherwise it is empty. Line breaks are shown as " | ".

    A passage can be faithful and still mislead by what it leaves out: the next sentence calls the deal
    off, or the "$49" two lines under "Starter" sits in the row of "Pro". The reader is shown this text
    so it can cut such a claim. It is never evidence for a claim.
    """
    found = _locate(quote, source)
    if found is None:
        return None
    src, start, end, passage = found
    breaks = [0, *_sentence_breaks(src), len(src)]
    first = ([b for b in breaks if b < start][-around:] or [start])[0]
    last = ([b for b in breaks if b > end][:around] or [end])[-1]
    before, whole, after = (
        x.strip().replace("\n", LINE_BREAK) for x in (src[first:start], src[start:end], src[end:last])
    )
    if len(before) > limit:
        before = before[-limit:].split(" ", 1)[-1]
    if len(after) > limit:
        after = after[:limit].rsplit(" ", 1)[0]
    return before, (whole if LINE_BREAK in whole and whole.replace(LINE_BREAK, " ") != passage else ""), after


def quote_match(quote: str, source: str) -> str | None:
    """Return "exact" when the quote is on the page, word for word (case, spacing and quote style aside)."""
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


_VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
_TABLE_ROLES = {"table", "grid", "treegrid"}
_HEAD_ROLES = {"columnheader", "rowheader"}
_CELL_ROLES = {"cell", "gridcell"}
CELL_BREAK = " | "  # between the cells of a table row, which is written as one line


def _table_part(tag: str, attrs: list) -> str:
    """What a tag is to a table: "table", "row", "head" (a header cell), "cell", or "" for anything else.

    A table made of <div>s that names its parts for screen readers (role="row", role="cell") is a
    table here too.
    """
    role = (dict(attrs).get("role") or "").lower()
    if tag == "table" or role in _TABLE_ROLES:
        return "table"
    if tag == "tr" or role == "row":
        return "row"
    if tag == "th" or role in _HEAD_ROLES:
        return "head"
    if tag == "td" or role in _CELL_ROLES:
        return "cell"
    return "thead" if tag == "thead" else ""


def row_line(
    cells: list[tuple[list[str], bool]], headers: list[str] | None, in_head: bool
) -> tuple[str, list[str] | None]:
    """One table row as one line of text, and the column headers to use for the rows after it.

    On a page, what a cell means is given by where it sits: under "Pro", beside "File uploads". Read
    cell by cell that is lost, and "10MB" is just a number. So a row is written whole, on one line,
    and each value carries the header of its column:

        File uploads | Free: 10MB | Pro: Unlimited

    A header is only ever what the page marks as one (<th>, <thead>, role="columnheader"). When a row
    does not line up with the headers, it is written plainly, cells side by side: no header is guessed.
    """
    texts = [" ".join(x for x in segments if x) for segments, _ in cells]
    if len(cells) > 1 and (in_head or all(head for _, head in cells)):
        labels = [next((x for x in segments if x), "") for segments, _ in cells]  # a header's first line names it
        return CELL_BREAK.join(t for t in texts if t), labels
    if headers and len(cells) == len(headers) and len(cells) > 1:
        rest = [f"{h}: {t}" if h else t for h, t in zip(headers[1:], texts[1:], strict=True) if t]
        return CELL_BREAK.join(x for x in [texts[0], *rest] if x), headers
    return CELL_BREAK.join(t for t in texts if t), headers


class _Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.out: list[str] = []
        self.title: list[str] = []
        self._skip = 0
        self._in_title = False
        self._open: list[tuple[str, str]] = []  # every open tag, with what it is to a table
        self._headers: list[list[str] | None] = [
            None
        ]  # column headers of each open table; the first is for rows outside any
        self._rows: list[list[tuple[list[str], bool]]] = []  # the cells of each open row
        self._cell: list[list[str]] = []  # the lines of text of each open cell

    def handle_starttag(self, tag, attrs):
        if tag == "title" and not self._skip:  # an <svg><title> is a label, not the page's title
            self._in_title = True
            return
        if tag in _SKIP:
            self._skip += 1
        kind = _table_part(tag, attrs)
        if tag not in _VOID:
            self._open.append((tag, kind))
        if kind == "table":
            self._headers.append(None)
        elif kind == "row":
            self._rows.append([])
        elif kind in ("head", "cell") and self._rows:
            self._cell.append([""])
        elif tag in _BLOCK:
            self._break()

    def _break(self) -> None:
        """A block ends a line: of the page, or of the cell it is in."""
        if self._cell:
            self._cell[-1].append("")
        else:
            self.out.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
            return
        at = next((i for i in range(len(self._open) - 1, -1, -1) if self._open[i][0] == tag), None)
        if at is None:
            return  # an end tag with nothing open to close
        closing, self._open = self._open[at:], self._open[:at]
        for closed, kind in reversed(closing):  # a tag left open closes with the one around it
            self._close(closed, kind)

    def _close(self, tag: str, kind: str) -> None:
        if tag in _SKIP:
            self._skip = max(0, self._skip - 1)
        if kind in ("head", "cell") and self._cell and self._rows:
            segments = [re.sub(r"\s+", " ", x).strip() for x in self._cell.pop()]
            self._rows[-1].append((segments, kind == "head"))
        elif kind == "row" and self._rows:
            in_head = any(k == "thead" for _, k in self._open)
            line, self._headers[-1] = row_line(self._rows.pop(), self._headers[-1], in_head)
            self._emit(line)
        elif kind == "table" and len(self._headers) > 1:
            self._headers.pop()
            self.out.append("\n")
        elif tag in _BLOCK:
            self._break()

    def _emit(self, line: str) -> None:
        """A finished row: a line of the page, or of the cell that holds its table."""
        if self._cell:
            self._cell[-1] += [line, ""]
        else:
            self.out.append(f"\n{line}\n")

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        elif self._skip:
            return
        elif self._cell:
            self._cell[-1][-1] += data
        else:
            self.out.append(data)

    def close(self):
        super().close()
        for tag, kind in reversed(self._open):  # a page cut short still gives up the rows it had
            self._close(tag, kind)
        self._open = []


def html_to_text(html: str) -> tuple[str, str]:
    """(title, visible text) of an HTML page. Scripts, styles and markup are dropped; blocks become lines."""
    p = _Text()
    p.feed(html)
    p.close()
    lines = [re.sub(r"[ \t\r\f\v]+", " ", x).strip() for x in "".join(p.out).split("\n")]
    text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
    return re.sub(r"\s+", " ", "".join(p.title)).strip(), text
