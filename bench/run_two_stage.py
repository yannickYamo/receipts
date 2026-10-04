"""Run both stages (the code check, then the reader) on one round and write the result.

    python bench/run_two_stage.py round1 --model haiku
    python bench/run_two_stage.py round2 --model haiku

The reader's answers are saved next to the result, so the table can be rebuilt without a model:
    python bench/run_two_stage.py round2 --replay
"""

import argparse
import json
import random
from pathlib import Path

from receipts import Claim, Ledger
from receipts import reader as reader_module
from receipts.backends import ClaudeCodeBackend, ScriptedBackend
from receipts.reader import READER_VERSION, check_with_reader, read_pairs

HERE = Path(__file__).parent
ROUNDS = {
    "round1": ("corpus", "heldout_clean.jsonl", "heldout_invented.jsonl"),
    "round2": ("corpus2", "round2_clean.jsonl", "round2_invented.jsonl"),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("round", choices=ROUNDS)
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--replay", action="store_true", help="use the saved readings; call no model")
    ap.add_argument(
        "--tag", default="", help="a suffix for the readings and result files, for a re-run kept beside the first"
    )
    a = ap.parse_args()
    corpus, clean_file, invented_file = ROUNDS[a.round]
    ledger = Ledger.load(HERE / corpus / "ledger.json")
    rows = [json.loads(x) | {"type": "clean"} for x in (HERE / clean_file).read_text().splitlines() if x.strip()]
    rows += [json.loads(x) for x in (HERE / invented_file).read_text().splitlines() if x.strip()]
    random.Random(7).shuffle(rows)  # true and invented claims reach the reader mixed, in one fixed order
    claims = [Claim(r["id"], r["text"], r["quote"], r["evidence_id"], r["company"]) for r in rows]
    tag = f"_{a.tag}" if a.tag else ""
    saved = HERE / f"readings_{a.round}{tag}.json"

    if a.replay:
        stored = json.loads(saved.read_text())
        reader_module.read_pairs = lambda cs, led, backend, batch=10: {
            c.id: tuple(stored["readings"][c.id]) for c in cs if c.id in stored["readings"]
        }
        backend, name = ScriptedBackend([]), stored["reader"]
        backend.calls, backend.cost_usd = stored.get("model_calls", 0), stored.get("cost_usd_list_price", 0.0)
    else:
        backend = ClaudeCodeBackend(a.model)
        name = f"{backend.name}, prompt {READER_VERSION}"
        calls: dict[str, tuple[bool, str]] = {}
        original = read_pairs

        def recording(cs, led, b, batch=10):
            got = original(cs, led, b, batch)
            calls.update(got)
            return got

        reader_module.read_pairs = recording

    report = check_with_reader(claims, ledger, backend)
    if not a.replay:
        saved.write_text(
            json.dumps(
                {
                    "reader": name,
                    "readings": calls,
                    "model_calls": backend.calls,
                    "cost_usd_list_price": round(backend.cost_usd, 4),
                },
                indent=1,
            )
        )
    verdict = {v.claim_id: v for v in report.verdicts}

    result: dict = {
        "round": a.round,
        "reader": name,
        "types": {},
        "cost_usd_list_price": round(backend.cost_usd, 4),
        "model_calls": backend.calls,
    }
    total = caught_total = 0
    for kind in [
        "clean",
        "wrong_figure",
        "fabricated_quote",
        "polarity",
        "wrong_company",
        "beyond_quote",
        "meaning_changed",
    ]:
        group = [r for r in rows if r["type"] == kind]
        cut = [r for r in group if not verdict[r["id"]].supported]
        kept = [r for r in group if verdict[r["id"]].supported]
        by: dict[str, int] = {}
        for r in cut:
            by[verdict[r["id"]].reason] = by.get(verdict[r["id"]].reason, 0) + 1
        if kind == "clean":
            print(f"clean left alone: {len(kept)} of {len(group)}   cut by: {by}")
            for r in cut:
                v = verdict[r["id"]]
                print(f"  FALSE CUT {r['id']} [{v.reason}: {v.detail}] {r['text']}\n            quote: {r['quote']}")
            result["types"][kind] = {
                "n": len(group),
                "left_alone": len(kept),
                "cut_by": by,
                "false_cuts": sorted(r["id"] for r in cut),
            }
        else:
            total += len(group)
            caught_total += len(cut)
            print(f"{kind}: caught {len(cut)} of {len(group)}   by: {by}")
            for r in kept:
                print(f"  MISSED {r['id']} {r['text']}\n         quote: {r['quote']}")
            result["types"][kind] = {
                "n": len(group),
                "caught": len(cut),
                "caught_by": by,
                "missed": sorted(r["id"] for r in kept),
            }
    print(
        f"all invented: caught {caught_total} of {total}   reader: {name}   calls: {backend.calls}   list-price cost: ${backend.cost_usd:.3f}"
    )
    result["invented"] = {"n": total, "caught": caught_total}
    (HERE / f"RESULT_{a.round}_two_stage{tag}.json").write_text(json.dumps(result, indent=1))


if __name__ == "__main__":
    main()
