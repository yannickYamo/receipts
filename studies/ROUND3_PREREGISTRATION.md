# Pre-registration, round 3: the reader with the page around the quote, and a base rate

Written on 2026-10-04, after the reader was changed and before any model read a claim with it. Nothing
below has been run. The runs, the third red-team set and the first labels are the work of an agent that
did not write the check; a person settles the labels.

## Why a third round

Two things changed after round 2 and the red teams (`RESULTS.md`, sections 3 and 4).

The reader now sees the page around the passage: up to three sentences or lines on each side, and,
for a quote that joins table lines, every line from the first to the last. The second red team got 6
of 6 through with a faithful quote that the next sentence takes back, and 2 of 6 with table lines that
belong to different rows. The prompt says the surrounding text is never evidence and can only cut.

The battle card gives a fact one more quote when its first quote did not carry it. On run 3, 9 of the
16 true facts that were cut had a quote that, by both labellers, does not state the fact. The fact's
words cannot change, and the second quote passes the same two stages.

Both changes can cost true claims. The earlier numbers were measured on reader f95a7623 and say
nothing about this one.

There is also a question the earlier rounds never asked. On run 3 the model proposed 59 facts and the
page states all 59, so the check caught nothing real. How often does a model that is told to quote
state something the page does not? Without that rate, a share of errors caught has nothing to stand on.

## What is tested

- `src/receipts/core.py` 59f710ad699d8fb9 and `src/receipts/text.py` b0bae52357db889c. The code check's decisions are
  unchanged from round 2: `text.py` gained the function that returns the text around a quote.
- reader prompt version 3e63cca8, model claude-haiku-4-5 through the local `claude` command, at most 10
  pairs per call, one page per call.

No file under `src/` changes during the round. If a bar is missed, it is reported as missed. A fix
comes after, with a set of its own.

## Part 1: the earlier sets, read again

These sets are not fresh. The change was written against two techniques of the second red team, not
against its claims, but its numbers here are a regression check, not a measurement.

| Set | Bar | Before |
|---|---|---|
| Round 2, true claims kept | at least 51 of 60 | 52 |
| Round 2, unsupported claims cut | at least 54 of 60 | 60 |
| Round 2 reader, three runs: claims whose verdict changes | at most 2 | 0 of 76 |
| Second red team, got past both stages | at most 10 of 40 | 15 (16 as shipped) |
| Second red team, next-sentence retraction, got past both | at most 2 of 6 | 6 |
| Real pages (run 3), true facts kept on the same quotes | at least 41 of 59 | 43 |

The last row can only fall: the quotes are fixed and the new text can only cut. It measures what the
change costs. It needs the pages of run 3, which are not in the repository.

## Part 2: a third red team, on fresh pages

Six Wikipedia articles neither earlier corpus used (`bench/corpus3/`). A new agent gets the source of
the check, the reader's prompt and `RESULTS.md`, and writes `bench/redteam3.jsonl`: 40 unsupported
claims built to pass both stages, in the format of `redteam2.jsonl`, each with its technique. At least
6 use a faithful quote that the page later takes back, with the retraction more than three sentences
away where the page allows it, and at least 6 join table or list lines. It keeps only claims that pass
the code check. It does not see this file's bars.

Bars, on the two techniques the change was made for: at most 2 of the retraction claims and at most 2
of the joined-line claims pass both stages. No bar on the total. It is reported by technique, with
every claim that got through.

## Part 3: the base rate, and every arm on the same claims

24 pages in three kinds (`bench/study/pages.json`): 8 pricing pages, 8 documentation pages, 8
encyclopedia articles. None was used in an earlier run. Two extractors, claude-haiku-4-5 and
claude-sonnet, each read every page and list up to 12 facts with an exact quote, under a plain
instruction to cite that says nothing of how the check works (`bench/study/study.py`, CITE_SYSTEM). That
is at most 576 claims.

**Labels.** Two labellers, one of them not a Claude model, each read every claim against the full page,
blind to the extractor and to every decision, and answer two yes/no questions: does the page state
it, and does the quote alone state it. A person then settles every claim the two disagree on, every
claim either says the page does not state, and a random 50 of the rest (seed 11). The settled file is
`labels_final.jsonl`. Counts are given by the settled labels and by each labeller.

**Arms.** All are decisions on the same claims (`study.py score`): keep everything (the bare model);
keep when the quote is on the page word for word; the code check; the reader alone; both stages.

**The fork, fixed now.** If the settled labels find fewer than 20 claims the page does not state, the
finding is the base rate with its interval. No share of errors caught is reported, and the README
says what the check is then for: making a claim checkable, not catching inventions.

Bars, when there are at least 20:

1. Both stages keep at most half as many unsupported claims as keeping everything does.
2. Both stages keep no more unsupported claims than the exact-quote arm.

Bars either way:

3. Of the claims whose quote states them, both stages keep at least 85%.
4. Of the claims the page states, both stages keep at least 70%. A plain instruction to cite does not
   teach the model to quote a price with its plan, so this is expected to be lower than bar 3. The
   difference between the two is the part a second quote is meant to recover, and Part 4 measures it.

## Part 4: one battle card with second quotes

One live run of `receipts card --us Freshdesk --them Zendesk` on the code as it stands. The same two
labellers read its proposed facts as in Part 3. Bar: of the facts the page states, at least 80% are
kept (run 3: 43 of 59, 73%). Reported with it: how many were kept on a second quote, and whether any
fact kept on a second quote is one the page does not state. One such fact fails the run.

## The runs, in order

```bash
pip install -e ".[dev,mcp]" && pytest -q                      # the suite, no model

python bench/run_two_stage.py round2 --tag v2                 # Part 1
python bench/repeat_reader.py 2 v2                            # two more runs beside the one above
python bench/run_redteam.py redteam2 --tag=v2
python bench/traces/recheck.py v2                             # needs bench/live/run3/ledger.json

# Part 2: the new agent writes bench/redteam3.jsonl, then
python bench/run_redteam.py redteam3

python bench/study/study.py pages                             # Part 3
python bench/study/study.py extract --model haiku
python bench/study/study.py extract --model sonnet
python bench/study/study.py sheet                             # then the labellers, then the person
python bench/study/study.py read
python bench/study/study.py score

receipts card --us Freshdesk --them Zendesk --out bench/live/run6   # Part 4
```

The `v2` runs are written beside the earlier files and replace none of them, so the suite keeps
rebuilding the published numbers from the answers they were measured with.

Every run that calls a model goes through the local `claude` command. Each is run once. A run that
breaks for a reason outside the check (a timeout, a page that no longer loads) is run again and the
first attempt is noted.

## What is written down whatever happens

Every bar with its result, missed ones included. Every claim that got past both stages in Part 2.
Every true claim that was cut in Parts 3 and 4, read one by one and grouped by cause. The cost at list
price and the number of calls. The earlier numbers stay in `RESULTS.md` beside the new ones, under the
reader version each was measured on.

## Limits

The extractors and the reader are one model family. One labeller is not, and a person settles the
labels, but only on the claims named above. Three kinds of page, all in English, all about software.
Sixty or forty claims a set gives wide intervals, and they are given. A reader that varies between runs
is measured on one set only.
