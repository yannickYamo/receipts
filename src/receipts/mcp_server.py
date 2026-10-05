"""The check as an MCP server, so an agent can check its own claims before it answers.

    pip install -e ".[mcp]"
    receipts mcp               # stdio, both stages (the reader runs on the local `claude` command)
    receipts mcp --code-only   # the code check alone: no model, and weaker

Two tools. `read_page` fetches a page into this session's ledger and returns its id and text, a part
at a time when the page is long. `check_claims` decides claims against the pages read. The agent cannot hand in page text of its own:
evidence is only what this server fetched.
"""

from __future__ import annotations

from . import Claim, Ledger, check_claims
from .backends import Backend
from .core import Evidence
from .fetch import FetchError
from .reader import READER_VERSION, check_with_reader

PART = 40_000  # characters of a page returned by one read_page call


def page_part(ev: Evidence, offset: int = 0) -> dict:
    """One part of a page for the agent, with the page's full length and where the next part starts, if any."""
    start = max(0, offset)
    out = {
        "evidence_id": ev.id,
        "title": ev.title,
        "fetched_at": ev.fetched_at,
        "text": ev.text[start : start + PART],
        "characters": len(ev.text),
    }
    return out | ({"next_offset": start + PART} if start + PART < len(ev.text) else {})


def build_server(reader: Backend | None = None):
    """Build the MCP server with its two tools. The ledger lives for the life of the server.

    With a `reader`, every check runs both stages. Without one it runs the code check alone, and each
    result says so: that stage cannot tell a claim that keeps a quote's words and changes their meaning.
    """
    try:  # mcp 2.x renamed FastMCP to MCPServer; both take the same decorators
        from mcp.server.mcpserver import MCPServer as Server  # pyright: ignore
    except ImportError:
        from mcp.server.fastmcp import FastMCP as Server  # pyright: ignore

    server = Server("receipts")
    ledger = Ledger()

    @server.tool()
    def read_page(url: str, offset: int = 0) -> dict:
        """Fetch a web page as evidence. Returns its evidence_id and text. Quote from this text exactly.

        A long page comes back in parts of 40,000 characters. When the result has `next_offset`, there is
        more: call again with the same url and that offset. The page is fetched once; a quote from any
        part of it can be checked."""
        ev = next((e for e in reversed(list(ledger.values())) if e.url == url), None) if offset else None
        if ev is None:
            try:
                ev = ledger.add_url(url)
            except FetchError as e:
                return {"error": f"could not read {url}: {e}"}
        return page_part(ev, offset)

    @server.tool()
    def check_claims_tool(claims: list[dict]) -> dict:
        """Check claims before stating them. Each claim: {text, quote, evidence_id, subject}. The quote must be
        copied exactly from a page returned by read_page. Returns, per claim, supported or the reason it is
        not. State only the supported ones; drop the rest, do not reword them. A claim cut because its quote
        does not carry it may be sent once more with another quote from the same page, its text unchanged."""
        cs = [
            Claim(
                str(c.get("id") or f"c{i + 1}"),
                str(c.get("text") or ""),
                str(c.get("quote") or ""),
                str(c.get("evidence_id") or ""),
                str(c.get("subject") or ""),
            )
            for i, c in enumerate(claims)
        ]
        if reader is None:
            return check_claims(cs, ledger).to_dict() | {"stages": "code check only: the reader did not run"}
        report = check_with_reader(cs, ledger, reader)
        return report.to_dict() | {"stages": f"code check, then reader ({reader.name}, prompt {READER_VERSION})"}

    return server


def serve(reader: Backend | None = None) -> int:
    """Run the MCP server on stdio, with `reader` as the second stage when one is given."""
    build_server(reader).run()
    return 0
