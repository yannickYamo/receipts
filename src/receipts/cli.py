"""The command line.

receipts check claims.json --ledger ledger.json     both stages; exit 1 when any claim is unsupported
receipts check claims.json --ledger l.json --code-only    the code stage alone: no model, and weaker
receipts fetch URL... --ledger ledger.json          read pages into a ledger
receipts audit card.html [--ledger ledger.json]     count the specifics in any text, and how many can be checked
receipts card --us A --them B --out DIR             build a battle card
receipts mcp                                        serve the check to an agent over MCP

Exit codes of `check`: 0 every claim is supported; 1 at least one was cut; 2 a file or an option is
wrong; 3 the reader gave no answer for at least one claim (those claims are cut, and the reason is printed).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import Claim, Ledger, check_claims
from .audit import audit
from .backends import BackendError
from .core import Report
from .fetch import FetchError


def _load_claims(path: str) -> list[Claim]:
    """Read claims from a JSON file: a list of objects, or an object with a "claims" list."""
    raw = json.loads(Path(path).read_text())
    items = raw.get("claims") if isinstance(raw, dict) else raw
    if not isinstance(items, list) or not all(isinstance(c, dict) for c in items):
        raise ValueError(f"{path}: expected a list of claims, each an object with text, quote, evidence_id and subject")
    return [
        Claim(
            id=str(c.get("id") or f"c{i + 1}"),
            text=str(c.get("text") or ""),
            quote=str(c.get("quote") or ""),
            evidence_id=str(c.get("evidence_id") or ""),
            subject=str(c.get("subject") or ""),
            topic=str(c.get("topic") or ""),
        )
        for i, c in enumerate(items)
    ]


CODE_ONLY_NOTE = (
    "code check only: the reader did not run. A claim that keeps a quote's words and changes their meaning "
    "can pass this stage. Drop --code-only to run both."
)


def _backend(kind: str, model: str):
    """The model backend for a command: the local `claude` command, or the Anthropic API."""
    from .backends import AnthropicBackend, ClaudeCodeBackend

    return ClaudeCodeBackend(model) if kind == "claude-code" else AnthropicBackend(model)


def _check(a: argparse.Namespace) -> int:
    claims = _load_claims(a.claims)
    ledger = Ledger.load(a.ledger)
    if a.code_only:
        report, stages = check_claims(claims, ledger, max_age_days=a.max_age_days), CODE_ONLY_NOTE
    else:
        from .reader import READER_VERSION, check_with_reader

        reader = _backend(a.backend, a.reader_model)
        report = check_with_reader(claims, ledger, reader, max_age_days=a.max_age_days)
        stages = f"code check, then reader ({reader.name}, prompt {READER_VERSION})"
    if a.json:
        print(json.dumps(report.to_dict() | {"stages": stages}, indent=1))
        return _exit_code(report)
    for claim, v in zip(claims, report.verdicts, strict=True):  # by position: two claims may share an id
        print(f"{'PASS' if v.supported else 'CUT '} {v.claim_id}  {claim.text}")
        if not v.supported:
            print(f"       {v.why}")
        if v.stale:
            print("       the page was read more than --max-age-days ago")
    print(f"\n{len(report.supported)} of {len(report.verdicts)} supported, {len(report.cut)} cut\n{stages}")
    return _exit_code(report)


def _exit_code(report: Report) -> int:
    """0 all supported, 1 some cut, 3 some cut because the reader gave no answer (said on stderr)."""
    unread = [v for v in report.verdicts if v.reason == "unread"]
    if unread:
        why = next((v.detail for v in unread if v.detail), "it returned nothing usable")
        print(
            f"receipts: the reader gave no answer for {len(unread)} claim(s), so they are cut: {why}", file=sys.stderr
        )
        return 3
    return 1 if report.cut else 0


def _fetch(a: argparse.Namespace) -> int:
    path = Path(a.ledger)
    ledger = Ledger.load(path) if path.exists() else Ledger()
    failed = 0
    for url in a.urls:
        try:
            ev = ledger.add_url(url)
            print(f"{ev.id}  {url}  ({len(ev.text):,} characters)")
        except FetchError as e:
            failed += 1
            print(f"could not read {url}: {e}", file=sys.stderr)
    ledger.save(path)
    return 1 if failed else 0


def _audit(a: argparse.Namespace) -> int:
    sources = list(Ledger.load(a.ledger).values()) if a.ledger else None
    result = audit(Path(a.file).read_text(), sources)
    if a.json:
        print(json.dumps(result.to_dict() | {"items": [s.__dict__ for s in result.specifics]}, indent=1))
        return 0
    d = result.to_dict()
    print(f"{d['lines']} lines, {d['lines_with_specifics']} of them state a specific a pattern can see")
    print(f"{d['specifics']} specifics: " + ", ".join(f"{n} {k.lower()}" for k, n in d["by_kind"].items()))
    print(f"{d['linked']} of {d['specifics']} sit on a line with a link a reader could follow")
    if sources is not None:
        print(f"{d['traced']} of {d['specifics']} appear on one of the {len(sources)} pages given")
    return 0


def _card(a: argparse.Namespace) -> int:
    from .battlecard import build_card, render_html
    from .battlecard.render import panel_text

    backend = _backend(a.backend, a.model or ("sonnet" if a.backend == "claude-code" else "opus"))
    urls = {a.us: a.us_url, a.them: a.them_url}
    reader = None if a.reader_model == "none" else _backend(a.backend, a.reader_model)
    card = build_card(
        a.us,
        a.them,
        backend,
        urls={k: v for k, v in urls.items() if v},
        pages_per_product=a.pages,
        reader=reader,
        log=lambda s: print(s, file=sys.stderr),
    )
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "card.html").write_text(render_html(card))
    (out / "card.json").write_text(json.dumps(card.to_dict(), indent=1, ensure_ascii=False))
    card.ledger.save(out / "ledger.json")
    print(panel_text(card))
    print(f"\n{out / 'card.html'}")
    return 0 if card.supported else 1


def _add_check_command(sub) -> None:
    """The `check` command and its options."""
    c = sub.add_parser("check", help="check claims against a ledger; exit 1 when any is unsupported")
    c.add_argument("claims", help="a JSON file: a list of {id, text, quote, evidence_id, subject}")
    c.add_argument("--ledger", required=True)
    c.add_argument("--max-age-days", type=int, help="flag claims whose page was read longer ago than this")
    c.add_argument("--json", action="store_true")
    c.add_argument("--code-only", action="store_true", help="skip the reader: no model, and a weaker check")
    c.add_argument("--reader-model", default="haiku", help="the model that reads each claim against its sentence")
    c.add_argument("--backend", choices=["claude-code", "anthropic"], default="claude-code")
    c.set_defaults(run=_check)


def _add_card_command(sub) -> None:
    """The `card` command and its options."""
    b = sub.add_parser("card", help="build a battle card from pages about two products")
    b.add_argument("--us", required=True, help="the product you sell")
    b.add_argument("--them", required=True, help="the competitor")
    b.add_argument(
        "--us-url", action="append", help="a page about your product (repeatable); found by search when absent"
    )
    b.add_argument("--them-url", action="append", help="a page about the competitor (repeatable)")
    b.add_argument("--pages", type=int, default=4, help="pages per product (default 4)")
    b.add_argument("--backend", choices=["claude-code", "anthropic"], default="claude-code")
    b.add_argument("--model")
    b.add_argument(
        "--reader-model",
        default="haiku",
        help='the model that reads facts against quotes; "none" for the code check only',
    )
    b.add_argument("--out", default="out")
    b.set_defaults(run=_card)


def _mcp(a: argparse.Namespace) -> int:
    from .mcp_server import serve

    return serve(None if a.code_only else _backend(a.backend, a.reader_model))


def main(argv: list[str] | None = None) -> int:
    """Parse the command line and run the command. Returns the exit code."""
    p = argparse.ArgumentParser(
        prog="receipts", description="Every claim carries a quote from a page that code fetched, or it is cut."
    )
    sub = p.add_subparsers(dest="command", required=True)

    _add_check_command(sub)

    f = sub.add_parser("fetch", help="read pages into a ledger")
    f.add_argument("urls", nargs="+")
    f.add_argument("--ledger", required=True)
    f.set_defaults(run=_fetch)

    u = sub.add_parser("audit", help="count the specifics in a text and how many can be checked")
    u.add_argument("file")
    u.add_argument("--ledger", help="the pages the text was written from, to trace figures against")
    u.add_argument("--json", action="store_true")
    u.set_defaults(run=_audit)

    _add_card_command(sub)
    m = sub.add_parser("mcp", help='serve the check over MCP (pip install -e ".[mcp]")')
    m.add_argument("--code-only", action="store_true", help="skip the reader: no model, and a weaker check")
    m.add_argument("--reader-model", default="haiku")
    m.add_argument("--backend", choices=["claude-code", "anthropic"], default="claude-code")
    m.set_defaults(run=_mcp)

    a = p.parse_args(argv)
    try:
        return int(a.run(a) or 0)
    except (OSError, ValueError, BackendError) as e:  # a missing or malformed file, a model that cannot be reached
        print(f"receipts: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
