# receipts

[![CI](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml/badge.svg)](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml)

**A guard for AI agents that research the web. Every claim carries a quote from a page that code fetched, or it is cut.**

Give it an agent's claims and the pages they came from → get back only the claims a page really states, each with its quote, its link and the reason anything was cut.

![A battle card where every line opens to its quote and page](docs/card.png)

## What it is

receipts is a small open-source Python package. It sits between an AI agent and the person who will act on what the agent found.

The agent researches the web and writes claims. receipts keeps a claim only when it can point to the sentence on the page that states it. Everything else is cut, and you get the list of what was cut and why.

No dependencies in the core. Python 3.10 or later. MIT license.

## Why use it

- **You can repeat what the agent told you.** Each claim that survives comes with the exact quote, the link and the date the page was read.
- **You stop re-doing the research.** Checking a claim is one click on its quote, not a new search.
- **Invented prices and figures don't reach your customer.** A figure that isn't in the quoted sentence is cut, not reworded.
- **You see what was left out.** Every cut claim is listed with its reason, and every page that could not be read is named.
- **It works with what you already have.** It checks the output of any agent and takes page text from any fetcher.
- **It's cheap.** The reader is a small model: reading 120 claims cost $0.17 at list price.

Who it's for: a sales rep or product marketer who has to trust a battle card. An engineer shipping an agent whose answers people will act on. Anyone who has pasted an agent's research into a document and then spent an hour checking it.

## How to use it

**Step 1, install.**

```bash
git clone https://github.com/yannickYamo/receipts && cd receipts
pip install -e .
```

**Step 2, check claims against a page.** The command exits with code 1 when any claim is unsupported, so it can stop a pipeline.

```bash
receipts fetch https://www.freshworks.com/freshdesk/pricing/ --ledger ledger.json
receipts check claims.json --ledger ledger.json
```

What you see:

```text
PASS a  Freshdesk Growth plan costs $19/agent/month, billed annually.
CUT  b  Freshdesk Growth plan costs $15/agent/month, billed annually.
       the claim states a figure the quote does not (15)
```

**Step 3, or use it from Python.**

```python
from receipts import Claim, Ledger, check_claims

ledger = Ledger()
page = ledger.add_url("https://www.freshworks.com/freshdesk/pricing/")
claim = Claim("a", text="Freshdesk Growth costs $19 per agent per month, billed annually",
              quote="Growth ... $19 /agent/month, billed annually", evidence_id=page.id, subject="Freshdesk")
report = check_claims([claim], ledger)
report.supported, report.cut, report.by_reason
```

Other ways in:

- Add the reader stage: `receipts.reader.check_with_reader(claims, ledger, backend)`.
- Let an agent check itself: `receipts mcp` is an MCP server (install with `pip install -e ".[mcp]"`) with two tools, `read_page` and `check_claims_tool`. The agent cannot hand in page text of its own.
- Audit someone else's output: `receipts audit card.html` counts the specifics in any text and how many sit on a line with a link.

## How it works

**A model may point at evidence; only code may vouch for it.**

```text
  a web page                     a model's claim
      |                          "Growth costs $19"  + quote + page id
      v                                  |
+-------------+                          v
|   fetch     |   page text      +----------------+     fails     +---------------+
|  (code)     |----------------->|   code check   |-------------->|  cut, with    |
+-------------+   date, hash     |  quote on page |               |  the reason   |
                                 |  figures match |               +---------------+
                                 |  right subject |                       ^
                                 +----------------+                       |
                                         | passes                         |
                                         v                                |
                                 +----------------+      "no"             |
                                 |    reader      |-----------------------+
                                 | (small model)  |   or no answer
                                 | may only cut   |
                                 +----------------+
                                         | "yes"
                                         v
                              the claim, its quote, its link
```

The steps in words:

1. **Code fetches the page.** The text in the ledger is what the site served, with a date and a hash. The model never supplies it.
2. **The model may only point.** Each claim names a page and quotes it.
3. **Code decides what code can decide:** the quote is on that page word for word, every figure in the claim is in the quote, and the page is about the right product.
4. **A small reader model decides the rest, and may only cut.** Code first widens the quote to the whole sentence it sits in on the page, so a clipped quote can't hide the words around it ("$425" cut out of "$425 million"). The reader answers one question: does that sentence state everything the claim states? A claim the reader could not read is cut too.
5. **What fails is cut, never reworded,** and listed with the reason.

## Example: a battle card a sales rep can check

One command:

```bash
receipts card --us Freshdesk --them Zendesk --out out/
```

It finds pages about both products, fetches them, lists facts with quotes, checks them, writes the card's lines from the facts that survived, checks the lines, and lays the page out from a fixed template. No model writes the HTML. Every line on the card opens to its quote, its page and the date the page was read. The top of the card says what was read and what was cut.

From a real run (the card is in the repository at bench/live/run5/card.html):

```text
sources   5 pages read · 2 could not be read
facts     34 of 48 supported by a quote on the page it names · 14 cut (4 beyond quote, 8 not stated, 1 polarity mismatch, 1 figure not in quote)
lines     19 of 23 kept · 4 cut
on this card: every line links to the page and quote it rests on
```

Lines from that card. Where we win: "Freshdesk publishes clear per-agent prices, billed annually: Growth $19, Pro $55, Enterprise $89." Where they win, because the facts say so: "Zendesk claims its AI Agents can achieve up to 80% automation. It also includes built-in QA scoring for 100% of AI interactions." A response to the objection "Zendesk says its AI can automate up to 80%": "That is their 'up to' claim. With Freshdesk, the Freddy AI Agent is on every plan with 500 complimentary AI sessions, so you can test it on your own tickets."

The card command uses the local `claude` command by default, so it runs on a Claude Code login.

## Why I built it

I kept hitting the same wall. An agent that researches the web hands me fluent prose full of prices, ratings and customer counts. Some are right. I can't tell which without redoing the research, so the time the agent saved comes back as checking.

The example that made me build this is the AI Sales Intelligence Agent Team by Shubham Saboo in the awesome-llm-apps collection (https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_ai_agents/multi_agent_apps/agent_teams/ai_sales_intelligence_agent_team). It's a good, clear example of a seven-agent pipeline that writes a sales battle card. I ran its prompts on its own sample request, "Help me compete against Zendesk, I sell Freshdesk" (on Claude Sonnet, not on Gemini as the original does). The card it wrote has 175 specifics that a pattern can find: prices, ratings, counts, dates. Not one sits on a line with a link. The model wrote VERIFY on its own output 23 times.

I did not show its figures are wrong: the Zendesk list prices it gave match Zendesk's pricing page. The point is that a sales rep can't tell which ones are right, because prose passes from agent to agent and no address survives to the card. A rep who repeats one wrong price in front of a prospect loses the room.

The check itself comes from my other project, Atelier (https://github.com/yannickYamo/atelier), where an invented-claim check works on the same idea: a small model reads, code decides. receipts applies it to web research, where the evidence is a page instead of the author's own notes.

## How it compares

receipts isn't a scraper, a search engine or an eval dashboard. It does one job the others leave open: it checks each claim against the page it cites and removes the ones the page doesn't state. What I say about each tool below is from its own documentation as I read it on 2026-10-04.

| Tool | What it is for | Does it check a claim against the page it cites? |
|---|---|---|
| [Firecrawl](https://docs.firecrawl.dev/introduction), [Jina Reader](https://jina.ai/reader/) | Getting the page: scrape, crawl, search. They handle JavaScript rendering, proxies and anti-bot | No. They are fetchers, and better ones than the fetcher in receipts |
| [Tavily](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Exa](https://exa.ai/docs/reference/answer), [Perplexity Sonar](https://docs.perplexity.ai/docs/sonar/quickstart), [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search) | Finding pages and answering with a list of sources | No. A citation is a source the answer used, not a quote that was checked |
| [Anthropic Citations](https://platform.claude.com/docs/en/build-with-claude/citations) | Claude cites exact passages from documents you supply | Partly. The cited text is guaranteed to be in the document. Whether it supports the claim is not checked, and nothing is removed |
| [Guardrails AI provenance](https://guardrailsai.com/hub/validator/guardrails/provenance_llm), [NeMo Guardrails fact-checking](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/fact-checking) | A guard in the loop: a model judges whether text is supported by sources | Partly. It is a model's judgment with no verbatim quote. NeMo blocks the whole reply below a score |
| [Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/), [DeepEval](https://deepeval.com/docs/metrics-faithfulness) faithfulness | Evaluation: the share of claims an LLM judge finds supported, as a score | Partly. They score the output. They do not edit it |
| **receipts** | Checking: each claim tied to a verbatim quote on a page that code fetched | Yes. Unsupported claims are cut and listed with the reason |

They work together. Firecrawl gets pages that receipts' own fetcher cannot (pages that need JavaScript, sites that refuse a plain request). Hand its text to the ledger and receipts checks against it.

```python
ledger = Ledger()
page = ledger.add_text(url, text_from_any_fetcher, title)   # Firecrawl, Jina Reader, your own crawler
report = check_claims(claims, ledger)
```

A search tool finds the pages. A fetcher reads them. receipts decides what the agent is allowed to say about them.

## What it does not do yet

- **It cuts some true facts.** On real pricing pages it cut about one true fact in four, mostly a price quoted without its plan name. Cutting a true line costs a line. Keeping a false one costs the rep the room. It's built for the second.
- **It doesn't stop someone who writes claims to beat it.**
- **It doesn't know whether a page is right.** A wrong page gives a well-sourced wrong claim.
- **Its own fetcher is basic:** no JavaScript, and sites that refuse the request are not read. The card says which pages it couldn't read.

How it was tested, with the failures kept in: [EVALS.md](EVALS.md).

## Project structure

```text
src/receipts/core.py         the code check          src/receipts/reader.py      the reader stage
src/receipts/ledger.py       pages, dates, hashes    src/receipts/audit.py       count specifics in any text
src/receipts/battlecard/     the worked example      src/receipts/mcp_server.py  the check as an MCP server
bench/                       test sets, red-team sets, labels, saved model answers, live runs
studies/                     the pre-registrations, the evaluation plan and the full results
EVALS.md                     what was tested, what passed and what failed
```

License: MIT. The bench corpus is Wikipedia text, CC BY-SA 4.0.
