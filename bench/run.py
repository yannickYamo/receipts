"""Run the check on the held-out sets and write the result. No model, no network.

python bench/run.py            prints the table and writes bench/RESULT_round1_code_only.json
"""

import hashlib
import json
from pathlib import Path

from receipts import Claim, Ledger, check_claim

HERE = Path(__file__).parent
ROOT = HERE.parent


def load(name: str) -> list[dict]:
    return [json.loads(line) for line in (HERE / name).read_text().splitlines() if line.strip()]


def main() -> None:
    ledger = Ledger.load(HERE / "corpus" / "ledger.json")
    clean, invented = load("heldout_clean.jsonl"), load("heldout_invented.jsonl")

    def verdict(row: dict):
        return check_claim(Claim(row["id"], row["text"], row["quote"], row["evidence_id"], row["company"]), ledger)

    false_cuts = [(r, v) for r in clean if not (v := verdict(r)).supported]
    by_type: dict[str, list[tuple[dict, object]]] = {}
    for r in invented:
        by_type.setdefault(r["type"], []).append((r, verdict(r)))

    print(f"clean claims left alone: {len(clean) - len(false_cuts)} of {len(clean)}")
    for r, v in false_cuts:
        print(f"  FALSE CUT {r['id']} [{v.reason}] {r['text']}\n            quote: {r['quote']}")
    result = {
        "clean": {
            "n": len(clean),
            "left_alone": len(clean) - len(false_cuts),
            "false_cuts": [{"id": r["id"], "reason": v.reason, "detail": v.detail} for r, v in false_cuts],
        },
        "invented": {},
    }
    mechanical = caught_mechanical = 0
    for kind, rows in by_type.items():
        caught = [(r, v) for r, v in rows if not v.supported]
        missed = [(r, v) for r, v in rows if v.supported]
        reasons: dict[str, int] = {}
        for _, v in caught:
            reasons[v.reason] = reasons.get(v.reason, 0) + 1
        print(f"{kind}: caught {len(caught)} of {len(rows)}  {reasons}")
        for r, _ in missed:
            print(f"  MISSED {r['id']} {r['text']}\n         quote: {r['quote']}")
        result["invented"][kind] = {
            "n": len(rows),
            "caught": len(caught),
            "caught_by": reasons,
            "missed": [r["id"] for r, _ in missed],
        }
        if kind != "meaning_changed":
            mechanical += len(rows)
            caught_mechanical += len(caught)
    print(f"five mechanical types together: caught {caught_mechanical} of {mechanical}")
    result["mechanical"] = {"n": mechanical, "caught": caught_mechanical}
    result["code"] = {
        f: hashlib.sha256((ROOT / "src/receipts" / f).read_bytes()).hexdigest()[:16] for f in ("core.py", "text.py")
    }
    (HERE / "RESULT_round1_code_only.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
