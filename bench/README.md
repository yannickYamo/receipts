# bench/

**Everything in `studies/RESULTS.md` and `EVALS.md` was computed from this folder. You don't need a model to re-run any of it: the reader model's answers were saved at the time each run was made, so `--replay` gives you the published numbers from disk.**

`pytest` runs every replay and checks the numbers against the published ones. If you drop `--replay`, the scripts call the reader model again through the local `claude` command, which is the slower path and the one that can drift.

```bash
python bench/run.py                              # round 1, the code check alone
python bench/run_two_stage.py round2 --replay    # round 2, both stages, from the saved answers
python bench/run_redteam.py redteam2 --replay    # the second red team
python bench/traces/score.py                     # real pages against the blind labels
```

**Which reader the saved answers are from.** Every `readings_*.json` here was made with reader prompt f95a7623. The reader in the code now also sees the page around each quote (prompt 3e63cca8) and hasn't been measured. To run a set on it without replacing the published answers, give the run a name: `python bench/run_two_stage.py round2 --tag v2`, `python bench/run_redteam.py redteam2 --tag=v2`. The plan for those runs is `studies/ROUND3_PREREGISTRATION.md`.

**The evidence.** `corpus/` and `corpus2/` each hold the plain text of six English Wikipedia articles about software companies, read 2026-10-03, under CC BY-SA 4.0 (https://creativecommons.org/licenses/by-sa/4.0/). Each has an `index.json` giving every article's address, and `build.py` fetches them again. `corpus3/` is six more, read 2026-10-04, for a third red team that hasn't been written yet.

**The claims.** Round 1 is `heldout_clean.jsonl` and `heldout_invented.jsonl`: 60 true claims, 60 unsupported. Round 2 is `round2_clean.jsonl` and `round2_invented.jsonl`, same shape against the second corpus. `redteam.jsonl` and `redteam2.jsonl` hold 40 false claims each, written by an agent that had the source code and was asked to get past the check.

**One warning worth reading twice: the unsupported and red-team claims are false on purpose.** They're test data, not statements about the companies named in them.

**The runs.** `readings_*.json` holds the reader model's saved answers; `RESULT_*.json` holds the result of each run. `traces/` holds the 59 facts from live run 3, two sets of blind labels, the verdicts of the check as published, and the score. `live/run1` through `live/run5` hold five runs of the battle card on real pages, as HTML and JSON. The vendors' page text isn't in the repository - each card keeps every page's address, date read, and a hash of its text. `study/` is the harness for round 3's base-rate study: the list of 24 pages, and one script that fetches them, has a model list facts with quotes, makes a blind sheet for labellers, and scores five arms on the same claims. It has no results yet. `baseline/` has the script that runs the upstream example's prompts plus `AUDIT.json` with the counts; the card it produced isn't here, because it's unverified text about two real companies.
