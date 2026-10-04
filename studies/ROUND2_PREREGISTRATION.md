# Pre-registration, round 2: both stages on a fresh set

Written on 2026-10-03, after round 1 and before either round 2 file was read or run.

## Why a second round

Round 1 tested the code check alone (`GATE_PREREGISTRATION.md`). It left 58 of 60 true claims alone and
caught 43 of 50 mechanical inventions, under its bar of 45, and 0 of 10 meaning changes, as predicted.
The misses share one cause: the claim keeps the quote's words and figures and changes what they mean.
A reader stage was added for that (`src/receipts/reader.py`). Its prompt was written after seeing the
round 1 misses, with no example from the set in it, and round 1 was then used to try it (59 of 60 caught,
58 of 60 clean left alone). That number is a development number. This round is the test.

## What is tested

`receipts.reader.check_with_reader`: the code check, then the reader on what the code check kept.

- `src/receipts/core.py` 6a415464f05ec28d and `src/receipts/text.py` e4a65eb07fa4aff9: unchanged since round 1
- reader prompt version f95a7623, model claude-haiku-4-5 through the local `claude` command, 10 pairs per call

## The set

Six other Wikipedia articles (`bench/corpus2/`). Two new agents wrote `round2_clean.jsonl` (60 true
claims) and `round2_invented.jsonl` (60 unsupported, 10 per type, same six types). Neither saw the
check, the reader, round 1 or the other's file. True and invented claims reach the reader mixed.

## Bars

1. Clean claims left alone: at least 51 of 60.
2. Inventions caught, all six types together: at least 54 of 60.

One run. Every miss and false cut is listed. A label that looks wrong is listed as disputed, and the
counts are given both ways.

## Limits

Same as round 1: one model family wrote the check, the reader prompt and the sets, and Wikipedia prose is
cleaner than a product page. A model reader varies a little between runs; this is one run.
