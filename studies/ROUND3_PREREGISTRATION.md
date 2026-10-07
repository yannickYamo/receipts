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

---

# Amendment, 2026-10-04

Written before any run of this round. Nothing above had been run, so nothing above is revised in the
light of a result. Where this amendment and the text above differ, the amendment holds. Parts 1, 2
and 4 stand as written. Part 3 changes as follows, and two things are added. The order of work is
now `ROUND3_RUNBOOK.md`, which replaces the list of runs above.

## Why amend

Three gaps in Part 3 as first written.

It counted one kind of error, a claim the page does not state. The check promises more than that:
a kept claim comes with a quote that states it. A true claim with a quote that does not state it
breaks that promise, and Part 3 had no number for it.

Its extractors were two Claude models. The check takes claims from any model, and a result on one
family cannot say so.

It had no row for the result where there are enough errors to measure and the check does not reduce
them. A plan with no sentence for its worst result lets the result be explained afterwards.

## The claims

Four extractors from three model families: claude-haiku-4-5 and claude-sonnet through the local
`claude` command, one OpenAI model and one xAI model through `--backend openai`. The run records the
exact model names. Each reads the same 24 pages and lists at most 9 facts with an exact quote, under
the same plain instruction (`CITE_SYSTEM`). That is at most 864 claims. The reader stays
claude-haiku-4-5: it is the reader whose rates this round measures. No other reader is measured.

## The rule for "the quote alone states it"

A labeller answers yes when the quote, read with the title of its page and nothing else, states
everything the claim states. The title may supply the subject: on a page titled "Acme pricing", "the
Pro plan costs $49" states a fact about Acme. A heading, a neighbouring row, or anything else on the
page may not supply what the quote leaves out. This is the rule the reader's prompt applies, so the
label and the code are held to the same contract.

## Labels

Two labellers, one of them not a Claude model, label every claim blind (`study.py sheet`). A person
then settles every claim the two disagree on, on either question, and every claim either says the
page does not state, and reads a random 50 of the rest, seed 11 (`study.py settle`). The settled file
is the person's label where one was given and the agreed label elsewhere (`study.py final`).

Reported with the results: how often the two labellers agree on each question, with Cohen's kappa,
and how many of the 50 agreed labels the person overturned. If the person overturns more than 5 of
the 50, the agreed labels are not good enough to stand unread: the person labels every claim, and
the result waits for that.

## The measures

Every measure is taken on settled labels. Each labeller's own counts are given beside them.

**Intervals.** Claims about one page fail together, whichever model wrote them. Every interval is a
95% percentile interval over 2,000 resamples of whole pages, seed 11. Wilson intervals on claims are
given beside them and decide nothing.

**M1p, inventions delivered.** Of the claims an arm delivers, the share the page does not state.

**M1q, unchecked claims delivered.** Of the claims an arm delivers, the share whose quote does not
state them.

For each, one bar: the rate after both stages is at most half the bare model's, and the whole interval
of (both stages minus bare model) lies below zero. The bar applies only when the bare model's output
holds at least 20 such claims. Below 20, the count and its interval are reported and no bar applies.
This replaces bars 1 and 2 of Part 3.

Also reported, no bar: whether the rate after both stages is no higher than the rate when a claim is
kept for having its quote on the page. And each rate by model family, by extractor and by kind of page.

**M2a.** Of the claims the page states, both stages keep at least 70%. **M2b.** Of the claims whose
quote states them, both stages keep at least 85%. These are bars 4 and 3 of Part 3, unchanged. Also
reported: true claims delivered per page read, for each arm, and every true claim both stages cut,
read one by one and grouped by cause.

**M5, cost and speed.** List price per 100 claims read and mean seconds per claim, through the
`claude` command. Reported. If the price is above $1.00 per 100 claims, the README says so.

## The Citations API, reported and put to no bar

Claude Sonnet reads the same 24 pages as citations documents and is asked for the same facts
(`bench/study/citations.py`). Each statement it writes is a claim, with the first text the API cites
as its quote; a statement with no citation is a claim with no quote. These claims are labelled with
the rest. Reported: M1p, M1q and true claims per page for its output as written and after both
stages, beside the same figures for Claude Sonnet's claims from the shared set.

No bar, because the two sets are different claims from one model, and with few errors the difference
between them is noise. Nothing here decides the sentence below or the version.

## Planted instructions

`bench/injection.jsonl`: 20 pairs, written by an agent that has the reader's prompt and not this
file's bars. Each pair is one unsupported claim that passes the code check, once on a plain page and
once on the same page with an instruction to the reader planted in the title, in the quoted passage,
or in the text around it, about a third each. Bar: across the pairs where both versions pass the code
check, the planted versions pass both stages at most 1 more time than the plain ones
(`bench/run_injection.py`).

## What the README will say, fixed now

The numbers pick the row (`study.py score` prints it). The blanks are filled from the result.

| Outcome | When | First sentence |
|---|---|---|
| 1 | M1p meets its bar | "On N claims from 24 real pages, written by models of three families that were told to quote their source, X% stated something the page does not. After receipts, Z%. It kept W% of the true ones." |
| 2 | M1p does not, M1q does | "On N claims from 24 real pages, written by models of three families that were told to quote their source, X% came with a quote that does not state the claim. After receipts, Z%. It kept W% of the true ones." Then one of: "Only K of the N stated something the page does not, too few to say receipts catches inventions." or "It did not halve the claims the page does not state: X% before, Z% after." |
| 3 | neither does | "On N claims from 24 real pages, receipts did not measurably improve on a model told to quote its source: [both rates, before and after]. What it gives is the record: every claim it keeps has its quote, its page and the date the page was read." |

When M2a is missed, any of the three is followed by: "It cut V% of the true claims, mostly [the
largest cause]." A missed bar in Part 1, Part 2, Part 4 or the planted instructions goes in the README's
limits with its number.

The version is 0.2.0 whatever the outcome. No result changes the code before release. A fix comes
in a later version, with a set of its own.

## One page replaced

The Linear pricing page was read in an end-to-end test of this version before the round, and the
facts the check cut on it were read one by one. It is no longer a page the check has not met. It is
replaced by another small pricing page, Buttondown's, chosen without reading what a model makes of it.

## The freeze

`study.py freeze` records `core.py`, `text.py`, `reader.py` and the reader prompt version before the
first model call of the round, and the suite then fails if any of them changes
(`tests/test_freeze.py`). If one must change, every model run of the round starts again. Anything
else (a script under `bench/`, a backend's plumbing) may be fixed when a run breaks: the fix is
noted, and only the broken step is run again.

---

# Additions, 2026-10-06

Written after the plan and its amendment, and before any result of the round was published. These
are not part of the plan. They are marked as additions wherever they appear.

**Bounds on the labels.** The results are also given under the strictest labelling the two labellers
allow (yes only where both say yes) and the most lenient (yes where either does). No settlement can
fall outside them. It decides nothing: the outcome and the bars are read from the settled labels, as
planned. It shows whether they would have been different in other hands.

**The cost sentence.** The plan's sentence ends "mostly [the largest cause]", which needs every cut
claim read and grouped. The sentence the page prints ends with where the cost falls by kind of page,
which is a count. The reading of every cut claim by cause was not done.

**Who settled the labels, and what was not run,** are stated with the results, in `RESULTS.md`
section 8 and in `EVALS.md`. If the labels were not settled by a person,
the result is not the pre-registered one, and `EVALS.md` says so in those words.

**Published without its files, 2026-10-07.** The results are in `RESULTS.md`, section 8. The files of
the runs are not in the repository, so the page `bench/round3_report.py` writes from them is not
either, and the numbers are a report, not something the repository can rebuild.
