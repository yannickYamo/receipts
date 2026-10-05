"""Run round 2's reader stage again and compare with the saved first run. Calls a model.

python bench/repeat_reader.py 2      # two more runs; writes bench/RESULT_round2_repeats.json
python bench/repeat_reader.py 2 v2   # against readings_round2_v2.json; writes RESULT_round2_repeats_v2.json
"""

import json
import random
import sys
from pathlib import Path

from receipts import Claim, Ledger, check_claim
from receipts.backends import ClaudeCodeBackend
from receipts.reader import READER_VERSION, read_pairs

HERE = Path(__file__).parent
ledger = Ledger.load(HERE / "corpus2" / "ledger.json")
rows = [json.loads(x) | {"type": "clean"} for x in (HERE / "round2_clean.jsonl").read_text().splitlines() if x.strip()]
rows += [json.loads(x) for x in (HERE / "round2_invented.jsonl").read_text().splitlines() if x.strip()]
random.Random(7).shuffle(rows)
claims = [Claim(r["id"], r["text"], r["quote"], r["evidence_id"], r["company"]) for r in rows]
standing = [c for c in claims if check_claim(c, ledger).supported]
kind = {r["id"]: r["type"] for r in rows}

TAG = f"_{sys.argv[2]}" if len(sys.argv) > 2 else ""
first = json.loads((HERE / f"readings_round2{TAG}.json").read_text())["readings"]
runs = [{cid: v[0] for cid, v in first.items()}]
cost = 0.0
for _ in range(int(sys.argv[1]) if len(sys.argv) > 1 else 2):
    backend = ClaudeCodeBackend("haiku")
    got = read_pairs(standing, ledger, backend)
    runs.append({c.id: got.get(c.id, (False, ""))[0] for c in standing})
    cost += backend.cost_usd

ids = [c.id for c in standing]
changed = [i for i in ids if len({run.get(i) for run in runs}) > 1]
summary = {"reader": f"claude-code (haiku), prompt {READER_VERSION}", "pairs_read": len(ids), "runs": []}
for run in runs:
    clean_cut = sum(1 for i in ids if kind[i] == "clean" and not run.get(i))
    invented_kept = sum(1 for i in ids if kind[i] != "clean" and run.get(i))
    summary["runs"].append(
        {"true_claims_cut_by_reader": clean_cut, "unsupported_claims_passed_by_reader": invented_kept}
    )
summary["claims_with_a_different_verdict_in_any_run"] = [
    {"id": i, "type": kind[i], "verdicts": [run.get(i) for run in runs]} for i in changed
]
summary["cost_usd_list_price_of_repeats"] = round(cost, 4)
(HERE / f"RESULT_round2_repeats{TAG}.json").write_text(json.dumps(summary, indent=1))
print(json.dumps(summary, indent=1))
