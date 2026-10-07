# Pre-registration: a reader bake-off

Written on 2026-10-06, before any model read a claim for it. Nothing below has been run.

## The question

The reader answers one bounded question for each claim: does the quote, alone, state everything the
claim states? The measured reader is a small chat model, claude-haiku-4-5, answering yes or no. Models
built to decide and not to write now exist; they answer such a question with a probability. Can one
of them do the reader's job as well, and what does it cost in true claims and in time?

## What is tested

`receipts.decision`: the same second stage on a decision model. Only claims that pass the code check
are read. The model is shown what the measured reader is shown: the page title, the claim, the
passage, and the page around it. It returns the probability that the quote states the claim, and the
claim stands when that probability reaches a threshold. A claim it gives no answer for is cut.

The first decision model is TypeSafe AI's Jev, through its public HTTP API (`jev-latest`; the result
records the exact version that answered). The question it is asked is `decision.INSTRUCTIONS`, version
recorded with the result. `core.py`, `text.py` and `reader.py` do not change.

Any chat model can be run through the same harness as an ordinary reader, answering yes or no, which
is scored as a probability of 1 or 0.

## The claims, and why no new labels are needed

The sets already in `bench/`, each of which says which claims are true:

| Set | Claims | Use here |
|---|---|---|
| Round 1 | 60 true, 60 unsupported | sets the threshold, and nothing else |
| Round 2 | 60 true, 60 unsupported | the test |
| Red team 1 and 2 | 40 and 40 unsupported, written to get through | the test |
| Red team 3 | 40 unsupported | scored when its file is in the repository |

The measured reader's saved answers on the same claims are the comparison: the newest saved run of
each set that is in the repository, named in the result.

## The threshold, fixed now

From round 1 alone: among the thresholds 0.05, 0.10, ... 0.95 that cut at least as many unsupported
claims as the measured reader did on round 1, the one that keeps the most true claims; of equals, the
highest. If none cuts as many, the one that cuts the most is used and the result says the rule was not
met. That threshold is then held for every other set. It is never tuned on a set it is scored on.

## Bars

A reader is level with the measured one when the rule above was met on round 1 and, at that threshold:

1. on round 2 it keeps at most 2 fewer true claims than the measured reader;
2. on round 2 it cuts at most 2 fewer unsupported claims;
3. on the second red team at most 2 more claims get past both stages.

Reported with them, no bar: the first and third red teams; every claim where the two readers differ;
the Brier score on round 2; the whole curve of round 2, threshold by threshold; seconds per claim and
tokens.

## What each result leads to

- **Level:** the reader is offered on the command line as an option, with these numbers beside it.
  The default stays the measured reader.
- **Not level:** it stays in `bench/`, and the result is written into `EVALS.md`.

Neither result changes the default reader. That would need a round on fresh claims.

## Limits

These sets are the ones the measured reader's prompt was developed around: round 1 was its
development set, and the two red teams led to changes in what the reader is shown. A new reader meets
them fresh, and the measured one does not. The comparison is fair on round 2 and less so on the red
teams. All claims are about software companies, from Wikipedia text. The measured reader's saved
answers for some sets predate the page-around-the-quote change; the result names the run each
comparison uses. One run, and a decision model's probabilities may differ between versions.
