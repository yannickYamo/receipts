import asyncio
import sys

import pytest

pytest.importorskip("mcp")


def test_mcp_server_checks_claims_over_stdio():
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    async def run():
        params = StdioServerParameters(command=sys.executable, args=["-m", "receipts.cli", "mcp"])
        async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
            await session.initialize()
            names = {t.name for t in (await session.list_tools()).tools}
            result = await session.call_tool(
                "check_claims_tool",
                {
                    "claims": [
                        {
                            "text": "Acme costs $5",
                            "quote": "Acme costs $5 per month.",
                            "evidence_id": "e-unknown",
                            "subject": "Acme",
                        }
                    ]
                },
            )
            return names, result

    names, result = asyncio.run(run())
    assert names == {"read_page", "check_claims_tool"}
    assert (
        not getattr(result, "is_error", getattr(result, "isError", False)) and '"no_evidence"' in result.content[0].text
    )
