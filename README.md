# receipts

[![CI](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml/badge.svg)](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml)

**Every claim your agent makes carries a quote from a page that code fetched, or it gets cut. receipts is a small Python package that enforces that rule on an agent's research output. A model may point at evidence; only code may vouch for it.**

![A battle card where every line opens to its quote and page](docs/card.png)

Repo: https://github.com/yannickYamo/receipts · MIT · Python 3.10+ · core has no dependencies.

You hand it an agent's claims and the pages those claims name. You get back only the claims a page actually states, each with its quote, its link, and the date it was read. You also get a list of everything that was cut, with the reason, and the name of every page that couldn't be read.

## Why you'd want this

The failure I kept hitting is the one that makes agent research expensive: a model hands you fluent prose full of prices, ratings, and customer counts. Some of it is right. You can't tell which part without doing the research again. The time the agent saved comes back as checking time.

receipts is for three people. The sales rep or product marketer who has to trust a battle card in front of a prospect. The engineer shipping an agent whose answers people act on. And anyone who has pasted agent research into a doc and then spent an hour verifying it line by line.

What you get, concretely:

- **You can repeat what the agent said.** A surviving claim is an exact quote plus a link plus a date read.
- **You don't redo the research.** Checking is one click on the quote.
- **Invented figures don't reach the customer.** If a figure isn't in the quoted sentence, the claim is cut, never reworded into something softer.
- **You see what was left out.** Every cut is listed with its reason; every unreadable page is named.
- **It works with any agent's output** and page text from any fetcher.
- **It's cheap.** The reader stage is a small model (claude-haiku-4-5). 120 claims read cost $0.17 at list price.

## How to use it

```bash
git clone https://github.com/yannickYamo/receipts && cd receipts
pip install -e .
```

Fetch a page into a ledger, then check claims against it:

```bash
receipts fetch https://www.freshworks.com/freshdesk/pricing/ --ledger ledger.json
receipts check claims.json --ledger ledger.json
```

The output names what survived and what didn't:

```text
PASS a  Freshdesk Growth plan costs $19/agent/month, billed annually.
CUT  b  Freshdesk Growth plan costs $15/agent/month, billed annually.
       the claim states a figure the quote does not (15)
```

`check` exits with code 1 when any claim is unsupported, so it can stop a pipeline.

From Python:

```python
from receipts import Claim, Ledger, check_claims

ledger = Ledger()
page = ledger.add_url("https://www.freshworks.com/freshdesk/pricing/")
claim = Claim("a", text="Freshdesk Growth costs $19 per agent per month, billed annually",
              quote="Growth ... $19 /agent/month, billed annually", evidence_id=page.id, subject="Freshdesk")
report = check_claims([claim], ledger)
report.supported, report.cut, report.by_reason
```

The reader stage is `receipts.reader.check_with_reader(claims, ledger, backend)`. If you want the agent checking itself, `receipts mcp` runs an MCP server (`pip install -e ".[mcp]"`) exposing two tools, `read_page` and `check_claims_tool`; the agent can't hand in its own page text. To grade someone else's output, `receipts audit card.html` counts the specifics and how many of them sit on a line with a link.

## How it works

Five steps, and the split between them is the whole design.

1. **Code fetches the page** into a ledger: text as served, date, hash. The model never supplies evidence.
2. **The model may only point.** Each claim names a page and quotes it.
3. **Code checks** that the quote is on that page word for word, that every figure in the claim appears in the quote, and that the page is about the right product.
4. **The reader may only cut.** A small model reads the claim against the whole sentence the quote sits in, and answers one question: does the sentence state everything the claim states? No answer counts as no.
5. **Anything that fails is cut**, never reworded, and listed with its reason.

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

## An example: the battle card

```bash
receipts card --us Freshdesk --them Zendesk --out out/
```

It finds pages on both products, fetches them, lists facts with quotes, checks those facts, writes lines from the facts that survived, checks the lines, and lays the result out from a fixed template. No model writes the HTML. Every line on the card opens to its quote, its page, and the date read. The top of the card says what was read and what was cut. It runs on the local `claude` command by default.

A real run is in the repo at `bench/live/run5/card.html`. Its panel:

```text
sources   5 pages read · 2 could not be read
facts     34 of 48 supported by a quote on the page it names · 14 cut (4 beyond quote, 8 not stated, 1 polarity mismatch, 1 figure not in quote)
lines     19 of 23 kept · 4 cut
on this card: every line links to the page and quote it rests on
```

Lines that survived, ours: "Freshdesk publishes clear per-agent prices, billed annually: Growth $19, Pro $55, Enterprise $89." And theirs, because the facts say so: "Zendesk claims its AI Agents can achieve up to 80% automation. It also includes built-in QA scoring for 100% of AI interactions." The objection "Zendesk says its AI can automate up to 80%" gets the response: "That is their 'up to' claim. With Freshdesk, the Freddy AI Agent is on every plan with 500 complimentary AI sessions, so you can test it on your own tickets."

## Why I built it

The trigger was the [AI Sales Intelligence Agent Team](https://github.com/Shubhamsaboo/awesome-llm-apps/tree/main/advanced_ai_agents/multi_agent_apps/agent_teams/ai_sales_intelligence_agent_team) by Shubham Saboo, in awesome-llm-apps. It's a good, clear example: seven agents, writes a sales battle card. I ran its prompts on its own sample request, "Help me compete against Zendesk, I sell Freshdesk", on Claude Sonnet rather than Gemini.

The card came back with 175 specifics a pattern can find: prices, ratings, counts, dates. Zero of them sat on a line with a link. The model wrote VERIFY on its own output 23 times.

I never showed those figures were wrong. The Zendesk list prices match Zendesk's own pricing page. The problem is that a rep can't tell which ones are right, because prose passes from agent to agent and no address survives the trip. A rep who repeats one wrong price in front of a prospect loses the room.

The shape of the check comes from my other project, [Atelier](https://github.com/yannickYamo/atelier): a small model reads, code decides. receipts is that idea pointed at web research, where the evidence is a page rather than the author's notes.

Three of my own mistakes shaped the design. The first version accepted a quote of "$19" on a page that says "$199"; an independent audit caught it. The code check alone then failed its own test, scoring 43 of 50 against a bar of 45, because it can't tell "A acquired B" from "B acquired A" - which is exactly why the reader stage exists. And a red team clipped "$425" out of "$425 million" and got through, so now code widens every quote to its whole sentence before anyone reads it.

## How it compares

receipts isn't a scraper, a search engine, or an eval dashboard. The open job it takes is narrower: check each claim against the page it cites, and remove what the page doesn't state. Figures below come from each vendor's own docs, read 2026-10-04.

| Tool | What it is for | Does it check a claim against the page it cites? |
|---|---|---|
| [Firecrawl](https://docs.firecrawl.dev/introduction), [Jina Reader](https://jina.ai/reader/) | Getting the page: scrape, crawl, search. They handle JavaScript rendering, proxies and anti-bot | No. They are fetchers, and better ones than the fetcher in receipts |
| [Tavily](https://docs.tavily.com/documentation/api-reference/endpoint/search), [Exa](https://exa.ai/docs/reference/answer), [Perplexity Sonar](https://docs.perplexity.ai/docs/sonar/quickstart), [OpenAI web search](https://developers.openai.com/api/docs/guides/tools-web-search) | Finding pages and answering with a list of sources | No. A citation is a source the answer used, not a quote that was checked |
| [Anthropic Citations](https://platform.claude.com/docs/en/build-with-claude/citations) | Claude cites exact passages from documents you supply | Partly. The cited text is guaranteed to be in the document. Whether it supports the claim is not checked, and nothing is removed |
| [Guardrails AI provenance](https://guardrailsai.com/hub/validator/guardrails/provenance_llm), [NeMo Guardrails fact-checking](https://docs.nvidia.com/nemo/guardrails/configure-guardrails/guardrail-catalog/fact-checking) | A guard in the loop: a model judges whether text is supported by sources | Partly. It is a model's judgment with no verbatim quote. NeMo blocks the whole reply below a score |
| [Ragas](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/), [DeepEval](https://deepeval.com/docs/metrics-faithfulness) faithfulness | Evaluation: the share of claims an LLM judge finds supported, as a score | Partly. They score the output. They do not edit it |
| **receipts** | Checking: each claim tied to a verbatim quote on a page that code fetched | Yes. Unsupported claims are cut and listed with the reason |

These work together. Firecrawl reads pages the receipts fetcher can't: JavaScript pages, sites that refuse a plain request. Hand its text to the ledger:

```python
ledger = Ledger()
page = ledger.add_text(url, text_from_any_fetcher, title)   # Firecrawl, Jina Reader, your own crawler
report = check_claims(claims, ledger)
```

A search tool finds the pages, a fetcher reads them, receipts decides what the agent may say about them.

## What it doesn't do yet

**It cuts some true facts.** About one true fact in four on real pricing pages, usually a price quoted without its plan name. Cutting a true line costs you a line; keeping a false one costs the rep the room. It's built for the second.

**It doesn't stop an adversary.** Someone writing claims specifically to beat the check can beat it.

**It doesn't know whether a page is right.** A wrong page gives you a well-sourced wrong claim.

**Its own fetcher is basic.** No JavaScript, and sites that refuse aren't read. G2 and Capterra answered 403 in every live run. The card names the pages it couldn't read.

What was tested, what passed and what failed, with the failures kept in, is in [EVALS.md](EVALS.md).

## Structure

```text
src/receipts/core.py         the code check          src/receipts/reader.py      the reader stage
src/receipts/ledger.py       pages, dates, hashes    src/receipts/audit.py       count specifics in any text
src/receipts/battlecard/     the worked example      src/receipts/mcp_server.py  the check as an MCP server
bench/                       test sets, red-team sets, labels, saved model answers, live runs
studies/                     the pre-registrations, the evaluation plan and the full results
EVALS.md                     what was tested, what passed and what failed
```

License MIT. The bench corpus is Wikipedia text, CC BY-SA 4.0.

The judgment doesn't disappear when you install this. It moves: instead of re-checking 175 specifics, you decide whether the pages were the right pages. That's the part a tool can't hold for you.
