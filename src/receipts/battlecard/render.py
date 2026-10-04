"""The page. Code lays out what the check kept; no model writes HTML, so two runs differ only in facts."""

from __future__ import annotations

from html import escape as h

from .pipeline import TOPICS, Card, Line

CSS = """
:root{--bg:#f6f5f1;--card:#fff;--ink:#1c1b19;--mute:#6b6862;--line:#dedbd3;--us:#1f6f4a;--them:#9a3b26;--warn:#8a6200;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#161614;--card:#1f1e1c;--ink:#ecebe6;--mute:#a09d95;--line:#35332f;--us:#6fcf9b;--them:#f08f78;--warn:#e0b455}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1040px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:28px;line-height:1.2;margin:0 0 4px}h2{font-size:13px;letter-spacing:.08em;text-transform:uppercase;color:var(--mute);margin:40px 0 12px}
.sub{color:var(--mute);margin:0 0 24px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px;font:13px/1.7 var(--mono);overflow-x:auto;white-space:pre-wrap}
.panel b{font-weight:600}.ok{color:var(--us)}.bad{color:var(--them)}.warn{color:var(--warn)}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:16px}@media (max-width:720px){.cols{grid-template-columns:1fr}}
.box{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:16px 20px}
.box h3{margin:0 0 8px;font-size:15px}.box.us h3{color:var(--us)}.box.them h3{color:var(--them)}
ul{margin:0;padding:0;list-style:none}li{padding:10px 0;border-top:1px solid var(--line)}li:first-child{border-top:0}
.topic{font:11px var(--mono);color:var(--mute);text-transform:uppercase;letter-spacing:.06em;margin:14px 0 0}
details{margin-top:4px;font-size:13px;color:var(--mute)}summary{cursor:pointer}
blockquote{margin:6px 0 0;padding-left:12px;border-left:2px solid var(--line)}
a{color:inherit}.said{font-weight:600}.empty{color:var(--mute);font-style:italic}
.cut li{font-size:14px}.why{color:var(--them);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:14px}td,th{text-align:left;padding:8px 10px;border-top:1px solid var(--line);vertical-align:top}th{color:var(--mute);font-weight:500}
@media print{body{background:#fff}details{display:none}}
"""

NOT_MEASURED = "whether a page is itself right; whether the advice is good"
NOT_MEASURED_NO_READER = (
    "whether a page is itself right; whether a quote that shares a fact's words and figures "
    "really states it, and whether advice lines add facts (no reader ran); whether the advice is good"
)


def _receipt(card: Card, fact_id: str) -> str:
    c = next(x for x in card.claims if x.id == fact_id)
    ev = card.ledger[c.evidence_id]
    return (
        f"<details><summary>{h(fact_id)} · source</summary><blockquote>{h(c.quote)}</blockquote>"
        f'<a href="{h(ev.url, quote=True)}">{h(ev.url)}</a> · read {h(ev.fetched_at[:10])}</details>'
    )


def _line(card: Card, x: Line) -> str:
    said = f'<div class="said">“{h(x.objection)}”</div>' if x.objection else ""
    return f"<li>{said}{h(x.text)}{''.join(_receipt(card, c) for c in x.cites)}</li>"


def _section(card: Card, section: str) -> str:
    kept = [x for x in card.lines if x.section == section and x.kept]
    if not kept:
        return '<p class="empty">Nothing here could be supported from the pages read.</p>'
    return f"<ul>{''.join(_line(card, x) for x in kept)}</ul>"


def _facts(card: Card, product: str) -> str:
    out = []
    for topic in TOPICS:
        facts = [c for c in card.supported if c.subject == product and c.topic == topic]
        if facts:
            out.append(
                f'<div class="topic">{h(topic)}</div><ul>'
                + "".join(f"<li>{h(c.text)}{_receipt(card, c.id)}</li>" for c in facts)
                + "</ul>"
            )
    return "".join(out) or '<p class="empty">No supported facts.</p>'


def panel_text(card: Card) -> str:
    """The verdict panel as plain text: what was read, what was kept, what was cut, what was not measured."""
    s = card.stats()
    reasons = ", ".join(f"{n} {r.replace('_', ' ')}" for r, n in s["facts_cut_by_reason"].items()) or "none"
    rows = [
        f"sources   {s['pages_read']} pages read · {s['pages_unread']} could not be read",
        f"facts     {s['facts_supported']} of {s['facts_proposed']} supported by a quote on the page it names · {s['facts_cut']} cut ({reasons})",
        f"lines     {s['lines_kept']} of {s['lines_written']} kept · {s['lines_cut']} cut",
        "on this card: every line links to the page and quote it rests on",
        f"not measured: {NOT_MEASURED if card.reader else NOT_MEASURED_NO_READER}",
        f"run       {card.backend} · {s['model_calls']} model calls",
        f"reader    {card.reader}"
        if card.reader
        else "reader    none: facts were checked by code only (quote, figures, subject)",
    ]
    if card.reader:
        rows.append(
            "          its reading of facts is measured (studies/); its reading of card lines and advice is not"
        )
    if card.partial:
        rows.insert(1, f"          {len(card.partial)} long pages were read only to {40_000:,} characters")
    return "\n".join(rows)


def render_html(card: Card) -> str:
    """The card as one self-contained HTML page. Every value is escaped; no model writes any of it."""
    cut_facts = "".join(
        f'<li>{h(c.text)}<div class="why">{h(card.verdicts[c.id].why)}</div></li>' for c in card.cut_claims
    )
    cut_lines = "".join(f'<li>{h(x.text)}<div class="why">{h(x.reason)}</div></li>' for x in card.lines if not x.kept)
    unread = "".join(f"<tr><td>{h(p)}</td><td>{h(u)}</td><td>{h(w)}</td></tr>" for p, u, w in card.unread)
    sources = "".join(
        f'<tr><td>{h(e.id)}</td><td><a href="{h(e.url, quote=True)}">{h(e.title or e.url)}</a></td>'
        f"<td>{h(e.fetched_at[:10])}</td><td>{h(e.sha256[:12])}</td></tr>"
        for e in card.ledger.values()
    )
    notes = "".join(f"<li>{h(n)}</li>" for n in card.notes)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{h(card.us)} vs {h(card.them)}</title><style>{CSS}</style></head><body><main>
<h1>{h(card.us)} vs {h(card.them)}</h1>
<p class="sub">Battle card. Every line opens to the quote and page it rests on.</p>
<div class="panel">{h(panel_text(card))}</div>
<h2>Where each is strong</h2>
<div class="cols"><div class="box us"><h3>Where {h(card.us)} wins</h3>{_section(card, "we_win")}</div>
<div class="box them"><h3>Where {h(card.them)} wins</h3>{_section(card, "they_win")}</div></div>
<h2>What prospects say, and a response</h2><div class="box">{_section(card, "objections")}</div>
<h2>Questions worth asking</h2><div class="box">{_section(card, "questions")}</div>
<h2>The facts, side by side</h2>
<div class="cols"><div class="box us"><h3>{h(card.us)}</h3>{_facts(card, card.us)}</div>
<div class="box them"><h3>{h(card.them)}</h3>{_facts(card, card.them)}</div></div>
<h2>Cut before it reached the card</h2>
<div class="box cut"><ul>{cut_facts}{cut_lines}</ul>{"" if cut_facts or cut_lines else '<p class="empty">Nothing was cut.</p>'}</div>
<h2>Sources</h2><div class="box"><table><tr><th>id</th><th>page</th><th>read</th><th>sha256</th></tr>{sources}</table>
{f"<table><tr><th>product</th><th>could not be read</th><th>why</th></tr>{unread}</table>" if unread else ""}
{f"<ul>{notes}</ul>" if notes else ""}</div>
</main></body></html>
"""
