# Round 3: how to run it

For whoever runs the round. The plan and the bars are in `ROUND3_PREREGISTRATION.md`; read its
amendment first. This file is the order of work. Every step that calls a model is marked.

## Rules

- Do not edit anything under `src/`. If a run breaks there, stop and report what broke.
- Run each step once. If a step breaks for a reason outside the check (a timeout, a page that will
  not load, a key that is wrong), fix that, run the step again, and note the first attempt.
- Do not look at a result and then change a set, a label or a prompt.
- The agent that writes the red-team set and the planted-instruction set must not be shown the bars.
- Hand back every file the steps write. Do not summarise in their place.

## The reader's name

The reader is claude-haiku-4-5. Every script takes its name: `--reader-model=<name>` for the bench
scripts, `--model` for `run_two_stage.py` and for `study.py read`, `--reader-model` for `receipts`.
The default is the short name `haiku`. If the `claude` command on the machine does not serve that
name, pass the full id (`claude-haiku-4-5`) to every step below, the same one each time. Each result
file names the reader it was read with. Note in the hand-back which route the calls took (a personal
login, an API key, a gateway): the model behind a name is the route's to decide.

## Before the freeze: check that every model can be reached

One small call per route. A failure here is plumbing, and it is fixed before anything is measured.

```bash
pip install -e ".[dev,mcp,anthropic]" && pytest -q

# Claude, through the local command (the reader, two extractors, the earlier sets)
python - <<'PY'
import json
from receipts import Ledger
led = Ledger()
ev = led.add_text("https://acme.example/about", "Acme was founded in 2010 in Berlin by two engineers.", "About Acme")
led.save("/tmp/l.json")
claim = {"id": "a", "text": "Acme was founded in 2010 in Berlin", "quote": "Acme was founded in 2010 in Berlin", "evidence_id": ev.id, "subject": "Acme"}
json.dump([claim], open("/tmp/c.json", "w"))
PY
receipts check /tmp/c.json --ledger /tmp/l.json; echo "exit $?"
# expected: PASS a, exit 0, and a last line naming the reader: claude-code (haiku), prompt 3e63cca8
# exit 3 means the reader could not be reached; the reason is printed

# OpenAI and xAI, through --backend openai (two extractors, one labeller)
export OPENAI_API_KEY=...            # for xAI also: export OPENAI_BASE_URL=https://api.x.ai/v1
python -c "from receipts.backends import OpenAIBackend as B; print(B('<model>').json('Reply in JSON.', 'Say ok.', {'type':'object','additionalProperties':False,'required':['ok'],'properties':{'ok':{'type':'boolean'}}}))"

# The Citations API (one arm, reported only)
export ANTHROPIC_API_KEY=...
python bench/study/study.py pages                                         # no model; fetches the 24 pages
python bench/study/citations.py --model sonnet --dir /tmp/citations-smoke # after copying ledger.json and index.json there
```

If the Citations script or the OpenAI route fails on the shape of a request or a reply, report it:
those two have only been tested against stand-ins.

## Freeze

```bash
python bench/study/study.py freeze      # writes bench/study/FROZEN.json; commit it
pytest -q                               # from here this fails if core.py, text.py or reader.py changes
```

## The sets that need an author (model calls)

1. `bench/redteam3.jsonl`: Part 2 of the pre-registration says who writes it and with what.
2. `bench/injection.jsonl`: the amendment says who writes it and with what. The format is at the top
   of `bench/run_injection.py`.

## The runs (model calls, each once)

```bash
# Part 1: the earlier sets on the new reader
python bench/run_two_stage.py round2 --tag v2
python bench/repeat_reader.py 2 v2
python bench/run_redteam.py redteam2 --tag=v2
python bench/traces/recheck.py v2                 # needs bench/live/run3/ledger.json, which is not in the repository;
                                                  # if it cannot be had, report the row as not run

# Part 2 and the planted instructions
python bench/run_redteam.py redteam3
python bench/run_injection.py

# Part 3: four extractors, three families
python bench/study/study.py extract --backend claude-code --model haiku  --family claude
python bench/study/study.py extract --backend claude-code --model sonnet --family claude
python bench/study/study.py extract --backend openai --model <an OpenAI model> --family gpt
OPENAI_BASE_URL=https://api.x.ai/v1 OPENAI_API_KEY=<the xAI key> \
python bench/study/study.py extract --backend openai --model <an xAI model>   --family grok
python bench/study/citations.py --model sonnet    # the Citations arm
python bench/study/study.py read                  # the reader on every claim, the Citations ones too

# Part 4
receipts card --us Freshdesk --them Zendesk --out bench/live/run6
```

## Labels

```bash
python bench/study/study.py sheet                 # writes sheet_blind.jsonl
```

Two labellers, one of them not a Claude model, each read every row of `sheet_blind.jsonl` against the
full page (its text is in `ledger.json` under the row's `evidence_id`) and write
`labels_<name>.jsonl`. The rule for `quote_states` is in the amendment. A labeller sees the sheet and
the pages, and nothing else: not `claims.jsonl`, not the readings, not the other labeller's file.

```bash
python bench/study/study.py settle --labellers <a>,<b>    # writes settle_sheet.jsonl for the person
# the person writes settled.jsonl
python bench/study/study.py final  --labellers <a>,<b>    # writes labels_final.jsonl and label_stats.json
python bench/study/study.py score                          # the table, the bars, the outcome
```

The facts of Part 4's card are labelled the same way.

## What to hand back

`FROZEN.json`, `redteam3.jsonl`, `injection.jsonl`, every `readings_*` and `RESULT_*` file the runs
wrote, `claims.jsonl`, `claims_citations.jsonl`, `extracted.jsonl`, `sheet_blind.jsonl`, both
`labels_*.jsonl`, `settle_sheet.jsonl`, `readings.json`, `bench/live/run6/`, the exact model names
used, what each step cost, and a note of any step that was run twice and why.
