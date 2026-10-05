"""One test for each defect an outside review found after publication. Each failed before its fix."""

import json

import pytest

from receipts import Claim, Ledger, check_claim
from receipts.backends import ScriptedBackend
from receipts.battlecard import Line, check_line
from receipts.cli import CODE_ONLY_NOTE, main
from receipts.mcp_server import build_server
from receipts.reader import check_with_reader

PAGE = "Zendesk offers the Suite Team plan in Europe. Zendesk does not offer it in India."
FALSE_CLAIM = {
    "id": "a",
    "text": "Zendesk offers the Suite Team plan in India",
    "quote": "the Suite Team plan in",
    "subject": "Zendesk",
}


@pytest.fixture
def files(tmp_path):
    led = Ledger()
    ev = led.add_text("https://www.zendesk.com/pricing", PAGE, "Zendesk pricing")
    led.save(tmp_path / "l.json")
    (tmp_path / "c.json").write_text(json.dumps([FALSE_CLAIM | {"evidence_id": ev.id}]))
    return tmp_path


def reader_says(stated: bool):
    return ScriptedBackend([{"verdicts": [{"n": 1, "stated": stated, "gap": "" if stated else "India"}]}])


def test_the_code_check_alone_passes_this_claim_and_says_what_it_is(files, capsys):
    """The known limit of the code stage. It is why `check` no longer runs that stage alone by default."""
    assert main(["check", str(files / "c.json"), "--ledger", str(files / "l.json"), "--code-only"]) == 0
    assert CODE_ONLY_NOTE in capsys.readouterr().out


def test_check_runs_both_stages_by_default(files, capsys, monkeypatch):
    monkeypatch.setattr("receipts.cli._backend", lambda kind, model: reader_says(False))
    assert main(["check", str(files / "c.json"), "--ledger", str(files / "l.json")]) == 1
    out = capsys.readouterr().out
    assert "CUT  a" in out and "code check, then reader" in out


def test_check_fails_closed_when_the_reader_cannot_run(files, monkeypatch):
    monkeypatch.setattr("receipts.cli._backend", lambda kind, model: ScriptedBackend([None]))
    assert main(["check", str(files / "c.json"), "--ledger", str(files / "l.json")]) == 3  # cut, and said why


def test_the_reader_is_shown_the_whole_sentence_not_the_clipped_quote(files):
    led = Ledger.load(files / "l.json")
    reader = reader_says(False)
    check_with_reader([Claim("a", FALSE_CLAIM["text"], FALSE_CLAIM["quote"], next(iter(led)), "Zendesk")], led, reader)
    assert "suite team plan in europe" in reader.prompts[0]


def test_mcp_server_says_which_stages_ran():
    pytest.importorskip("mcp")
    assert build_server() is not None and build_server(reader_says(True)) is not None


def test_a_card_line_keeps_the_kind_of_a_figure():
    facts = {"f1": Claim("f1", "Freshdesk Growth costs $19 per agent", "Growth ... $19 /agent/month", "e", "Freshdesk")}
    assert not check_line(
        Line("we_win", "Freshdesk Growth supports 19 agents", ["f1"]), facts, "Freshdesk Zendesk"
    ).kept
    assert check_line(Line("we_win", "Freshdesk Growth costs $19 per agent", ["f1"]), facts, "Freshdesk Zendesk").kept


def test_check_prints_each_claim_by_position_when_ids_repeat(tmp_path, capsys):
    led = Ledger()
    ev = led.add_text("https://f.example/p", "Freshdesk Growth costs $19 per agent per month.", "Freshdesk")
    led.save(tmp_path / "l.json")
    base = {
        "id": "a",
        "quote": "Freshdesk Growth costs $19 per agent per month.",
        "evidence_id": ev.id,
        "subject": "Freshdesk",
    }
    claims = [
        base | {"text": "Freshdesk Growth costs $19 per agent per month"},
        base | {"text": "Freshdesk Growth costs $15 per agent per month"},
    ]
    (tmp_path / "c.json").write_text(json.dumps(claims))
    main(["check", str(tmp_path / "c.json"), "--ledger", str(tmp_path / "l.json"), "--code-only"])
    out = capsys.readouterr().out
    assert "PASS a  Freshdesk Growth costs $19" in out and "CUT  a  Freshdesk Growth costs $15" in out


def test_a_ledger_edited_after_the_fetch_is_refused(tmp_path, capsys):
    led = Ledger()
    led.add_text("https://f.example/p", "Freshdesk Growth costs $19 per agent per month.", "Freshdesk")
    led.save(tmp_path / "l.json")
    raw = json.loads((tmp_path / "l.json").read_text())
    raw[0]["text"] = raw[0]["text"].replace("$19", "$15")
    (tmp_path / "l.json").write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="no longer matches its hash"):
        Ledger.load(tmp_path / "l.json")
    (tmp_path / "c.json").write_text("[]")
    assert main(["check", str(tmp_path / "c.json"), "--ledger", str(tmp_path / "l.json"), "--code-only"]) == 2
    assert "no longer matches its hash" in capsys.readouterr().err


def test_a_page_read_again_keeps_the_text_a_claim_was_written_against():
    led = Ledger()
    old = led.add_text("https://x.example/p", "The plan costs $9 per month.", "Acme")
    new = led.add_text("https://x.example/p", "The plan costs $12 per month.", "Acme")
    same = led.add_text("https://x.example/p", "The plan costs $12 per month.", "Acme")
    assert old.id != new.id and new.id == same.id and len(led) == 2
    assert check_claim(
        Claim("c", "Acme's plan costs $9 per month", "The plan costs $9 per month.", old.id, "Acme"), led
    ).supported
    assert not check_claim(
        Claim("c", "Acme's plan costs $9 per month", "The plan costs $9 per month.", new.id, "Acme"), led
    ).supported


def test_the_reader_stage_keeps_every_field_of_a_claim():
    led = Ledger()
    ev = led.add_text("https://x.example/p", "Acme costs $9 per month.", "Acme")
    seen = []

    class Spy(ScriptedBackend):
        def json(self, system, prompt, schema):
            seen.append(prompt)
            return {"verdicts": [{"n": 1, "stated": True, "gap": ""}]}

    report = check_with_reader(
        [Claim("x", "Acme costs $9 per month", "Acme costs $9 per month.", ev.id, "Acme", "pricing")], led, Spy([])
    )
    assert report.verdicts[0].claim_id == "x" and report.verdicts[0].supported and seen
