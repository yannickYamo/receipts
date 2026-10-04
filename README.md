# receipts

[![CI](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml/badge.svg)](https://github.com/yannickYamo/receipts/actions/workflows/ci.yml)

**receipts is a guard for the output of AI agents that research the web: every claim carries a quote from a page that code fetched, or it gets cut.**

An agent that researches the web hands you fluent prose full of prices, ratings and customer counts. Some are right. You can't tell which without redoing the research, so the time the agent saved comes back as checking. The core has no dependencies, needs Python 3.10 or later, and is MIT licensed.

## How it works

1. **Code fetches the page.** The text in the ledger is what the site served, with a date and a hash.
2. **The model may only point.** Each claim names a page and quotes it.
3. **Code decides what code can decide.** Is the quote on that page, word for word? Does every figure in the claim appear in the quote, money as money? Is the page about the product the claim names?
4. **A small reader model decides the rest, and may only cut.** It never sees the quote the first model chose. Code widens the quote to the whole sentences it sits in on the page, and the reader answers one question about that passage: does it state everything the claim states? A claim the reader couldn't read is cut too, so a failed call never lets a claim through.
5. **What fails is cut, never reworded,** and listed with the reason.

The design in one line: a model may point at evidence; only code may vouch for it.

## The evals: what passes and what fails

| Eval | Bar set before the run | Result | |
|---|---|---|---|
| True claims kept (60 written for the test, round 2) | at least 51 | 52 | pass |
| Unsupported claims cut (60 written for the test, round 2) | at least 54 | 60 | pass |
| The code check alone, with no reader (round 1) | at least 45 of 50 | 43 | **fail** |
| The reader run three times: verdicts that changed | none set | 0 of 76 | |
| Real pages: facts the check kept that the page states | at least 95% | 44 of 44 | pass |
| Real pages: true facts the check kept | none set | 44 of 59 | open |
| A red team that had the source code: false claims that got through | none set | 15 of 40 | open |

I wrote the evals before the runs, set a bar where I could, and kept the failures in. Every judgment is yes or no: there are no scores.

- **Rounds 1 and 2 were pre-registered.** Each has 60 true claims and 60 unsupported claims of six kinds, written by agents that never saw the check, with Wikipedia articles about software companies as the evidence.
- **The code check alone failed its bar in round 1.** It stopped every changed figure and every invented quote. It missed claims that keep the quote's words and change what they mean, for example the acquirer and the acquired swapped. I added the reader after that and tested both stages on a fresh set in round 2. All 8 true claims cut in round 2 were cut by the code check, none by the reader. The reader is claude-haiku-4-5, and reading the 120 claims of round 2 cost $0.17 at list price.
- **Real pages: the check cut true facts.** I took the 59 facts the model proposed in a live run on Freshdesk and Zendesk pages. Two labelers on different models read each fact against the full page without seeing what the check decided. Both said the page states all 59. So on that run the model invented nothing, and the check caught nothing. What the check did was cut 15 true facts, one in four. A guard that blocks a valid answer has a bug, and this is mine. I read the 15 one by one: 8 were cut because the quote held the value and not what it belongs to (a price without its plan name), 5 because the fact added a word the quote lacks, 1 was a faithful paraphrase, 1 tripped the negation rule.
- **The red team got through 15 of 40.** I gave an agent the source code and asked it for false claims built to get through. The first set got 9 of 40 past both stages, all by cutting a quote out of its sentence ("$425" out of "$425 million"). That's why the reader now reads the whole sentence. A fresh red team against the fixed code got 15 of 40 through. The most reliable way through, 6 of 6: quote a sentence faithfully when the next sentence on the page takes it back (a deal announced, then called off). The check verifies that a sentence on a page says what the claim says. It doesn't verify that the page, read whole, still stands behind that sentence.
- **An independent reviewer attacked the code before publishing.** It found that a quote of "$19" was accepted on a page that says "$199". That and eight other holes are fixed, each with a regression test.

The full record, every miss listed: `studies/RESULTS.md`. The test suite rebuilds every number in this README from the test sets and the saved model answers, with no model call. Both red-team sets run in the suite: a change that lets more of them through fails the build.

**What the numbers don't cover:**

- People. One model family wrote the check, the reader prompt, the test claims and the labels. A test set and labels from people come first.
- Whether a page is itself right. A wrong page yields a well-sourced wrong claim.
- Evidence other than software companies and their pricing pages.

## Use it

```bash
git clone https://github.com/yannickYamo/receipts && cd receipts
pip install -e .
```

As a check in a pipeline, exit code 1 when any claim is unsupported:

```bash
receipts fetch https://www.freshworks.com/freshdesk/pricing/ --ledger ledger.json
receipts check claims.json --ledger ledger.json
```

Its output:

```text
PASS a  Freshdesk Growth plan costs $19/agent/month, billed annually.
CUT  b  Freshdesk Growth plan costs $15/agent/month, billed annually.
       the claim states a figure the quote does not (15)
```

In Python:

```python
from receipts import Claim, Ledger, check_claims

ledger = Ledger()
page = ledger.add_url("https://www.freshworks.com/freshdesk/pricing/")
claim = Claim("a", text="Freshdesk Growth costs $19 per agent per month, billed annually",
              quote="Growth ... $19 /agent/month, billed annually", evidence_id=page.id, subject="Freshdesk")
report = check_claims([claim], ledger)
report.supported, report.cut, report.by_reason
```

The reader stage is added with `receipts.reader.check_with_reader(claims, ledger, backend)`.

**As a tool an agent calls on itself:** `receipts mcp` is an MCP server (install with `pip install -e ".[mcp]"`) with two tools, `read_page` and `check_claims_tool`. The agent can't hand in page text of its own. Evidence is only what the server fetched, and the server only fetches public http and https addresses.

**On someone else's output:** `receipts audit card.html` counts the specifics in any text and how many sit on a line with a link. It's a pattern count and it over-counts.

## The worked example: a battle card a rep can check

```bash
receipts card --us Freshdesk --them Zendesk --out out/
```

Both products go through the same steps: find pages, fetch them, list facts with quotes, check, write lines that cite the facts, check the lines, lay the page out from a fixed template. No model writes the HTML. Every line on the card opens to its quote, its page and the date the page was read. The top of the card says what was read, what was cut and what wasn't measured. This panel is from a real run on the code as published (bench/live/run4):

```text
sources   5 pages read · 2 could not be read
facts     37 of 48 supported by a quote on the page it names · 11 cut (7 not stated, 2 figure not in quote, 1 beyond quote, 1 polarity mismatch)
lines     16 of 22 kept · 6 cut
on this card: every line links to the page and quote it rests on
not measured: whether a page is itself right; whether the advice is good
run       claude-code (sonnet) · 16 model calls
reader    claude-code (haiku), prompt f95a7623
          its reading of facts is measured (studies/); its reading of card lines and advice is not
```

A response from that card, to the objection "Zendesk AI can automate up to 80%": "That's their claim. With Freshdesk the Freddy AI Agent is on every plan with 500 free sessions, so you can test it on your own tickets. Extra sessions are $49 per 100." The card also says where the competitor is strong, because the facts say so: "Zendesk has built-in QA scoring for 100% of AI interactions."

The default backend is the local `claude` command, so it runs on a Claude Code login. `--backend anthropic` uses the Anthropic API (install with `pip install -e ".[anthropic]"`). That path hasn't been run yet: I had no API key for it when I built this.

## Known limits

- **It cuts true things:** one true fact in four on real pricing pages. Cutting a true line costs a line. Keeping a false one costs the rep the room. The check is built for the second, and the first is the next thing to fix.
- **It doesn't stop someone who writes claims to beat it:** 15 of 40 got through.
- **Sites that refuse the fetch aren't read.** G2 and Capterra answered 403 in every live run. The card says which pages it couldn't read. It doesn't fall back to the model's memory.
- **Pages that need JavaScript aren't read.**
- **The reader is a model.** Its numbers hold for claude-haiku-4-5 and the prompt version they were measured on.

## Where this comes from

I took a popular open-source example, a seven-agent sales "battle card" pipeline in the awesome-llm-apps collection, and ran its own prompts on its own sample request: "Help me compete against Zendesk, I sell Freshdesk". I ran the prompts on Claude Sonnet, not on Gemini as the original does, so this shows how the pipeline is built, not how accurate Gemini is. The card it wrote has 175 pattern hits for specifics (prices, ratings, counts, dates, attributions). I read a seeded sample of 40 by hand: 32 were checkable facts, 28 of them distinct. Not one of the 175 sits on a line with a link. The model wrote VERIFY on its own output 23 times. I did not show its figures are wrong: the Zendesk list prices it gave match Zendesk's pricing page.

The point is that a sales rep can't tell which ones are right, because the pipeline passes prose from agent to agent and no address survives to the card.

The invented-claim check in my other project, [Atelier](https://github.com/yannickYamo/atelier), works on the same idea: a small model reads, code decides. receipts applies it to web research, where the evidence is a page instead of the author's own notes.

## Layout

```text
src/receipts/core.py         the code check          src/receipts/reader.py      the reader stage
src/receipts/ledger.py       pages, dates, hashes    src/receipts/audit.py       count specifics in any text
src/receipts/battlecard/     the worked example      src/receipts/mcp_server.py  the check as an MCP server
bench/                       test sets, red-team sets, labels, saved model answers, live runs
studies/                     the pre-registrations, the evaluation plan and the results
```

`pytest` runs the suite offline and rebuilds every result table. `ruff check` and `ruff format --check` run in CI with the tests.

License: MIT. The bench corpus is Wikipedia text, CC BY-SA 4.0.
