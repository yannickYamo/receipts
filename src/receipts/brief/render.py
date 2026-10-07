"""The page for a set of briefs. Code lays out what the check kept; no model writes HTML."""

from __future__ import annotations

from html import escape as h

from ..battlecard.pipeline import Line
from ..battlecard.render import CSS
from .pipeline import SIGNALS, YOU, Brief

NOT_MEASURED = "whether a page is itself right; whether the reasons and the message are good ones"
NOT_MEASURED_NO_READER = (
    "whether a page is itself right; whether a quote that shares a signal's words really states it, and "
    "whether a line adds a fact (no reader ran); whether the reasons and the message are good ones"
)


def panel_text(brief: Brief) -> str:
    """The verdict panel as plain text: what was read, what was kept, what was cut, what was not measured."""
    s = brief.stats()
    reasons = ", ".join(f"{n} {r.replace('_', ' ')}" for r, n in s["signals_cut_by_reason"].items()) or "none"
    rows = [
        f"company   {brief.company} · {brief.url}",
        f"sources   {s['pages_read']} pages of its own site read · {s['pages_unread']} could not be read",
        f"signals   {s['signals_supported']} of {s['signals_proposed']} supported by a quote on the page it names · {s['signals_cut']} cut ({reasons})",
        f"why now   {s['why_now_kept']} kept · {s['why_now_cut']} cut",
        f"message   {s['message_sentences_kept']} sentences kept · {s['message_sentences_cut']} cut",
        "on this page: every signal links to the page and quote it rests on; what you sell is in your words and is not checked",
        f"not measured: {NOT_MEASURED if brief.card.reader else NOT_MEASURED_NO_READER}",
        f"run       {brief.card.backend} · {s['model_calls']} model calls",
        f"reader    {brief.card.reader}"
        if brief.card.reader
        else "reader    none: signals were checked by code only (quote, figures, subject)",
    ]
    if s["signals_kept_on_a_second_quote"]:
        rows.insert(
            3,
            f"          {s['signals_kept_on_a_second_quote']} of the supported signals were kept on a second quote from the same page",
        )
    if s["left_out_for_naming_a_person"]:
        rows.insert(
            3,
            f"          {s['left_out_for_naming_a_person']} proposed signals were left out because they name a person",
        )
    if brief.card.partial:
        rows.insert(2, f"          {len(brief.card.partial)} long pages were read only to {40_000:,} characters")
    return "\n".join(rows)


def _receipt(brief: Brief, fact_id: str) -> str:
    c = next(x for x in brief.card.claims if x.id == fact_id)
    ev = brief.card.ledger[c.evidence_id]
    return (
        f"<details><summary>{h(fact_id)} · source</summary><blockquote>{h(c.quote)}</blockquote>"
        f'<a href="{h(ev.url, quote=True)}">{h(ev.url)}</a> · read {h(ev.fetched_at[:10])}</details>'
    )


def _line(brief: Brief, x: Line) -> str:
    signals = [c for c in x.cites if c != YOU]
    yours = "" if signals else "<details><summary>rests on what you sell, in your words</summary></details>"
    return f"<li>{h(x.text)}{''.join(_receipt(brief, c) for c in signals)}{yours}</li>"


def _lines(brief: Brief, section: str, empty: str) -> str:
    kept = brief.lines(section)
    return f"<ul>{''.join(_line(brief, x) for x in kept)}</ul>" if kept else f'<p class="empty">{h(empty)}</p>'


def _signals(brief: Brief) -> str:
    out = []
    for kind in SIGNALS:
        found = [c for c in brief.signals if c.topic == kind]
        if found:
            out.append(
                f'<div class="topic">{h(kind)}</div><ul>'
                + "".join(f"<li>{h(c.text)}{_receipt(brief, c.id)}</li>" for c in found)
                + "</ul>"
            )
    return "".join(out) or '<p class="empty">No signal could be supported from the pages read.</p>'


def _one(brief: Brief) -> str:
    card = brief.card
    cut = "".join(f'<li>{h(c.text)}<div class="why">{h(card.verdicts[c.id].why)}</div></li>' for c in card.cut_claims)
    cut += "".join(f'<li>{h(x.text)}<div class="why">{h(x.reason)}</div></li>' for x in card.lines if not x.kept)
    cut += "".join(f'<li>{h(t)}<div class="why">{h(w)}</div></li>' for t, w in brief.skipped)
    sources = "".join(
        f'<tr><td>{h(e.id)}</td><td><a href="{h(e.url, quote=True)}">{h(e.title or e.url)}</a></td>'
        f"<td>{h(e.fetched_at[:10])}</td><td>{h(card.ledger.how(e.id))}</td><td>{h(e.sha256[:12])}</td></tr>"
        for e in card.ledger.values()
    )
    unread = "".join(f"<tr><td>{h(u)}</td><td>{h(w)}</td></tr>" for _, u, w in card.unread)
    notes = "".join(f"<li>{h(n)}</li>" for n in card.notes)
    return f"""<section>
<h1>{h(brief.company)}</h1>
<p class="sub">Brief for a first message. Every signal opens to the quote and page it rests on.</p>
<div class="panel">{h(panel_text(brief))}</div>
<h2>What its own pages say</h2><div class="box">{_signals(brief)}</div>
<h2>Why now</h2><div class="box">{_lines(brief, "why_now", "No reason could be rested on the signals.")}</div>
<h2>A first message</h2><div class="box">{_lines(brief, "message", "No message could be rested on the signals.")}</div>
<h2>Cut before it reached this page</h2>
<div class="box cut"><ul>{cut}</ul>{"" if cut else '<p class="empty">Nothing was cut.</p>'}</div>
<h2>Sources</h2><div class="box"><table><tr><th>id</th><th>page</th><th>read</th><th>how</th><th>sha256</th></tr>{sources}</table>
{f"<table><tr><th>could not be read</th><th>why</th></tr>{unread}</table>" if unread else ""}
{f"<ul>{notes}</ul>" if notes else ""}</div>
</section>"""


def render_html(briefs: list[Brief]) -> str:
    """The briefs as one self-contained HTML page. Every value is escaped; no model writes any of it."""
    seller = briefs[0].seller if briefs else ""
    title = "Briefs: " + ", ".join(b.company for b in briefs)
    body = "\n<hr>\n".join(_one(b) for b in briefs)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h(title)}</title><style>{CSS}hr{{border:0;border-top:1px solid var(--line);margin:56px 0}}section h1{{margin-top:0}}</style></head><body><main>
<p class="sub">You sell: {h(seller)}</p>
{body}
</main></body></html>
"""
