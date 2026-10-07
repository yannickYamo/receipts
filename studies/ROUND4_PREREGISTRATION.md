# Pre-registration, round 4: tables

Written on 2026-10-06, before any model read a page with the changed text. Nothing below has been run.

## Why

Round 3 kept 47% of the true claims on pricing pages, against 71% on documentation and 83% on
encyclopedia articles. On a pricing page a value sits in a cell, and what it means is given by its
row and its column. The text the check read put every cell on a line of its own, so a quote could
hold "10MB" and nothing that says whose limit it is.

## What changed

A table row is now one line of text, and each value carries the header of its column:
`File uploads | Free: 10MB | Pro: Unlimited` (`text.row_line`). This holds for HTML tables and for
tables built from other elements that name their rows and cells for screen readers. A header is only
what the page marks as one; none is guessed. The prompts that list facts say how to quote such a line.

The code check's rules and the reader's prompt are unchanged. What they read on a page with tables is
not, so nothing measured before says how they do on it.

- `src/receipts/core.py` 59f710ad699d8fb9, `src/receipts/text.py` 7269fdd18c53b875, `src/receipts/reader.py` 24b0ee00c397867a at the
  time of writing. `study.py freeze --dir bench/round4` records them again before the first model call.

## What this cannot fix, said now

Of the 12 pricing pages of this round, 6 have tables whose headers code can read, and 6 have none:
their plans are boxes that only look like a table on screen. The change does nothing for the second
kind. The results are given for the two kinds apart, and the bar is on all 12 together, so it may
well be missed.

## The parts

**1. Nothing earlier moves.** The corpora of rounds 1 to 3 are stored text and do not pass through
the changed step. The suite replays their published numbers; it must still pass. No model.

**2. Fresh pricing pages.** 12 pricing pages no earlier round or test read
(`bench/round4/pages.json`), the four extractors of round 3 under the same plain instruction to
quote, at most 9 facts a page: at most 432 claims. Labelled as in round 3, by two labellers of
different model families under the same rule for "the quote alone states it", with the strictest and
the most lenient labelling given beside the settled one. Who settles is recorded with the result. If
it is not a person, the result says so in those words.

**3. A red team on tables.** Six Wikipedia pages that are mostly tables (`bench/corpus4/`). A new
agent with the source and this change, and not these bars, writes `bench/redteam4.jsonl`: 40
unsupported claims that pass the code check, at least 10 that give a value to the wrong row and at
least 10 that give it to the wrong column, the rest as it sees fit.

**4. One battle card** on Freshdesk and Zendesk, as in round 3.

## Bars

1. Part 2: of the claims the page states, both stages keep at least 70% (round 3 on pricing pages: 47%).
2. Part 2: of the claims delivered, at most 15% have a quote that does not state them (round 3: 12%).
3. Part 2: both stages deliver no more claims the page does not state than the bare models did.
4. Part 3: at most 2 wrong-row claims and at most 2 wrong-column claims get past both stages.
5. Part 4: of the facts the page states, at least 80% are kept (round 3: 77%).

Reported, no bar: bar 1 for pages with readable tables and for pages without; every measure by
model family; the red team by technique, with every claim that got through; cost.

## What a miss means

It is written into `EVALS.md` with its number. If bar 4 is missed, the table change is not
released: a change that lets a wrong value through costs more than the true claims it saves. Any
other miss is a limit that is stated, and the next change gets a round of its own.

## Order of work

```bash
python bench/study/study.py freeze --dir bench/round4
python bench/study/study.py pages  --dir bench/round4
python bench/study/study.py extract --dir bench/round4 --backend claude-code --model haiku  --family claude
python bench/study/study.py extract --dir bench/round4 --backend claude-code --model sonnet --family claude
python bench/study/study.py extract --dir bench/round4 --backend openai --model <an OpenAI model> --family gpt
python bench/study/study.py extract --dir bench/round4 --backend openai --model <an xAI model>   --family grok
python bench/study/study.py sheet  --dir bench/round4      # then the labellers, settle, final, bounds
python bench/study/study.py read   --dir bench/round4
python bench/study/study.py score  --dir bench/round4
python bench/run_redteam.py redteam4                        # after the agent has written bench/redteam4.jsonl
receipts card --us Freshdesk --them Zendesk --out bench/live/run7
```

## Limits

Twelve pages, all pricing pages of software companies, in English. The red team's pages are Wikipedia
tables, which are cleaner than a pricing page. The extractors and the reader are as in round 3, so a
difference from round 3 is the pages and the text, not the models.
