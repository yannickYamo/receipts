"""Where the model calls go. The pipeline asks for JSON and for addresses to read; nothing else.

  ScriptedBackend     answers from a list, for tests: no model, no network
  ClaudeCodeBackend   the local `claude` command in print mode, for running on a Claude Code login
  AnthropicBackend    the Anthropic API (pip install claim-receipts[anthropic]); needs credentials

A backend never supplies evidence. It may name addresses; code fetches them (fetch.py).
"""

from __future__ import annotations

import json
import os
import subprocess
from collections.abc import Callable
from typing import Any, Protocol

URLS_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["urls"],
    "properties": {"urls": {"type": "array", "items": {"type": "string"}}},
}
FIND_SYSTEM = (
    "You find the public web pages that state facts about a software product. Search the web, then "
    "return addresses only. List the vendor's own pricing page first, then its features or product page, its "
    "integrations or documentation page, and one independent page with reviews or company facts. "
    "Return full https addresses of pages that exist in your search results. Do not guess an address."
)


class Backend(Protocol):
    """What the pipeline needs from a model: JSON that fits a schema, and addresses to read."""

    name: str
    calls: int
    cost_usd: float

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Answer `prompt` as JSON that fits `schema`."""
        ...

    def find_urls(self, product: str, limit: int) -> list[str]:
        """Name up to `limit` public pages about `product`."""
        ...


class ScriptedBackend:
    """Replies in order from `replies` (dicts, or functions of the prompt). `urls` answers find_urls."""

    def __init__(self, replies: list[dict | Callable[[str], dict]], urls: dict[str, list[str]] | None = None) -> None:
        self.name = "scripted"
        self.calls = 0
        self.cost_usd = 0.0
        self._replies = list(replies)
        self._urls = urls or {}
        self.prompts: list[str] = []

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Answer `prompt` as JSON that fits `schema`."""
        self.calls += 1
        self.prompts.append(prompt)
        reply = self._replies.pop(0)
        return reply(prompt) if callable(reply) else reply

    def find_urls(self, product: str, limit: int) -> list[str]:
        """Name up to `limit` public pages about `product`."""
        return self._urls.get(product, [])[:limit]


class BackendError(Exception):
    """A model call that failed or returned nothing usable."""


class ClaudeCodeBackend:
    """Runs `claude -p` with a JSON schema. No tools for reading; web search only when finding addresses."""

    def __init__(self, model: str = "sonnet", timeout: int = 300) -> None:
        self.name = f"claude-code ({model})"
        self.model = model
        self.timeout = timeout
        self.calls = 0
        self.cost_usd = 0.0  # what the command reports, at list price

    def _call(self, system: str, prompt: str, schema: dict | None, tools: str) -> dict:
        cmd = [
            "claude",
            "-p",
            "--model",
            self.model,
            "--output-format",
            "json",
            "--tools",
            tools,
            "--no-session-persistence",
            "--disable-slash-commands",
            "--strict-mcp-config",
            "--setting-sources",
            "",
            "--system-prompt",
            system,
        ]
        if schema is not None:
            cmd += ["--json-schema", json.dumps(schema)]
        if tools:
            cmd += ["--allowedTools", tools]
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}
        try:
            done = subprocess.run(cmd, input=prompt, capture_output=True, text=True, timeout=self.timeout, env=env)
        except (OSError, subprocess.TimeoutExpired) as e:
            raise BackendError(f"the claude command did not finish: {e}") from e
        self.calls += 1
        try:
            reply = json.loads(done.stdout)
        except json.JSONDecodeError as e:
            raise BackendError(f"the claude command returned no JSON: {(done.stderr or done.stdout)[:300]}") from e
        self.cost_usd += float(reply.get("total_cost_usd") or 0)
        return reply

    def _run(self, system: str, prompt: str, schema: dict, tools: str) -> dict:
        reply = self._call(system, prompt, schema, tools)
        out = reply.get("structured_output")
        if reply.get("is_error") or not isinstance(out, dict):
            raise BackendError(f"the claude command returned no structured output: {str(reply.get('result'))[:300]}")
        return out

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Answer `prompt` as JSON that fits `schema`."""
        return self._run(system, prompt, schema, "")

    def text(self, system: str, prompt: str, web_search: bool = False) -> str:
        """Plain prose, optionally with web search. Used by the baseline arm in bench/, not by the pipeline."""
        reply = self._call(system, prompt, None, "WebSearch" if web_search else "")
        if reply.get("is_error") or not isinstance(reply.get("result"), str):
            raise BackendError(f"the claude command returned no text: {str(reply)[:300]}")
        return reply["result"]

    def find_urls(self, product: str, limit: int) -> list[str]:
        """Name up to `limit` public pages about `product`."""
        out = self._run(FIND_SYSTEM, f"Product: {product}\nReturn at most {limit} addresses.", URLS_SCHEMA, "WebSearch")
        return [u for u in out.get("urls", []) if isinstance(u, str)][:limit]


class AnthropicBackend:
    """The Anthropic API, with structured output. Not exercised by the test suite: it needs credentials."""

    def __init__(self, model: str = "claude-opus-5-5", client: Any = None) -> None:
        if client is None:
            import anthropic  # an optional dependency

            client = anthropic.Anthropic()
        self.client = client
        self.model = model
        self.name = f"anthropic ({model})"
        self.calls = 0
        self.cost_usd = 0.0  # not computed here: read it from the Console

    def _create(self, system: str, prompt: str, schema: dict, tools: list[dict] | None = None) -> dict:
        messages: list[dict] = [{"role": "user", "content": prompt}]
        for _ in range(4):  # a server-tool turn can pause; resume it a few times at most
            kw: dict[str, Any] = {"tools": tools} if tools else {}
            response = self.client.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=messages,
                output_config={"format": {"type": "json_schema", "schema": schema}},
                **kw,
            )
            self.calls += 1
            if response.stop_reason == "refusal":
                raise BackendError("the model declined the request")
            if response.stop_reason != "pause_turn":
                texts = [b.text for b in response.content if b.type == "text"]
                return json.loads(texts[-1]) if texts else {}
            messages.append({"role": "assistant", "content": response.content})
        raise BackendError("the search did not finish")

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Answer `prompt` as JSON that fits `schema`."""
        return self._create(system, prompt, schema)

    def find_urls(self, product: str, limit: int) -> list[str]:
        """Name up to `limit` public pages about `product`."""
        out = self._create(
            FIND_SYSTEM,
            f"Product: {product}\nReturn at most {limit} addresses.",
            URLS_SCHEMA,
            tools=[{"type": "web_search_20260209", "name": "web_search", "max_uses": 4}],
        )
        return [u for u in out.get("urls", []) if isinstance(u, str)][:limit]
