"""Arm F of the study: Claude with the page as a citations document. Calls the Anthropic API.

The same pages, the same subjects, the same number of facts as the other extractors, but the model
is not asked for a quote: the API attaches the cited text itself and guarantees it is in the document.
Each statement it writes becomes one claim, with the first cited text as its quote. A statement it
writes with no citation is a claim too, with an empty quote: it reaches the user all the same.

    python bench/study/citations.py --model sonnet       writes claims_citations.jsonl beside claims.jsonl

The claims are then labelled, read and scored with the others (study.py sheet, read, score). They are
reported beside the same model's uncited claims and put to no bar: the two sets are different claims.
Needs `pip install -e ".[anthropic]"` and ANTHROPIC_API_KEY.
"""

import argparse
import json
import re
from pathlib import Path

from receipts import Ledger
from receipts.backends import api_model

HERE = Path(__file__).parent
PER_PAGE = 9
PAGE_CHARS = 40_000
SYSTEM = (
    "You read one document and list facts it states about the subject you are given. Write each fact as one "
    "sentence on its own line that names the subject, and cite the document for it. Prefer specifics: prices "
    "and what they are for, limits, counts, dates, names. Do not use anything you know from elsewhere. Write "
    "nothing but the facts: no introduction, no headings, no summary."
)


def statements(content: list) -> list[dict]:
    """The reply's statements, each with the text the API cited for it.

    The reply is a run of text blocks. A block with citations ends a statement; text before it on the same
    line belongs to it. A line with words and no citation is a statement without a quote.
    """
    out: list[dict] = []
    pending = ""
    for block in content:
        if getattr(block, "type", "") != "text":
            continue
        cites = getattr(block, "citations", None) or []
        text = pending + block.text
        if cites:
            line = re.sub(r"^[\s\-*•\d.)]+", "", text.split("\n")[-1]).strip()
            earlier = text.split("\n")[:-1]
            out += [
                {"text": s, "quote": "", "cited": False, "citations": 0}
                for s in map(_clean, earlier)
                if _is_statement(s)
            ]
            out.append(
                {"text": line, "quote": str(cites[0].cited_text).strip(), "cited": True, "citations": len(cites)}
            )
            pending = ""
        else:
            pending = text
            if "\n" in pending:
                *whole, pending = pending.split("\n")
                out += [
                    {"text": s, "quote": "", "cited": False, "citations": 0}
                    for s in map(_clean, whole)
                    if _is_statement(s)
                ]
    if _is_statement(_clean(pending)):
        out.append({"text": _clean(pending), "quote": "", "cited": False, "citations": 0})
    return [s for s in out if s["text"]]


def _clean(line: str) -> str:
    return re.sub(r"^[\s\-*•\d.)]+", "", line).strip()


def _is_statement(line: str) -> bool:
    return len(line.split()) >= 4


def main() -> None:
    """Ask for facts with citations on every page of the study, and write them as claims."""
    ap = argparse.ArgumentParser(description=(__doc__ or "").split("\n")[0])
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--dir", type=Path, default=HERE)
    a = ap.parse_args()
    import anthropic  # pyright: ignore[reportMissingImports]

    client, ledger = anthropic.Anthropic(), Ledger.load(a.dir / "ledger.json")
    out, calls, tokens = [], 0, [0, 0]
    for p in json.loads((a.dir / "index.json").read_text()):
        ev = ledger[p["evidence_id"]]
        document = {
            "type": "document",
            "source": {"type": "text", "media_type": "text/plain", "data": ev.text[:PAGE_CHARS]},
            "title": ev.title or p["subject"],
            "citations": {"enabled": True},
        }
        ask = f"Subject: {p['subject']}\nList at most {PER_PAGE} facts."
        reply = client.messages.create(
            model=api_model(a.model),
            max_tokens=4000,
            system=SYSTEM,
            messages=[{"role": "user", "content": [document, {"type": "text", "text": ask}]}],
        )
        calls += 1
        tokens[0] += reply.usage.input_tokens
        tokens[1] += reply.usage.output_tokens
        found = statements(reply.content)[:PER_PAGE]
        for i, s in enumerate(found):
            out.append(
                {
                    "id": f"{p['evidence_id']}-citations-{i + 1}",
                    "extractor": f"citations:{a.model}",
                    "compare_with": a.model,
                    "family": "claude",
                    "kind": p["kind"],
                    "subject": p["subject"],
                    "evidence_id": p["evidence_id"],
                }
                | s
            )
        print(f"{p['url']}: {len(found)} statements, {sum(not s['cited'] for s in found)} without a citation")
    (a.dir / "claims_citations.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))
    print(f"{len(out)} claims · {calls} calls · {tokens[0]:,} input and {tokens[1]:,} output tokens")


if __name__ == "__main__":
    main()
