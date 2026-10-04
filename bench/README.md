# bench

Everything the results in `studies/RESULTS.md` were computed from. Nothing here needs a model to re-run: the model's answers were saved when each run was made.

## What's in it

- **`corpus/` and `corpus2/`**: the evidence for the test rounds. Each is the plain text of six English Wikipedia articles about software companies, read on 2026-10-03. Wikipedia text is licensed [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). `index.json` in each folder gives every article's address. `build.py` fetches them again.
- **`heldout_clean.jsonl` and `heldout_invented.jsonl`**: round 1. 60 true claims and 60 unsupported claims. The unsupported ones are false on purpose: they're test data, not statements about the companies.
- **`round2_clean.jsonl` and `round2_invented.jsonl`**: round 2, the same shape on the second corpus.
- **`redteam.jsonl` and `redteam2.jsonl`**: 40 false claims each, written by an agent that had the source code and was asked to get past the check. Also false on purpose.
- **`readings_*.json`**: the reader model's saved answers for each run.
- **`RESULT_*.json`**: the result of each run.
- **`traces/`**: the 59 facts from live run 3, two sets of blind labels, the verdicts of the check as shipped, and the score.
- **`live/run1` to `live/run5`**: five runs of the battle card on real pages. Each has the card as HTML and as JSON. The full text of the vendors' pages isn't in the repository; each card keeps every page's address, the date it was read and a hash of its text.
- **`baseline/`**: the script that runs the upstream example's prompts, and `AUDIT.json` with the counts. The card it produced isn't in the repository, because it's unverified text about two real companies.

## Commands

```bash
python bench/run.py                              # round 1, the code check alone
python bench/run_two_stage.py round2 --replay    # round 2, both stages, from the saved answers
python bench/run_redteam.py redteam2 --replay    # the second red team
python bench/traces/score.py                     # real pages against the blind labels
```

Without `--replay`, the scripts call the reader model again through the local `claude` command. `pytest` runs all of the replays and checks the numbers against the ones published.
