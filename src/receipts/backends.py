"""Where the model calls go. The pipeline asks for JSON and for addresses to read; nothing else.

  ScriptedBackend     answers from a list, for tests: no model, no network
  ClaudeCodeBackend   the local `claude` command in print mode, for running on a Claude Code login
  AnthropicBackend    the Anthropic API (pip install -e ".[anthropic]"); needs credentials
  OpenAIBackend       any API that speaks OpenAI's chat completions: OpenAI, xAI and others; needs a key

The check does not care which model wrote a claim, and the reader can be any of these. The reader's
measured rates hold only for the model and prompt version they were measured on (bench/).

A backend never supplies evidence. It may name addresses; code fetches them (fetch.py).
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request
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


# The short names the `claude` command takes, as the API's model ids. The API does not know "haiku".
API_MODELS = {"haiku": "claude-haiku-4-5-20251001", "sonnet": "claude-sonnet-5-5", "opus": "claude-opus-5-5"}


def api_model(name: str) -> str:
    """The API's id for a model name. A name that is not a Claude model at all raises ValueError before any work.

    A full id is passed as given: which ids exist changes with every model release and with the route
    to the API, so a mistyped one comes back as the API's own error, with exit code 3.
    """
    if name in API_MODELS:
        return API_MODELS[name]
    if name.startswith("claude-"):
        return name
    known = ", ".join(API_MODELS)
    raise ValueError(
        f'"{name}" is not a model the Anthropic API takes: use {known}, or a full id such as claude-opus-5-5'
    )


class AnthropicBackend:
    """The Anthropic API, with structured output. The tests run it against a stand-in client, never the live API."""

    def __init__(self, model: str = "opus", client: Any = None) -> None:
        self.model = api_model(model)
        if client is None:
            try:
                import anthropic  # an optional dependency  # pyright: ignore[reportMissingImports]
            except ImportError as e:
                raise BackendError('the anthropic package is not installed: pip install -e ".[anthropic]"') from e
            try:
                client = anthropic.Anthropic()
            except Exception as e:  # no credentials
                raise BackendError(f"the Anthropic client could not start: {e}") from e
        self.client = client
        self.name = f"anthropic ({self.model})"
        self.calls = 0
        self.cost_usd = 0.0  # not computed here: read it from the Console

    def _create(self, system: str, prompt: str, schema: dict, tools: list[dict] | None = None) -> dict:
        messages: list[dict] = [{"role": "user", "content": prompt}]
        for _ in range(4):  # a server-tool turn can pause; resume it a few times at most
            kw: dict[str, Any] = {"tools": tools} if tools else {}
            try:
                response = self.client.messages.create(
                    model=self.model,
                    max_tokens=16000,
                    system=system,
                    messages=messages,
                    output_config={"format": {"type": "json_schema", "schema": schema}},
                    **kw,
                )
            except Exception as e:  # every failure of the API, typed or not, is one thing to the pipeline
                raise BackendError(f"the API call failed: {e}") from e
            self.calls += 1
            if response.stop_reason == "refusal":
                raise BackendError("the model declined the request")
            if response.stop_reason != "pause_turn":
                texts = [b.text for b in response.content if b.type == "text"]
                try:
                    return json.loads(texts[-1]) if texts else {}
                except json.JSONDecodeError as e:  # a reply cut short
                    raise BackendError("the model's reply was not complete JSON") from e
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


class OpenAIBackend:
    """An API that speaks OpenAI's chat completions with a JSON schema: OpenAI itself, xAI, and others.

    The key is read from OPENAI_API_KEY and the address from OPENAI_BASE_URL (default: OpenAI's). For
    xAI, set OPENAI_BASE_URL=https://api.x.ai/v1 and put the xAI key in OPENAI_API_KEY. The model name
    is passed as given: a name the API does not know comes back as that API's own error.
    """

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: int = 300,
        post: Callable[[str, dict, dict], dict] | None = None,
    ) -> None:
        self.model = model
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or ""
        if not self.api_key and post is None:
            raise BackendError("no key for the OpenAI-compatible API: set OPENAI_API_KEY")
        self.timeout = timeout
        self.name = f"openai-compatible ({model} at {self.base_url.split('//')[-1]})"
        self.calls = 0
        self.cost_usd = 0.0  # not computed here: prices differ by provider
        self.tokens = {"input": 0, "output": 0}
        self._post = post or self._http_post

    def _http_post(self, url: str, headers: dict, body: dict) -> dict:
        req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:  # noqa: S310 - the operator's own API address
                return json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            raise BackendError(f"the API answered {e.code}: {e.read().decode('utf-8', 'replace')[:300]}") from e
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as e:
            raise BackendError(f"the API call failed: {e}") from e

    def json(self, system: str, prompt: str, schema: dict) -> dict:
        """Answer `prompt` as JSON that fits `schema`."""
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}],
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "reply", "strict": True, "schema": schema},
            },
        }
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        reply = self._post(f"{self.base_url}/chat/completions", headers, body)
        self.calls += 1
        try:
            message = reply["choices"][0]["message"]
            usage = reply.get("usage") or {}
            self.tokens["input"] += int(usage.get("prompt_tokens") or 0)
            self.tokens["output"] += int(usage.get("completion_tokens") or 0)
            if message.get("refusal"):
                raise BackendError("the model declined the request")
            out = json.loads(message["content"])
        except (KeyError, IndexError, TypeError, ValueError) as e:
            raise BackendError(f"the API returned no usable JSON: {str(reply)[:300]}") from e
        if not isinstance(out, dict):
            raise BackendError("the API returned JSON that is not an object")
        return out

    def find_urls(self, product: str, limit: int) -> list[str]:
        """This backend has no web search: the caller passes the pages."""
        raise BackendError("this backend cannot search the web: pass the pages with --us-url and --them-url")
