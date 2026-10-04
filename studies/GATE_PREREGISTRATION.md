# Pre-registration: does the check catch unsupported claims and leave true ones alone?

Written on 2026-10-03, before either held-out file was read or run.

## What is tested

`receipts.check_claim` at its default settings (`min_overlap=0.5`, near-quote match on at 0.85, no model
involved). The code is frozen at these hashes (first 16 hex of sha256):

- `src/receipts/core.py` 6a415464f05ec28d
- `src/receipts/text.py` e4a65eb07fa4aff9

If either file changes before the run, the change and its reason are listed in the result.

## The sets

The evidence is the plain text of six Wikipedia articles (`bench/corpus/`). Two agents wrote the claims.
Neither saw the check, the tests or the other's file.

- `bench/heldout_clean.jsonl`: 60 true claims, paraphrased as an analyst would, each with a verbatim quote.
- `bench/heldout_invented.jsonl`: 60 unsupported claims, 10 of each type: wrong_figure, fabricated_quote,
  polarity, wrong_company, beyond_quote, meaning_changed.

One run, no tuning afterwards. Every miss and every false cut is listed by id in the result.

## Bars

1. Clean claims left alone: at least 51 of 60 (85%).
2. Inventions caught, the five mechanical types together (wrong_figure, fabricated_quote, polarity,
   wrong_company, beyond_quote): at least 45 of 50 (90%).
3. meaning_changed is reported on its own and has no bar. Prediction: the check misses most of them. It
   compares words and figures, and these claims keep both while changing who did what. If that holds,
   the README says so and names it as the case that needs a reader.

## Limits known before the run

- The same model family wrote the check and both sets. An outside author may write claims that
  behave differently.
- Wikipedia prose is cleaner than a pricing page. The live run on real product pages is a separate record.
- A label can be wrong. Any claim whose label is disputed after the run is listed with the reason,
  and both counts (as labelled, and with disputed items removed) are given.
