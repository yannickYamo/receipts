"""Once a measurement has started, the code that decides a claim does not change under it."""

import importlib.util
import json
from pathlib import Path

STUDY = Path(__file__).parent.parent / "bench" / "study"


def test_the_code_being_measured_is_the_code_that_was_frozen():
    record = STUDY / "FROZEN.json"
    if not record.exists():  # nothing is being measured yet
        return
    spec = importlib.util.spec_from_file_location("study", STUDY / "study.py")
    study = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(study)
    frozen, now = json.loads(record.read_text()), study.frozen_now()
    assert now["files"] == frozen["files"] and now["reader_prompt"] == frozen["reader_prompt"], (
        "core.py, text.py or reader.py changed after the freeze: every number measured on the frozen code "
        "no longer describes this code. Undo the change, or start the round again and freeze anew."
    )
