# Evals

**What receipts is: a guard for AI agents that research the web. Every claim has to carry a quote from a page that code actually fetched, or it gets cut. Two stages do the cutting - a code check, then a small reader model (claude-haiku-4-5) that is only allowed to cut, never to add. This file is the record of what it was tested against, what passed, and what didn't. The short version: it's reliable at stopping fabricated numbers and invented quotes, it's not reliable against a determined attacker, and it cuts about one in four true facts on pricing pages. Trust it accordingly.**

| Eval | Bar set before the run | Result | |
|---|---|---|---|
| True claims kept (60 written for the test, round 2) | at least 51 | 52 | pass |
| Unsupported claims cut (60 written for the test, round 2) | at least 54 | 60 | pass |
| The code check alone, with no reader (round 1) | at least 45 of 50 | 43 | **fail** |
| The reader run three times: verdicts that changed | none set | 0 of 76 | |
| Real pages: facts the check kept that the page states | at least 95% | 43 of 43 | pass |
| Real pages: true facts the check kept | none set | 43 of 59 | open |
| A red team that had the source code: false claims that got through | none set | 15 of 40 | open |

## How I ran these

The evals were written before the runs, and the bar was set beforehand wherever I could set one. Failures stay in the table. Every judgment is yes or no - nothing is scored out of ten, because I don't trust myself to read a 7.2 honestly.

The full record, with every miss listed, is in `studies/RESULTS.md`. The test suite rebuilds every number on this page from the saved test sets and saved model answers, with no model call, so you can check my arithmetic without spending anything.

## Round 1 failed, and that's why there's a reader

Round 1 was the code check on its own: 60 true claims and 60 unsupported claims of six kinds, written by agents that had never seen the check, with Wikipedia articles about software companies as the evidence. It scored 43 against a bar of 45 of 50.

What it caught was the obvious family. Every changed figure, every invented quote. What it missed was claims that keep the quote's words intact and change what they mean - the acquirer and the acquired swapped, for instance. The words all appear on the page. The sentence is a lie.

So I added the reader stage and tested both stages together on a fresh set. That's round 2, and it passed both bars. Worth noting where the losses came from: all 8 true claims that got cut in round 2 were cut by the code check, none by the reader. The reader cost $0.17 at list price for all 120 claims.

**The reader is a model, so one good run could be luck.** I ran it three times over the 76 claims that reach it in round 2. Not one verdict changed.

## The number I'd want a skeptic to look at

On a live run against Freshdesk and Zendesk pages, the model proposed 59 facts. Two labelers, different models, read each fact against the full page, blind to what the check had decided. Both said the page states all 59.

So the model invented nothing on that run, and the check caught nothing. What it did do was cut 16 true facts. About one in four.

I read all 16. Eight were cases where the quote held a value but not what the value belongs to - a price without its plan name. Six added a word the quote lacked. One was a faithful paraphrase. One tripped the negation rule. A guard that blocks a valid answer has a bug, and this bug is mine, not the model's.

## What a motivated attacker gets

I gave an agent the source code and asked it to write false claims designed to get through. First set: 9 of 40 made it past both stages, all by cutting a quote out of its sentence, lifting "$425" out of "$425 million". I fixed that by having the reader read the whole sentence.

A fresh red team against the fixed code got 15 of 40 through. The same set rerun against the code as published: 16 of 40.

The most reliable route through is subtle and I don't have a fix for it yet: quote a sentence faithfully when the next sentence on the page takes it back. A deal announced, then called off. **The check verifies that a sentence on a page says what the claim says. It does not verify that the page, read whole, still stands behind that sentence.** Both red-team sets run in the test suite, so a change that lets more through fails the build.

Two independent audits attacked the code before publishing. The first found "$19" accepted on a page that says "$199". The second found "19 agents" accepted against "$19". Every defect they found is fixed and has a regression test.

## Run it yourself

```bash
pip install -e ".[dev,mcp]"
pytest                                           # rebuilds every number above, no model
python bench/run_two_stage.py round2 --replay    # round 2 in detail, every miss listed
python bench/run_redteam.py redteam2 --replay    # the red team, every claim that got through
```

## What these evals don't cover

No people were involved. One model family wrote the check, the reader prompt, the test claims and the labels, which means a shared blind spot would be invisible to all of this. A human-written test set with human labels is the first thing I owe this project.

Whether a page is itself correct is out of scope. A wrong page gives you a well-sourced wrong claim. Evidence outside software companies and their pricing pages is untested. And the reader was measured on facts against sentences only, not on the battle card's lines and advice.

## Next, in order

1. Stop cutting true facts on pricing pages: keep a value attached to the name it belongs to.
2. Let the reader see the sentences on either side, so a claim the next sentence retracts gets cut. Then a fresh round.
3. A test set and labels written by people.

If you're deciding whether to depend on this, the honest frame is that receipts moves the failure mode. It doesn't remove it. Fabricated figures mostly stop here. Adversarial quoting mostly doesn't, and a true answer sometimes dies on the way out. You're still the one answerable for what ships with a citation on it.
