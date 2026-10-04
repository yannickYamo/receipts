"""Score the shipped check on live run 3's facts against two blind labellers. No model.

    python bench/traces/score.py     prints the table and writes bench/traces/RESULT_traces.json

"Pass" is the positive class. For the check as a judge of "the quote states the claim":
  TPR  of the facts a labeller says the quote states, the share the check kept
  TNR  of the facts a labeller says the quote does not state, the share the check cut
"""

import json
from pathlib import Path

HERE = Path(__file__).parent


def load(name: str) -> dict[str, dict]:
    return {r["id"]: r for r in (json.loads(x) for x in (HERE / name).read_text().splitlines() if x.strip())}


def main() -> None:
    verdicts = json.loads((HERE / "verdicts_shipped.json").read_text())["verdicts"]
    kept = {i: v["kept"] for i, v in verdicts.items()}
    labels = {"A (claude-opus)": load("labels_A.jsonl"), "B (claude-sonnet)": load("labels_B.jsonl")}
    out: dict = {"facts": len(kept), "kept": sum(kept.values()), "cut": len(kept) - sum(kept.values()), "labellers": {}}
    for name, lab in labels.items():
        page_true = [i for i in kept if lab[i]["page_states"]]
        quote_yes = [i for i in kept if lab[i]["quote_states"]]
        quote_no = [i for i in kept if not lab[i]["quote_states"]]
        row = {
            "kept_facts_the_page_states": [sum(lab[i]["page_states"] for i in kept if kept[i]), sum(kept.values())],
            "page_true_facts_kept": [sum(kept[i] for i in page_true), len(page_true)],
            "TPR_quote_states_and_kept": [sum(kept[i] for i in quote_yes), len(quote_yes)],
            "TNR_quote_does_not_state_and_cut": [sum(not kept[i] for i in quote_no), len(quote_no)],
            "kept_although_quote_does_not_state": sorted(i for i in quote_no if kept[i]),
            "cut_although_quote_states": sorted(i for i in quote_yes if not kept[i]),
        }
        out["labellers"][name] = row
        print(name)
        for k, v in row.items():
            counted = len(v) == 2 and all(isinstance(x, int) for x in v)
            print(f"  {k}: " + (f"{v[0]} of {v[1]}" if counted else ", ".join(v) or "none"))
    a, b = labels.values()
    out["labellers_agree_on_quote_states"] = [
        sum(a[i]["quote_states"] == b[i]["quote_states"] for i in kept),
        len(kept),
    ]
    out["labellers_disagree"] = sorted(i for i in kept if a[i]["quote_states"] != b[i]["quote_states"])
    print(
        "labellers agree on quote_states:",
        out["labellers_agree_on_quote_states"],
        "disagree on:",
        out["labellers_disagree"],
    )
    (HERE / "RESULT_traces.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
