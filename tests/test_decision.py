"""A reader that answers with a probability, and the bake-off that puts it beside the measured reader. No model."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

from receipts import Claim, Ledger
from receipts.backends import BackendError
from receipts.decision import CRITERIA, INSTRUCTIONS, JevBackend, check_with_decider, state_of

BENCH = Path(__file__).parent.parent / "bench"
BAKEOFF = BENCH / "bakeoff" / "bakeoff.py"
PAGE = (
    "Zoom was founded in 2011. In July 2021, Zoom announced plans to acquire Five9 for $14.7 billion. "
    "The deal was called off in September 2021. Zoom is based in San Jose."
)


def claims():
    led = Ledger()
    ev = led.add_text("https://zoom.example/history", PAGE, "Zoom")
    return led, [
        Claim("a", "Zoom was founded in 2011", "Zoom was founded in 2011.", ev.id, "Zoom"),
        Claim(
            "b",
            "Zoom is acquiring Five9 for $14.7 billion",
            "Zoom announced plans to acquire Five9 for $14.7 billion",
            ev.id,
            "Zoom",
        ),
        Claim("c", "Zoom was founded in 2012", "Zoom was founded in 2011.", ev.id, "Zoom"),
    ]


class Fixed:
    """A stand-in decision model: the probability it gives depends on the claim."""

    name, calls = "fixed", 0

    def __init__(self, by_claim, fail=()):
        self.by_claim, self.fail, self.states = by_claim, set(fail), []

    def probability(self, state, instructions, criteria):
        self.calls += 1
        self.states.append(state)
        if state["claim"] in self.fail:
            raise BackendError("429 rate limit")
        return self.by_claim[state["claim"]]


def test_a_claim_stands_when_the_probability_reaches_the_threshold_and_only_code_passers_are_read():
    led, cs = claims()
    model = Fixed({cs[0].text: 0.97, cs[1].text: 0.31})
    report = check_with_decider(cs, led, model, threshold=0.5)
    assert [(v.supported, v.reason) for v in report.verdicts] == [
        (True, "ok"),
        (False, "not_stated"),
        (False, "figure_not_in_quote"),
    ]
    assert report.verdicts[1].detail == "probability 0.31 that the quote states it, under 0.50"
    assert model.calls == 2  # the claim the code check cut never reaches the model
    shown = model.states[1]
    assert (
        shown["after"].startswith("the deal was called off")
        and shown["page_title"] == "Zoom"
        and "between" not in shown
    )
    assert check_with_decider(cs, led, Fixed({cs[0].text: 0.97, cs[1].text: 0.31}), threshold=0.3).verdicts[1].supported
    with pytest.raises(ValueError):
        check_with_decider(cs, led, model, threshold=0)


def test_a_claim_the_model_gives_no_answer_for_is_cut_after_one_more_try():
    led, cs = claims()
    model = Fixed({cs[0].text: 0.9}, fail=[cs[1].text])
    report = check_with_decider(cs[:2], led, model)
    assert (report.verdicts[1].supported, report.verdicts[1].reason, report.verdicts[1].detail) == (
        False,
        "unread",
        "429 rate limit",
    )
    assert model.calls == 3  # one for the first claim, two for the one that failed


def test_the_jev_client_asks_one_yes_or_no_question_and_reads_back_a_probability(monkeypatch):
    sent = []

    def post(url, headers, body):
        sent.append((url, headers, body))
        return {
            "model": "jev-1.13.0",
            "answers": {"stated": {"type": "noul", "noul": 0.11}},
            "usage": {"input_tokens": 392, "output_tokens": 65},
        }

    led, cs = claims()
    jev = JevBackend(api_key="k", post=post)
    assert jev.probability(state_of(cs[1], led[cs[1].evidence_id]), INSTRUCTIONS, CRITERIA) == 0.11
    url, headers, body = sent[0]
    assert url == "https://api.typesafe.ai/v1/systemone" and headers["Authorization"] == "Bearer k"
    assert body["model"] == "jev-latest" and body["questions"]["stated"]["type"] == "noul"
    assert body["state"]["claim"] == cs[1].text and set(body["questions"]["stated"]["criteria"]) == {"true", "false"}
    assert jev.served_by == "jev-1.13.0" and jev.tokens == {"input": 392, "output": 65} and jev.calls == 1
    for reply in (
        {"answers": {}},
        {"answers": {"stated": {"noul": "high"}}},
        {"answers": {"stated": {"noul": 1.4}}},
        {"error": "x"},
    ):
        with pytest.raises(BackendError):
            JevBackend(api_key="k", post=lambda u, h, b, r=reply: r).probability({}, "q", {})
    monkeypatch.delenv("TYPESAFE_API_KEY", raising=False)
    with pytest.raises(BackendError, match="TYPESAFE_API_KEY"):
        JevBackend()


def bakeoff():
    spec = importlib.util.spec_from_file_location("bakeoff", BAKEOFF)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def score(tmp_path, name, sets):
    record = {"reader": name, "kind": "decision", "prompt_version": "x", "calls": 1, "seconds": 23.0, "sets": sets}
    (tmp_path / f"probabilities_{name}.json").write_text(json.dumps(record))
    out = subprocess.run(
        [sys.executable, str(BAKEOFF), "score", "--name", name, "--dir", str(tmp_path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads((tmp_path / f"RESULT_bakeoff_{name}.json").read_text()), out


def test_the_bake_off_puts_a_reader_beside_the_measured_one_on_the_saved_sets(tmp_path):
    b = bakeoff()
    measured = {name: b.baseline(name, BENCH)[0] for name in ("round1", "round2", "redteam", "redteam2")}
    same = {name: {cid: 0.9 if kept else 0.1 for cid, kept in answers.items()} for name, answers in measured.items()}
    r, out = score(tmp_path, "same", same)
    assert r["threshold_rule_met_on_round_1"] and r["level_with_the_measured_reader"] and all(r["bars"].values())
    two = r["sets"]["round2"]
    assert (
        (two["new"]["true_kept"], two["new"]["unsupported_cut"])
        == (52, 60)
        == (two["measured"]["true_kept"], two["measured"]["unsupported_cut"])
    )
    assert r["sets"]["redteam2"]["new"]["unsupported_past_both"] == 16 and "level with the measured reader" in out
    assert two["brier"] == 0.01 and r["seconds_per_claim"] > 0 and "0.5" in two["curve"]

    yes = {
        name: {cid: 0.99 for cid in answers} for name, answers in measured.items()
    }  # a reader that passes everything
    r, out = score(tmp_path, "yes", yes)
    assert not r["threshold_rule_met_on_round_1"] and not r["level_with_the_measured_reader"]
    assert r["sets"]["redteam2"]["new"]["unsupported_past_both"] == 40 and not r["bars"]["redteam2_past_both"]
    assert "not level with the measured reader" in out


def test_the_threshold_comes_from_round_one_alone_by_a_fixed_rule():
    b = bakeoff()
    rows = [{"claim": Claim(f"t{i}", "", "", "", ""), "true": True, "past_code": True} for i in range(4)]
    rows += [{"claim": Claim(f"f{i}", "", "", "", ""), "true": False, "past_code": True} for i in range(4)]
    p = {"t0": 0.9, "t1": 0.8, "t2": 0.6, "t3": 0.3, "f0": 0.7, "f1": 0.4, "f2": 0.2, "f3": 0.1}
    # To cut at least 3 of the 4 unsupported claims the threshold must be above 0.4; the lowest such keeps the most true ones.
    assert b.pick_threshold(rows, p, {"unsupported_cut": 3}) == (0.6, True)
    assert b.pick_threshold(rows, p, {"unsupported_cut": 4}) == (
        0.8,
        True,
    )  # 0.75 and 0.8 keep the same two: the higher
    always_yes = dict.fromkeys(p, 1.0)
    assert (
        b.pick_threshold(rows, always_yes, {"unsupported_cut": 1})[1] is False
    )  # nothing cuts enough: said, not hidden
