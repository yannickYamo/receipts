# Evals: what passes and what fails

This is the record of the tests `receipts` was held to, and what it did on them. I wrote the evals before the runs, set a bar wherever I could set one honestly, and left the failures in. Every judgment here is yes or no, there are no scores, and the full record with every miss listed sits in `studies/RESULTS.md`.

The test suite rebuilds every number on this page from the test sets and the saved model answers, with no model call.

| Eval | Bar set before the run | Result | |
|---|---|---|---|
| True claims kept (60 written for the test, round 2) | at least 51 | 52 | pass |
| Unsupported claims cut (60 written for the test, round 2) | at least 54 | 60 | pass |
| The code check alone, with no reader (round 1) | at least 45 of 50 | 43 | **fail** |
| The reader run three times: verdicts that changed | none set | 0 of 76 | |
| Real pages: facts the check kept that the page states | at least 95% | 43 of 43 | pass |
| Real pages: true facts the check kept | none set | 43 of 59 | open |
| A red team that had the source code: false claims that got through | none set | 15 of 40 | open |

## What each line means

**Rounds 1 and 2 were pre-registered.** Each has 60 true claims and 60 unsupported claims of six kinds, written by agents that never saw the check, with Wikipedia articles about software companies as the evidence.

**The code check alone failed its bar in round 1.** It stopped every changed figure and every invented quote. What it missed were claims that keep the words of the quote and change what they mean - the acquirer and the acquired swapped, for instance. I added the reader after that and tested both stages on a fresh set in round 2. All 8 true claims cut in round 2 were cut by the code check, none by the reader. The reader is `claude-haiku-4-5`, and reading the 120 claims of round 2 cost $0.17 at list price.

**The reader is a model, so one run could be luck.** I ran it three times over the 76 claims that reach it in round 2. No verdict changed.

**On real pages, the failure is cutting true facts, not letting false ones through.** I took the 59 facts the model proposed in a live run against Freshdesk and Zendesk pages. Two labelers on different models read each fact against the full page without seeing what the check decided, and both said the page states all 59. So the model invented nothing on that run, and the check caught nothing. What it did was cut 16 true facts, about one in four. A guard that blocks a valid answer has a bug, and this one is mine. I read the 16 one by one: 8 were cut because the quote held the value and not what it belongs to (a price with no plan name attached), 6 because the fact added a word the quote lacks, 1 was a faithful paraphrase, and 1 tripped the negation rule.

**The red team had the source code.** The first set got 9 of 40 past both stages, all of them by cutting a quote out of its sentence - "$425" lifted out of "$425 million". The reader now reads the whole sentence for that reason. A fresh red team against the fixed code got 15 of 40 through, and 16 of 40 when I reran the same set on the code as published. The most reliable way through is to quote a sentence faithfully when the next sentence on the page takes it back: a deal announced, then called off. The check verifies that a sentence on a page says what the claim says. It doesn't verify that the page, read whole, still stands behind that sentence.

**Two independent audits attacked the code before publishing.** The first found that a quote of "$19" was accepted on a page that says "$199". The second found that "19 agents" was accepted against "$19". Every defect they found is fixed and has a regression test. Both red-team sets run in the test suite, so a change that lets more of them through fails the build.

## What the numbers do not cover

- **People.** One model family wrote the check, the reader prompt, the test claims and the labels. A test set and labels from people come first.
- **Whether a page is itself right.** A wrong page yields a well-sourced wrong claim.
- **Evidence other than software companies and their pricing pages.**
- **The reader on the battle card's lines and advice.** It was measured on facts against sentences only.

## Run it yourself

```bash
pip install -e ".[dev,mcp]"
pytest                                           # rebuilds every number above, no model
python bench/run_two_stage.py round2 --replay    # round 2 in detail, every miss listed
python bench/run_redteam.py redteam2 --replay    # the red team, every claim that got through
```

## What is next

1. Stop cutting true facts on pricing pages: keep a value together with the name it belongs to.
2. Let the reader see the sentences on either side, so a claim the next sentence takes back is cut. Then a fresh round.
3. A test set and labels written by people.
