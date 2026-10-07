"""Once a measurement has started, the code that decides a claim does not change under it."""

import importlib.util
import json
from pathlib import Path

BENCH = Path(__file__).parent.parent / "bench"


def study():
    spec = importlib.util.spec_from_file_location("study", BENCH / "study" / "study.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_code_being_measured_is_the_code_that_was_frozen():
    now = study().frozen_now()
    for record in BENCH.glob("*/FROZEN.json"):  # every round that has frozen; a round that is over is closed
        frozen = json.loads(record.read_text())
        if frozen.get("closed"):
            continue
        assert now["files"] == frozen["files"] and now["reader_prompt"] == frozen["reader_prompt"], (
            f"{record}: core.py, text.py or reader.py changed after the freeze: every number measured on the frozen "
            "code no longer describes this code. Undo the change, or start the round again and freeze anew."
        )


def test_a_closed_round_keeps_its_record_and_lets_the_code_move_on(tmp_path):
    import argparse

    s = study()
    s.freeze(argparse.Namespace(dir=tmp_path))
    record = json.loads((tmp_path / "FROZEN.json").read_text())
    record["files"]["text.py"] = "0000000000000000"  # as if text.py had changed since
    (tmp_path / "FROZEN.json").write_text(json.dumps(record))
    s.close(argparse.Namespace(dir=tmp_path, note="round 3, measured on 0.2.0"))
    closed = json.loads((tmp_path / "FROZEN.json").read_text())
    assert closed["closed"] == "round 3, measured on 0.2.0" and closed["files"]["text.py"] == "0000000000000000"
