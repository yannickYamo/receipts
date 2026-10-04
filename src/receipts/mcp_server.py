"""The check as an MCP server, so an agent can check its own claims before it answers.

    pip install claim-receipts[mcp]
    receipts mcp               # stdio, both stages (the reader runs on the local `claude` command)
    receipts mcp --code-only   # the code check alone: no model, and weaker

Two tools. `read_page` fetches a page into this session's ledger and returns its id and text.
`check_claims` decides claims against the pages read. The agent cannot hand in page text of its own:
evidence is only what this server fetched.
"""

from __future__ import annotations

from . import Claim, Ledger, check_claims
from .backends import Backend
from .fetch import FetchError
from .reader import READER_VERSION, check_with_reader


def build_server(reader: Backend | None = None):
    """Build the MCP server with its two tools. The ledger lives for the life of the server.

    With a `reader`, every check runs both stages. Without one it runs the code check alone, and each
    result says so: that stage cannot tell a claim that keeps a quote's words and changes their meaning.
    """
    try:  # mcp 2.x renamed FastMCP to MCPServer; both take the same decorators
        from mcp.server.mcpserver import MCPServer as Server
    except ImportError:
        from mcp.server.fastmcp import FastMCP as Server

    server = Server("receipts")
    ledger = Ledger()

    @server.tool()
    def read_page(url: str) -> dict:
        """Fetch a web page as evidence. Returns its evidence_id and text. Quote from this text exactly."""
        try:
            ev = ledger.add_url(url)
        except FetchError as e:
            return {"error": f"could not read {url}: {e}"}
        return {"evidence_id": ev.id, "title": ev.title, "fetched_at": ev.fetched_at, "text": ev.text[:40_000]}

    @server.tool()
    def check_claims_tool(claims: list[dict]) -> dict:
        """Check claims before stating them. Each claim: {text, quote, evidence_id, subject}. The quote must be
        copied exactly from a page returned by read_page. Returns, per claim, supported or the reason it is
        not. State only the supported ones; drop the rest, do not reword them."""
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
