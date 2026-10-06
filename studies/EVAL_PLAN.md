# Evaluation plan: three more measurements

Written on 2026-10-03, before any of the three was run. Rounds 1 and 2 (`RESULTS.md`) measured the check
on claims written for the test. These three measure what those rounds could not.

## A. Real traces, labelled blind

The 59 facts the model proposed in live run 3 (`bench/live/run3`), each with its quote and its page.
Two labellers working apart, on different models, read each fact against the full page and answer two
yes/no questions without seeing what the check decided:

- `page_states`: does the page state this fact?
- `quote_states`: does the quote, alone, state everything the fact states?

Where they disagree, the item is listed for a person to settle, and results are given both ways.

What is reported:

- **Of the facts the check kept, how many does the page state?** This is the promise on the card. Bar:
  at least 95% by each labeller.
- **Of the facts the page states, how many did the check keep?** This is what the promise costs. No bar:
  it is reported.
- How often the two labellers agree.

The labellers are models, not people. Until a person has labelled a sample, these are provisional.

## B. A red team with the source code

Rounds 1 and 2 never met an adversary: their false claims copied whole sentences as quotes. One agent,
given the source of the check, writes 40 unsupported claims built to get past the code check, and
confirms each against the code. The reader then reads the ones that got past the code.

Reported: how many of the 40 pass the code check, and how many of those the reader also passes. No bar.
Every claim that passes both is listed, then fixed with a regression test or stated as a limit.

## C. The reader, repeated

Round 2's reader stage is run two more times on the same 120 claims. Reported: the three results, and
how many claims got a different verdict in any run.
