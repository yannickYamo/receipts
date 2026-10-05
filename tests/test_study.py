"""The study's scorer on a set small enough to count by hand. No model."""

import json
import subprocess
import sys
from pathlib import Path

from receipts import Ledger

STUDY = Path(__file__).parent.parent / "bench" / "study" / "study.py"
PAGE = "Acme Starter costs $20 per seat per month. Acme was founded in 2010. Acme has offices in Lisbon."


def test_every_arm_is_scored_on_the_same_claims(tmp_path):
    led = Ledger()
    ev = led.add_text("https://acme.example/p", PAGE, "Acme")
    led.save(tmp_path / "ledger.json")
    claims = [  # id, text, quote, the page states it, the reader says yes
        ("true", "Acme Starter costs $20 per seat per month", "Acme Starter costs $20 per seat per month.", True, True),
        ("true-cut", "Acme was founded in 2010", "Acme was founded in 2010.", True, False),
        (
            "wrong-figure",
            "Acme Starter costs $25 per seat per month",
            "Acme Starter costs $20 per seat per month.",
            False,
            True,
        ),
        ("not-on-page", "Acme has 900 integrations", "Acme includes 900 integrations.", False, True),
        ("meaning", "Acme has offices outside Lisbon", "Acme has offices in Lisbon.", False, False),
    ]
    base = {"extractor": "haiku", "kind": "pricing", "subject": "Acme", "evidence_id": ev.id}
    (tmp_path / "claims.jsonl").write_text(
        "".join(json.dumps(base | {"id": i, "text": t, "quote": q}) + "\n" for i, t, q, _, _ in claims)
    )
    (tmp_path / "labels_final.jsonl").write_text(
        "".join(json.dumps({"id": i, "page_states": s, "quote_states": s}) + "\n" for i, _, _, s, _ in claims)
    )
    readings = {i: [yes, ""] for i, _, _, _, yes in claims if i != "not-on-page"}  # one claim got no answer
    (tmp_path / "readings.json").write_text(json.dumps({"reader": "scripted", "readings": readings}))
    out = subprocess.run(
        [sys.executable, str(STUDY), "score", "--dir", str(tmp_path)], check=True, capture_output=True, text=True
    ).stdout
    r = json.loads((tmp_path / "RESULT_study.json").read_text())
    kept = {arm: (v["unsupported_kept"][0], v["true_kept"][0]) for arm, v in r["by_page_states"].items()}
    assert kept == {
        "keep_all": (3, 2),  # the bare model keeps all three unsupported claims
        "quote_on_page": (2, 2),  # an exact quote stops the invented one, not the changed figure
        "code_only": (1, 2),  # the code check stops the figure too; the meaning change passes
        "reader_only": (1, 1),  # the reader alone passes the changed figure it was told is stated
        "both": (0, 1),
    }
    assert r["base_rate"] == {"unsupported": 3, "of": 5, "interval": r["base_rate"]["interval"]}
    assert r["enough_unsupported_to_report_a_share"] is False and "the finding is the base rate" in out
    assert r["by_page_states"]["both"]["unsupported_kept"][1:2] == [3]
