"""The reader bake-off: another reader on the claims the measured reader was measured on. No new labels.

Every set in bench/ already says which of its claims are true and which are not. So a new reader can
be put beside the measured one for the price of its calls: it reads the same claims that pass the
code check, and the two are compared claim for claim.

    python bench/bakeoff/bakeoff.py read --reader jev --name jev            a decision model (calls its API)
    python bench/bakeoff/bakeoff.py read --reader openai --model <m> --name <n>   any chat model as an ordinary reader
    python bench/bakeoff/bakeoff.py score --name jev                        the comparison (no model)

A decision reader returns a probability. Its threshold is set on round 1 by a rule fixed in advance
and then held for every other set. A chat reader answers yes or no, which is a probability of 1 or 0.
The plan and the bars are in studies/BAKEOFF_PREREGISTRATION.md.
"""

import argparse
import json
import time
from pathlib import Path

from receipts import Claim, Ledger, check_claim
from receipts.backends import AnthropicBackend, ClaudeCodeBackend, OpenAIBackend
from receipts.decision import DECISION_VERSION, JevBackend, read_probabilities
from receipts.reader import READER_VERSION, read_pairs

HERE = Path(__file__).parent
BENCH = HERE.parent
# set -> (corpus, the files of true claims, the files of unsupported claims)
SETS = {
    "round1": ("corpus", ["heldout_clean.jsonl"], ["heldout_invented.jsonl"]),
    "round2": ("corpus2", ["round2_clean.jsonl"], ["round2_invented.jsonl"]),
    "redteam": ("corpus2", [], ["redteam.jsonl"]),
    "redteam2": ("corpus", [], ["redteam2.jsonl"]),
    "redteam3": ("corpus3", [], ["redteam3.jsonl"]),
    "redteam4": ("corpus4", [], ["redteam4.jsonl"]),
}
# The measured reader's saved answers for each set: the newest that is in the repository.
BASELINE = {
    "round1": ["readings_round1_v2.json", "readings_round1_shipped.json"],
    "round2": ["readings_round2_v2.json", "readings_round2_shipped.json"],
    "redteam": ["readings_redteam_v2.json", "readings_redteam_after_fix.json"],
    "redteam2": ["readings_redteam2_v2.json", "readings_redteam2_shipped.json"],
    "redteam3": ["readings_redteam3.json"],
    "redteam4": ["readings_redteam4.json"],
}
THRESHOLDS = [round(0.05 * i, 2) for i in range(1, 20)]
SLACK = 2  # claims a new reader may be behind the measured one on a set and still count as level with it


def load(name: str, bench: Path) -> list[dict] | None:
    """A set as rows: each claim that passes the code check, with whether it is true. None when a file is absent."""
    corpus, true_files, false_files = SETS[name]
    if (
        not all((bench / f).exists() for f in [*true_files, *false_files])
        or not (bench / corpus / "ledger.json").exists()
    ):
        return None
    ledger = Ledger.load(bench / corpus / "ledger.json")
    out = []
    for files, true in ((true_files, True), (false_files, False)):
        for f in files:
            for r in (json.loads(x) for x in (bench / f).read_text().splitlines() if x.strip()):
                claim = Claim(r["id"], r["text"], r["quote"], r["evidence_id"], r["company"])
                out.append({"claim": claim, "true": true, "past_code": check_claim(claim, ledger).supported})
    return out


def read(a: argparse.Namespace) -> None:
    """The reader on every claim that passes the code check, in every set that is here. Saves a probability for each."""
    chat = {"claude-code": ClaudeCodeBackend, "anthropic": AnthropicBackend, "openai": OpenAIBackend}
    backend = JevBackend(a.model or "jev-latest") if a.reader == "jev" else chat[a.reader](a.model or "haiku")
    sets, started, errors = {}, time.monotonic(), []
    for name in SETS:
        rows = load(name, a.bench)
        if rows is None:
            continue
        ledger = Ledger.load(a.bench / SETS[name][0] / "ledger.json")
        standing = [r["claim"] for r in rows if r["past_code"]]
        if a.reader == "jev":
            sets[name] = read_probabilities(standing, ledger, backend, errors)
        else:
            answers = read_pairs(standing, ledger, backend, errors=errors)
            sets[name] = {cid: 1.0 if stated else 0.0 for cid, (stated, _) in answers.items()}
        print(f"{name}: {len(sets[name])} of {len(standing)} claims read")
    record = {
        "reader": backend.name,
        "served_by": getattr(backend, "served_by", ""),
        "kind": "decision" if a.reader == "jev" else "chat",
        "prompt_version": DECISION_VERSION if a.reader == "jev" else READER_VERSION,
        "calls": backend.calls,
        "seconds": round(time.monotonic() - started, 1),
        "tokens": getattr(backend, "tokens", {}),
        "cost_usd_list_price": round(getattr(backend, "cost_usd", 0.0), 4),
        "errors": errors[:5],
        "sets": sets,
    }
    (a.dir / f"probabilities_{a.name}.json").write_text(json.dumps(record, indent=1))


def counts(rows: list[dict], kept: dict[str, bool]) -> dict:
    """True claims kept and unsupported claims cut, over the whole set: a claim the code check cut is cut."""
    true = [r for r in rows if r["true"]]
    false = [r for r in rows if not r["true"]]
    stands = lambda r: r["past_code"] and kept.get(r["claim"].id, False)  # noqa: E731
    return {
        "true_kept": sum(stands(r) for r in true),
        "true": len(true),
        "unsupported_cut": sum(not stands(r) for r in false),
        "unsupported": len(false),
        "unsupported_past_both": sum(stands(r) for r in false),
    }


def baseline(name: str, bench: Path) -> tuple[dict[str, bool], str] | None:
    """The measured reader's answers on a set, and the file they come from."""
    for f in BASELINE[name]:
        if (bench / f).exists():
            stored = json.loads((bench / f).read_text())
            return {k: bool(v[0]) for k, v in stored["readings"].items()}, f"{f} ({stored['reader']})"
    return None


def pick_threshold(rows: list[dict], probabilities: dict[str, float], measured: dict) -> tuple[float, bool]:
    """The threshold, from round 1 alone, and whether it met the rule.

    The rule: among the thresholds that cut at least as many unsupported claims as the measured reader
    did on round 1, the one that keeps the most true claims; of equals, the highest. When none cuts
    as many, the one that cuts the most, and the result says the rule was not met.
    """
    scored = [(t, counts(rows, {k: p >= t for k, p in probabilities.items()})) for t in THRESHOLDS]
    level = [(c["true_kept"], t) for t, c in scored if c["unsupported_cut"] >= measured["unsupported_cut"]]
    if level:
        return max(level)[1], True
    return max((c["unsupported_cut"], c["true_kept"], t) for t, c in scored)[2], False


def score(a: argparse.Namespace) -> None:
    """The comparison, set by set, at the threshold round 1 gives. No model."""
    record = json.loads((a.dir / f"probabilities_{a.name}.json").read_text())
    loaded = {name: load(name, a.bench) for name in SETS}
    first, first_base = loaded["round1"], baseline("round1", a.bench)
    if first is None or first_base is None or "round1" not in record["sets"]:
        raise SystemExit(
            "round 1 is needed to set the threshold: its claims, its saved readings and this reader's answers"
        )
    threshold, met_rule = pick_threshold(first, record["sets"]["round1"], counts(first, first_base[0]))
    result: dict = {
        "reader": record["reader"],
        "served_by": record.get("served_by", ""),
        "kind": record["kind"],
        "prompt_version": record["prompt_version"],
        "threshold": threshold,
        "threshold_rule_met_on_round_1": met_rule,
        "sets": {},
    }
    read_total = sum(len(v) for v in record["sets"].values())
    if read_total:
        result["seconds_per_claim"] = round(record["seconds"] / read_total, 3)
        result["tokens"] = record.get("tokens", {})
    for name, rows in loaded.items():
        base = baseline(name, a.bench)
        if rows is None or base is None or name not in record["sets"]:
            continue
        probabilities = record["sets"][name]
        new = counts(rows, {k: p >= threshold for k, p in probabilities.items()})
        old = counts(rows, base[0])
        unanswered = sum(r["past_code"] and r["claim"].id not in probabilities for r in rows)
        entry = {"measured": old | {"from": base[1]}, "new": new | {"unanswered": unanswered}}
        if name == "round2":
            entry["curve"] = {str(t): counts(rows, {k: p >= t for k, p in probabilities.items()}) for t in THRESHOLDS}
            passed = [r for r in rows if r["past_code"] and r["claim"].id in probabilities]
            entry["brier"] = (
                round(sum((probabilities[r["claim"].id] - r["true"]) ** 2 for r in passed) / len(passed), 4)
                if passed
                else None
            )
        result["sets"][name] = entry
    bars = {}
    if "round2" in result["sets"]:
        r2 = result["sets"]["round2"]
        bars["round2_true_kept"] = r2["new"]["true_kept"] >= r2["measured"]["true_kept"] - SLACK
        bars["round2_unsupported_cut"] = r2["new"]["unsupported_cut"] >= r2["measured"]["unsupported_cut"] - SLACK
    if "redteam2" in result["sets"]:
        rt = result["sets"]["redteam2"]
        bars["redteam2_past_both"] = (
            rt["new"]["unsupported_past_both"] <= rt["measured"]["unsupported_past_both"] + SLACK
        )
    result["bars"] = bars
    result["level_with_the_measured_reader"] = bool(bars) and all(bars.values()) and met_rule
    (a.dir / f"RESULT_bakeoff_{a.name}.json").write_text(json.dumps(result, indent=1))
    print(
        f"{record['reader']} · threshold {threshold} from round 1"
        + ("" if met_rule else " (the rule was not met there)")
    )
    for name, e in result["sets"].items():
        old, new = e["measured"], e["new"]
        if old["true"]:
            print(
                f"  {name:9} true kept {new['true_kept']} of {new['true']} (measured reader {old['true_kept']}) · unsupported cut {new['unsupported_cut']} of {new['unsupported']} (measured reader {old['unsupported_cut']})"
            )
        else:
            print(
                f"  {name:9} past both stages {new['unsupported_past_both']} of {new['unsupported']} (measured reader {old['unsupported_past_both']})"
            )
    print("  bars: " + ", ".join(f"{k} {'met' if v else 'missed'}" for k, v in bars.items()))
    print(
        "  level with the measured reader"
        if result["level_with_the_measured_reader"]
        else "  not level with the measured reader"
    )


def main() -> None:
    """Parse the command line and run one step."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("step", choices=["read", "score"])
    ap.add_argument("--reader", choices=["jev", "claude-code", "anthropic", "openai"], default="jev")
    ap.add_argument("--model", default="")
    ap.add_argument("--name", required=True, help="a name for this reader's files")
    ap.add_argument("--dir", type=Path, default=HERE)
    ap.add_argument("--bench", type=Path, default=BENCH)
    a = ap.parse_args()
    {"read": read, "score": score}[a.step](a)


if __name__ == "__main__":
    main()
