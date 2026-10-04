"""The red-team set: unsupported claims built, with the source in hand, to get past the code check.

python bench/run_redteam.py redteam              reads them with the reader (calls a model), saves the readings
python bench/run_redteam.py redteam --replay     rebuilds the table from the saved readings
python bench/run_redteam.py redteam --after-fix  the same set again, kept beside the first run
python bench/run_redteam.py redteam2             the second red team, written against the fixed check
"""

import json
import sys
from pathlib import Path

from receipts import Claim, Ledger, check_claim
from receipts.backends import ClaudeCodeBackend
from receipts.reader import READER_VERSION, read_pairs

HERE = Path(__file__).parent
NAME = next((x for x in sys.argv[1:] if not x.startswith("--")), "redteam")  # redteam, redteam2
CORPUS = {"redteam": "corpus2", "redteam2": "corpus"}[NAME]
TAG = "_after_fix" if "--after-fix" in sys.argv else ""
rows = [json.loads(x) for x in (HERE / f"{NAME}.jsonl").read_text().splitlines() if x.strip()]
ledger = Ledger.load(HERE / CORPUS / "ledger.json")
claims = [Claim(r["id"], r["text"], r["quote"], r["evidence_id"], r["company"]) for r in rows]
REPLAY = "--replay" in sys.argv
past_code = [c for c in claims if check_claim(c, ledger).supported]
saved = HERE / f"readings_{NAME}{TAG}.json"
if REPLAY:
    # A replay is the record of that run: the claims that had passed the code check then are the ones it read.
    stored = json.loads(saved.read_text())
    readings = {k: tuple(v) for k, v in stored["readings"].items()}
    name, cost = stored["reader"], stored["cost_usd_list_price"]
    past_code = [c for c in claims if c.id in readings]
else:
    backend = ClaudeCodeBackend("haiku")
    readings = read_pairs(past_code, ledger, backend)
    name, cost = f"{backend.name}, prompt {READER_VERSION}", round(backend.cost_usd, 4)
    saved.write_text(json.dumps({"reader": name, "readings": readings, "cost_usd_list_price": cost}, indent=1))

past_both = [c for c in past_code if readings.get(c.id, (False, ""))[0]]
technique = {r["id"]: r["technique"] for r in rows}
by: dict[str, list[int]] = {}
for c in claims:
    t = by.setdefault(technique[c.id], [0, 0, 0])
    t[0] += 1
    t[1] += c in past_code
    t[2] += c in past_both
print(
    f"{len(claims)} red-team claims · past the code check: {len(past_code)} · past the reader too: {len(past_both)}   ({name})"
)
for t, (n, code, both) in sorted(by.items(), key=lambda kv: -kv[1][2]):
    print(f"  {t:42} written {n}  past code {code}  past both {both}")
for c in past_both:
    print(f"  PAST BOTH {c.id} [{technique[c.id]}] {c.text}\n            quote: {c.quote}")
(HERE / f"RESULT_{NAME}{TAG}.json").write_text(
    json.dumps(
        {
            "reader": name,
            "n": len(claims),
            "past_code": len(past_code),
            "past_both": len(past_both),
            "by_technique": {t: {"written": v[0], "past_code": v[1], "past_both": v[2]} for t, v in by.items()},
            "past_both_ids": [c.id for c in past_both],
            "cost_usd_list_price": cost,
        },
        indent=1,
    )
)
