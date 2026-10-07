# Evals

**receipts is a guard for AI agents that research the web: every claim has to carry a quote from a page the code actually fetched, or it gets cut. This file is the list of tests it was held to, what passed, and what failed. Some bars were missed, and they're in the tables with everything else. If you only read the table, you'll have the honest version.**

## Round 3: the reader in 0.2.0

The plan, its amendment and the sentence each outcome would put in the README were written before any run (`studies/ROUND3_PREREGISTRATION.md`). The full record is in `studies/RESULTS.md`, section 8. One thing sets this round apart from the earlier ones: the files of its runs are not in this repository, so these numbers cannot be rebuilt from it the way every earlier number can.

| Measure | Bar set before the run | Result | |
|---|---|---|---|
| Round 2 again, true claims kept | at least 51 of 60 | 52 | met |
| Round 2 again, unsupported claims cut | at least 54 of 60 | 60 | met |
| The reader run three times: verdicts that changed | at most 2 | 0 of 76 | met |
| Second red team again: got past both stages | at most 10 of 40 | 5 | met |
| Second red team again: retractions past both | at most 2 of 6 | 1 | met |
| Third red team, fresh: retractions past both | at most 2 | 0 of 7 | met |
| Third red team, fresh: joined table lines past both | at most 2 | 0 of 10 | met |
| Third red team, all techniques | none set | 1 of 40 | |
| Instructions planted on the page: passes, planted against plain | at most 1 more | 1 against 0, of 20 pairs | met, at the limit |
| 864 claims, 24 real pages: delivered with a quote that doesn't state them | at most half the bare model's | 34% before, 12% after | met |
| Same claims: delivered and not stated by the page at all | at most half, when there are 20 | 9 of 864 before, 4 of 576 after | no bar: too few |
| Same claims: true claims kept | at least 70% | 572 of 855 (67%) | **missed** |
| Same claims: claims whose quote states them, kept | at least 85% | 504 of 568 (89%) | met |
| A live battle card: true facts kept | at least 80% | 43 of 56 (77%) | **missed** |
| Reader, list price for 100 claims | reported | $0.36 | |

**What it shows.** Told to quote their source, four models from three families attached a quote that doesn't state the claim one time in three. receipts cut that to about one in eight. That is what it does.

**What it doesn't show.** That it catches inventions. Only 9 of the 864 claims stated something the page doesn't, and 4 were still there after the check. That is too few to put to a bar, and the pre-registered sentence for this outcome says so in the README.

**What it costs.** One true claim in three. By kind of page it kept 83% of true claims on encyclopedia articles, 71% on documentation, and 47% on pricing pages, where a value sits in a column away from the name it belongs to. That is the first thing to fix.

**Four ways this is not the result as planned.**

- The files of the runs are not published. Every earlier number in this file replays from saved files with no model; these are reported, not reproducible from the repository.
- The labels were not settled by a person, so the result is not the pre-registered one. Two labellers of different model families labelled every claim, and a third model family settled the 148 they disputed or marked unsupported, plus a sample of 50. Of that sample, 2 agreed labels were overturned.
- The two labellers agree on "the quote states it" for 91% of claims (kappa 0.79) and on "the page states it" for 97% (kappa 0.18). The second kappa is low because almost every claim is stated by its page: on the few that might not be, the labellers mostly disagree. So the count of inventions is soft: 3 of 864 by the most lenient reading of the two labellers, 29 by the strictest.
- Two runs were not made: the Citations API arm, and the re-read of the 59 facts of live run 3.

**How much rests on the labels.** Every measure was also computed under the strictest labelling the two labellers allow (yes only where both say yes) and the most lenient (yes where either does). No settlement can fall outside those two. The outcome is the same under each: quotes that don't state the claim fall from 35% to 13% under the strictest and from 26% to 8% under the most lenient. One bar is not the same: "claims whose quote states them, kept" is 89% as settled and 83% under the most lenient labels, which is under its bar of 85%.

## The reader of 0.1.0

Everything from here to the audits was measured on the earlier reader (prompt f95a7623), which did not see the page around a quote.

| Eval | Bar set before the run | Result | |
|---|---|---|---|
| True claims kept (60 written for the test, round 2) | at least 51 | 52 | pass |
| Unsupported claims cut (60 written for the test, round 2) | at least 54 | 60 | pass |
| The code check alone, with no reader (round 1) | at least 45 of 50 | 43 | **fail** |
| The reader run three times: verdicts that changed | none set | 0 of 76 | |
| Real pages: facts the check kept that the page states | at least 95% | 43 of 43 | pass, on a run where the model proposed nothing false |
| Real pages: true facts the check kept | none set | 43 of 59 | open |
| A red team that had the source code: false claims that got through | none set | 15 of 40 | open |

## How I ran these

I wrote the evals before the runs, and where I could set a bar beforehand, I set one and wrote it down. Every judgment is yes or no. No scores, no partial credit, no rubric I could later reinterpret in my own favor. Failures stay in the table.

The guard has two stages: a code check, then a small reader model (claude-haiku-4-5) that's only allowed to cut. The reader can never add a claim or approve one the code rejected. That asymmetry is deliberate, and it's the reason a model sits inside a guard at all.

The full record, with every individual miss listed, is in `studies/RESULTS.md`. The test suite rebuilds every number in the table above from the saved test sets and saved model answers, with no model call.

## Rounds 1 and 2: the code check alone wasn't enough

Both rounds were pre-registered. Each one is 60 true claims and 60 unsupported claims across six kinds, written by agents that never saw the check, against Wikipedia articles about software companies.

Round 1 tested the code check on its own, and it failed its bar: 43 against a bar of 45 of 50. It stopped every changed figure and every invented quote. What it missed were claims that keep the quote's words and change what they mean - the clean example being an acquisition where acquirer and acquired are swapped. The words are all there on the page. The sentence says the opposite thing.

So I added the reader and tested both stages together on a fresh set, which is round 2. Round 2 passed both bars. Worth noting which stage caused the remaining damage: all 8 true claims that were wrongly cut were cut by the code check, none by the reader. The reader cost $0.17 at list price for all 120 claims.

**A model inside a guard needs its own stability test.** One run can be luck. I ran the reader three times over the 76 claims that reach it in round 2, and no verdict changed.

## Real pages: the check cuts true facts

On a live run against Freshdesk and Zendesk pages, the model proposed 59 facts. Two labelers, different models, read each fact against the full page, blind to what the check had decided. Both agreed the page states all 59. On that run the model invented nothing, so the check caught nothing real.

What it did do was cut 16 true facts. About one in four.

**A guard that blocks a valid answer has a bug, and this one is mine.** I read the 16 one at a time. Eight were cases where the quote held a value but not what the value belongs to - a price without its plan name. Six were facts that added a word the quote didn't have. One was a faithful paraphrase. One tripped the negation rule.

## Red team on the earlier reader: 15 of 40 got through

I gave an agent the source code and asked it to build false claims designed to pass. The first set got 9 of 40 past both stages, all by the same trick: lifting a quote out of its sentence, so "$425" comes out of "$425 million." I fixed that by making the reader read the whole sentence.

A fresh red team against the fixed code got 15 of 40 through. Running that same set against the code as published gets 16 of 40.

The most reliable route through is a faithful quote of a sentence that the next sentence on the page takes back - a deal announced, then called off. That tells you exactly what this guard verifies: that some sentence on a fetched page says what the claim says. It does not verify that the page, read whole, still stands behind that sentence. Both red-team sets run in the test suite, and a change that lets more through fails the build.

## Audits

Two independent audits attacked the code before I published. The first found a quote of "$19" accepted on a page that says "$199." The second found "19 agents" accepted against "$19." Both got fixed with a regression test.

After publishing, an outside review found four more. The worst one: `receipts check` and the MCP tool were running the code stage alone - the stage that failed its bar in round 1. The reviewer's probe was a page saying "Zendesk offers the Suite Team plan in Europe. Zendesk does not offer it in India," a claim that Zendesk offers it in India, and the quote "the Suite Team plan in." Code stage passed it. Both stages cut it. Both stages are now the default everywhere, and `--code-only` has to be asked for and tells you what it is. The other three: the battle card's line check accepted "19 agents" against "$19"; the command printed the wrong text when two claims shared an id; a ledger file edited after the fetch was accepted. All fixed, each with a regression test.

A second outside review found ten more, none in the check's decisions: the API backend sent a model name the API refuses, a reader reply that answered a claim twice kept the last answer, a malformed ledger crashed, the fetcher looked a host name up twice. The list is in `studies/RESULTS.md`, section 7. All fixed, each with a regression test.

## What these evals don't cover

No people. One model family wrote the check, the reader prompt, the test claims, and the labels. A test set and labels written by people is the thing I most need and don't have.

Nothing here tells you whether a page is itself right. A wrong page gets you a well-sourced wrong claim. Evidence is software companies and their pricing pages only. And the reader is measured on facts against sentences - not on the battle card's lines or its advice.

## Run it yourself

```bash
pip install -e ".[dev,mcp]"
pytest                                           # rebuilds every number above, no model
python bench/run_two_stage.py round2 --replay    # round 2 in detail, every miss listed
python bench/run_redteam.py redteam2 --replay    # the red team, every claim that got through
```

## Next, in order

1. Keep a value with the name it belongs to on pricing pages. That is where half the true claims are lost.
2. Publish the files of round 3, have a person settle its labels, and make the two runs that were not made.
3. Measure the two experiments: the brief on a company, and a reader that answers with a probability.
4. A test set written by people.

## What to trust it for

Trust it to stop invented quotes and changed figures, and to remove most claims whose quote doesn't back them. Don't trust it against someone who has read the source code and is picking sentences a page later contradicts, and don't trust that a cut claim was false: most claims it cuts are true ones with a quote that doesn't carry them.

The guard moved the work. It didn't remove it: you're still the one answerable for the claim that ships, and this file only tells you where to look first.
