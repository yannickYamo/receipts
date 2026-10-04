"""The baseline arm: the upstream example's own prompts, run as it runs them, on a Claude model.

Upstream: Shubhamsaboo/awesome-llm-apps, ai_sales_intelligence_agent_team (Apache-2.0), pinned to one
commit. Its prompts are read from that commit at run time, not copied here. The pipeline is the same
straight line: research, features, positioning, strengths and weaknesses, objections, then the HTML
card written by a model. Stage 7 (an image) is left out.

What differs from upstream, and is said wherever the result is shown: the model is Claude Sonnet through
the local `claude` command, not Gemini through Google ADK, and the search tool is Claude Code's.

    python bench/baseline/run.py "Help me compete against Zendesk, I sell Freshdesk" bench/baseline/freshdesk-vs-zendesk
"""

import ast
import json
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

from receipts.backends import ClaudeCodeBackend

COMMIT = "4b2ac4a47c063bd30402b1a49181a0b4d6bd978b"
BASE = (
    "https://raw.githubusercontent.com/Shubhamsaboo/awesome-llm-apps/{commit}/advanced_ai_agents/multi_agent_apps/"
    "agent_teams/ai_sales_intelligence_agent_team/{file}"
)


def source(name: str) -> ast.Module:
    with urllib.request.urlopen(BASE.format(commit=COMMIT, file=name), timeout=30) as r:
        return ast.parse(r.read().decode())


def stages() -> list[dict]:
    """Each LlmAgent in upstream agent.py that has an output_key, in file order: its prompt, tools and key."""
    out = []
    for node in ast.walk(source("agent.py")):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "LlmAgent":
            kw = {k.arg: k.value for k in node.keywords}
            if "output_key" in kw:
                out.append(
                    {
                        "line": node.lineno,
                        "name": kw["name"].value,
                        "instruction": kw["instruction"].value,
                        "key": kw["output_key"].value,
                        "search": "google_search" in ast.unparse(kw.get("tools", ast.List([]))),
                    }
                )
    return sorted(out, key=lambda s: s["line"])


def html_prompt(data: str) -> str:
    """The f-string prompt inside upstream tools.generate_battle_card_html, filled in."""
    for node in ast.walk(source("tools.py")):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "generate_battle_card_html":
            fstring = next(n.value for n in ast.walk(node) if isinstance(n, ast.Assign) and n.targets[0].id == "prompt")
            values = {"current_date": datetime.now().strftime("%B %d, %Y"), "battle_card_data": data}
            return "".join(v.value if isinstance(v, ast.Constant) else values[v.value.id] for v in fstring.values)
    raise SystemExit("upstream tools.py has changed shape")


def main() -> None:
    request, out = sys.argv[1], Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    backend = ClaudeCodeBackend("sonnet", timeout=600)
    state: dict[str, str] = {}
    for s in stages():
        if s["key"] == "chart_result":
            continue
        system = s["instruction"]
        for key, value in state.items():
            system = system.replace("{" + key + "}", value)
        if s["key"] == "battle_card_result":
            # Upstream: the agent compiles the data and passes it to a tool, and the tool has a model write the page.
            data = backend.text(
                system
                + "\n\nYou have no tool here. Output the compiled data that you would pass to it, and nothing else.",
                request,
            )
            html = backend.text("You output only what is asked.", html_prompt(data))
            if "```" in html:
                html = html.split("```html")[-1].split("```")[0] if "```html" in html else html.split("```")[1]
            (out / "card.html").write_text(html.strip())
            state[s["key"]] = data
        else:
            state[s["key"]] = backend.text(system, request, web_search=s["search"])
        print(s["name"], len(state[s["key"]]), "characters", file=sys.stderr)
    (out / "state.json").write_text(json.dumps(state, indent=1))
    (out / "run.json").write_text(
        json.dumps(
            {
                "request": request,
                "upstream_commit": COMMIT,
                "model": backend.name,
                "calls": backend.calls,
                "cost_usd_list_price": round(backend.cost_usd, 4),
            },
            indent=1,
        )
    )


if __name__ == "__main__":
    main()
