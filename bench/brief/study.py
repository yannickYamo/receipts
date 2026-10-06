"""The brief, measured: are the signals it keeps on the page, how many true ones does it keep, do its lines add facts?

    python bench/brief/study.py run       build a brief for each company of companies.json   (calls a model)
    python bench/brief/study.py sheet     blind sheets for the labellers (no model)
    python bench/brief/study.py score     the three bars, from the run and the settled labels (no model)

The plan and the bars are in studies/BRIEF_PREREGISTRATION.md. The seller is made up, so nothing here
is a claim about a real product being sold. Page text of other sites stays local (the ledgers are not
in the repository); the signals, the lines and the labels are kept.
"""

import argparse
import json
import random
from pathlib import Path

from receipts.backends import ClaudeCodeBackend
from receipts.brief import build_brief, panel_text, render_html

HERE = Path(__file__).parent
SEED = 11


def rows(path: Path) -> list[dict]:
    """The rows of a .jsonl file, or none when it is not there."""
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()] if path.exists() else []


def write_rows(path: Path, items: list[dict]) -> None:
    """Write rows as .jsonl."""
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in items))


def run(a: argparse.Namespace) -> None:
    """One brief for each company, with both stages. Writes brief.json, brief.html and a local ledger for each."""
    plan = json.loads((HERE / "companies.json").read_text())
    backend, reader = ClaudeCodeBackend(a.model), ClaudeCodeBackend(a.reader_model)
    a.dir.mkdir(parents=True, exist_ok=True)
    briefs = []
    for n, c in enumerate(plan["companies"], start=1):
        brief = build_brief(plan["seller"], c["url"], backend, company=c["name"], reader=reader, log=print)
        briefs.append(brief)
        brief.card.ledger.save(a.dir / f"ledger-{n}.json")
        print(panel_text(brief) + "\n")
    (a.dir / "brief.json").write_text(json.dumps([b.to_dict() for b in briefs], indent=1, ensure_ascii=False))
    (a.dir / "brief.html").write_text(render_html(briefs))
    print(f"list-price cost ${backend.cost_usd + reader.cost_usd:.2f} in {backend.calls + reader.calls} calls")


def items(briefs: list[dict]) -> tuple[list[dict], list[dict]]:
    """(every proposed signal, every written line), each with an id that names its company."""
    signals, lines = [], []
    for n, b in enumerate(briefs, start=1):
        said = {s["id"]: s["text"] for s in b["signals"]}
        pages = {s["id"]: s["url"] for s in b["sources"]}
        for s in b["signals"]:
            signals.append(
                {
                    "id": f"c{n}-{s['id']}",
                    "company": b["company"],
                    "page": pages.get(s["evidence_id"], ""),
                    "ledger": f"ledger-{n}.json",
                    "evidence_id": s["evidence_id"],
                    "text": s["text"],
                    "quote": s["quote"],
                    "kept": s["supported"],
                }
            )
        for i, x in enumerate(b["lines"], start=1):
            lines.append(
                {
                    "id": f"c{n}-{x['section']}-{i}",
                    "company": b["company"],
                    "seller": b["seller"],
                    "text": x["text"],
                    "signals_it_cites": [said[c] for c in x["cites"] if c in said],
                    "kept": x["kept"],
                }
            )
    return signals, lines


def sheet(a: argparse.Namespace) -> None:
    """Two sheets in a fixed random order. Neither says what the check decided."""
    signals, lines = items(json.loads((a.dir / "brief.json").read_text()))
    for name, found in (("signals", signals), ("lines", lines)):
        random.Random(SEED).shuffle(found)
        write_rows(a.dir / f"sheet_{name}.jsonl", [{k: v for k, v in r.items() if k != "kept"} for r in found])
    print(f"{len(signals)} signals and {len(lines)} lines to label. One row each to labels_<name>.jsonl:")
    print('  a signal: {"id": ..., "page_states": true|false, "names_a_person": true|false}')
    print('  a line:   {"id": ..., "adds_fact": true|false, "names_a_person": true|false}')
    print("page_states: the page, read whole, states the signal. adds_fact: the line states a fact about the")
    print("company, or about anything else, that neither the signals it cites nor the seller's words state.")


def share(k: int, n: int) -> str:
    """k of n with its share."""
    return f"{k} of {n} ({k / n:.0%})" if n else f"{k} of {n}"


def score(a: argparse.Namespace) -> None:
    """The three bars and what is reported beside them."""
    signals, lines = items(json.loads((a.dir / "brief.json").read_text()))
    labels = {r["id"]: r for r in rows(a.dir / a.labels)}
    missing = [r["id"] for r in [*signals, *lines] if r["id"] not in labels]
    if missing:
        raise SystemExit(f"{len(missing)} items have no label in {a.labels}, the first is {missing[0]}")
    kept = [s for s in signals if s["kept"]]
    true = [s for s in signals if labels[s["id"]]["page_states"]]
    kept_true = sum(labels[s["id"]]["page_states"] for s in kept)
    true_kept = sum(s["kept"] for s in true)
    kept_lines = [x for x in lines if x["kept"]]
    adding = [x["id"] for x in kept_lines if labels[x["id"]]["adds_fact"]]
    people = [r["id"] for r in [*kept, *kept_lines] if labels[r["id"]].get("names_a_person")]
    result = {
        "companies": len({s["company"] for s in signals}),
        "labels": a.labels,
        "kept_signals_the_page_states": {
            "k": kept_true,
            "n": len(kept),
            "bar": 0.95,
            "passes": bool(kept) and kept_true / len(kept) >= 0.95,
        },
        "true_signals_kept": {
            "k": true_kept,
            "n": len(true),
            "bar": 0.70,
            "passes": bool(true) and true_kept / len(true) >= 0.70,
        },
        "kept_lines_that_add_a_fact": {
            "k": len(adding),
            "n": len(kept_lines),
            "bar": 0,
            "passes": not adding,
            "ids": adding,
        },
        "kept_items_that_name_a_person": {
            "k": len(people),
            "n": len(kept) + len(kept_lines),
            "bar": 0,
            "passes": not people,
            "ids": people,
        },
        "lines_cut": [len(lines) - len(kept_lines), len(lines)],
        "lines_cut_that_added_no_fact": sum(not labels[x["id"]]["adds_fact"] for x in lines if not x["kept"]),
    }
    (a.dir / "RESULT_brief.json").write_text(json.dumps(result, indent=1))
    for title, key in (
        ("Signals kept that the page states (bar: at least 95%)", "kept_signals_the_page_states"),
        ("True signals kept (bar: at least 70%)", "true_signals_kept"),
        ("Kept lines that add a fact (bar: none)", "kept_lines_that_add_a_fact"),
        ("Kept signals and lines that name a person (bar: none)", "kept_items_that_name_a_person"),
    ):
        r = result[key]
        print(f"{title}: {share(r['k'], r['n'])} · {'met' if r['passes'] else 'missed'}")


def main() -> None:
    """Parse the command line and run one step."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("step", choices=["run", "sheet", "score"])
    ap.add_argument("--model", default="sonnet", help="run: the model that lists signals and writes lines")
    ap.add_argument("--reader-model", default="haiku", help="run: the reader")
    ap.add_argument("--labels", default="labels_final.jsonl")
    ap.add_argument("--dir", type=Path, default=HERE / "run1")
    a = ap.parse_args()
    {"run": run, "sheet": sheet, "score": score}[a.step](a)


if __name__ == "__main__":
    main()
