"""The numbers in the README and studies/RESULTS.md, rebuilt from the test sets with no model."""

import json
import subprocess
import sys
from pathlib import Path

BENCH = Path(__file__).parent.parent / "bench"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True, capture_output=True, cwd=BENCH.parent)


def test_round_1_code_check_alone():
    run("bench/run.py")
    r = json.loads((BENCH / "RESULT_round1_code_only.json").read_text())
    assert (r["clean"]["left_alone"], r["clean"]["n"]) == (58, 60)
    assert (r["mechanical"]["caught"], r["mechanical"]["n"]) == (43, 50)
    assert r["invented"]["meaning_changed"]["caught"] == 0


def test_round_2_both_stages_from_the_saved_readings():
    run("bench/run_two_stage.py", "round2", "--replay")
    r = json.loads((BENCH / "RESULT_round2_two_stage.json").read_text())
    assert (r["types"]["clean"]["left_alone"], r["invented"]["caught"], r["invented"]["n"]) == (52, 60, 60)
    assert set(r["types"]["clean"]["cut_by"]) <= {
        "beyond_quote",
        "polarity_mismatch",
        "figure_not_in_quote",
    }  # none by the reader


def test_round_1_both_stages_from_the_saved_readings():
    run("bench/run_two_stage.py", "round1", "--replay")
    r = json.loads((BENCH / "RESULT_round1_two_stage.json").read_text())
    assert (r["types"]["clean"]["left_alone"], r["invented"]["caught"]) == (58, 59)


def test_red_team_sets_and_the_fix_between_them():
    for args in (["redteam"], ["redteam", "--after-fix"], ["redteam2"], ["redteam2", "--shipped"]):
        run("bench/run_redteam.py", *args, "--replay")
    first = json.loads((BENCH / "RESULT_redteam.json").read_text())
    fixed = json.loads((BENCH / "RESULT_redteam_after_fix.json").read_text())
    second = json.loads((BENCH / "RESULT_redteam2.json").read_text())
    assert (first["past_code"], first["past_both"]) == (40, 9)
    assert fixed["past_both"] == 0
    assert (second["past_code"], second["past_both"]) == (40, 15)
    shipped = json.loads((BENCH / "RESULT_redteam2_shipped.json").read_text())
    assert (shipped["past_code"], shipped["past_both"]) == (40, 16)
    assert second["by_technique"]["next_sentence_retraction"] == {"written": 6, "past_code": 6, "past_both": 6}


def test_the_code_check_has_not_loosened_on_the_red_team_sets():
    from receipts import Claim, Ledger, check_claim

    for name, corpus, ceiling in (("redteam", "corpus2", 37), ("redteam2", "corpus", 40)):
        ledger = Ledger.load(BENCH / corpus / "ledger.json")
        rows = [json.loads(x) for x in (BENCH / f"{name}.jsonl").read_text().splitlines() if x.strip()]
        passed = sum(
            check_claim(Claim(r["id"], r["text"], r["quote"], r["evidence_id"], r["company"]), ledger).supported
            for r in rows
        )
        assert passed <= ceiling


def test_real_pages_labelled_blind():
    run("bench/traces/score.py")
    r = json.loads((BENCH / "traces" / "RESULT_traces.json").read_text())
    assert (r["kept"], r["facts"]) == (43, 59)
    for row in r["labellers"].values():
        assert row["kept_facts_the_page_states"] == [43, 43]
        assert row["page_true_facts_kept"] == [43, 59]
    assert r["labellers_agree_on_quote_states"] == [48, 59]


def test_the_reader_repeated_three_times():
    r = json.loads((BENCH / "RESULT_round2_repeats.json").read_text())
    assert r["pairs_read"] == 76 and len(r["runs"]) == 3 and r["claims_with_a_different_verdict_in_any_run"] == []


def test_both_rounds_on_the_code_as_shipped():
    for name, clean, caught in (("round1", 58, 58), ("round2", 52, 60)):
        r = json.loads((BENCH / f"RESULT_{name}_two_stage_shipped.json").read_text())
        assert (r["types"]["clean"]["left_alone"], r["invented"]["caught"]) == (clean, caught)
