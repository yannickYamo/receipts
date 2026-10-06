"""The brief on a company: pages chosen by code, signals checked like any claim, and lines that stand on them."""

import json

import pytest

from receipts.backends import ScriptedBackend
from receipts.brief import build_brief, names_a_person, panel_text, pick_pages, render_html
from receipts.cli import main
from receipts.fetch import FetchError, links_in

SELL = "Deskly, a help desk for support teams of 10 to 200 agents"
HOME = "https://www.acme.example/"
SITE = {
    HOME: ("Acme: freight software", "Acme makes routing software for freight carriers. " * 6),
    "https://www.acme.example/press": (
        "Acme press",
        "We opened our Lisbon support hub on 12 September 2026. "
        "Acme agreed to acquire Globex in May. The deal was called off in July after a review. "
        "Our CEO Jane Doe said the hub will grow quickly. " * 3,
    ),
    "https://www.acme.example/careers": (
        "Careers at Acme",
        "Open roles\nCustomer Support\n14 open roles\nEngineering\n3 open roles\n" + "Join us. " * 30,
    ),
}
LINKS = [
    ("https://www.acme.example/press", "Press"),
    ("https://www.acme.example/press/2026/lisbon", "Lisbon hub"),
    ("https://www.acme.example/careers", "Careers"),
    ("https://jobs.other.example/acme", "Jobs"),
    ("https://www.acme.example/brand.pdf", "about"),
    ("https://www.acme.example/pricing", "Pricing"),
]


@pytest.fixture
def web(monkeypatch):
    def fake_fetch(url, **kw):
        if url not in SITE:
            raise FetchError("the site answered 404")
        return SITE[url]

    monkeypatch.setattr("receipts.ledger.fetch", fake_fetch)
    monkeypatch.setattr("receipts.brief.pipeline.fetch_with_links", lambda url, **kw: (*fake_fetch(url), LINKS))


def scripted(lines=None):
    home = {
        "facts": [
            {
                "text": "Acme makes routing software for freight carriers",
                "quote": "Acme makes routing software for freight carriers.",
                "topic": "company",
            }
        ]
    }
    press = {
        "facts": [
            {
                "text": "Acme opened a support hub in Lisbon on 12 September 2026",
                "quote": "We opened our Lisbon support hub on 12 September 2026.",
                "topic": "expansion",
            },
            {
                "text": "Acme agreed to acquire Globex in May",
                "quote": "Acme agreed to acquire Globex in May.",
                "topic": "company",
            },
            {
                "text": "Acme CEO Jane Doe said the hub will grow quickly",
                "quote": "Our CEO Jane Doe said the hub will grow quickly.",
                "topic": "expansion",
            },
            {
                "text": "Acme raised $40 million",
                "quote": "We opened our Lisbon support hub on 12 September 2026.",
                "topic": "funding",
            },
        ]
    }
    careers = {
        "facts": [
            {
                "text": "Acme has 14 open roles in customer support",
                "quote": "Customer Support ... 14 open roles",
                "topic": "hiring",
            }
        ]
    }
    written = lines or {
        "why_now": [
            {
                "text": "A new support hub and 14 open support roles mean a support team that is growing now",
                "cites": ["f2", "f6"],
            },
            {"text": "Acme probably has outgrown its current tools", "cites": []},
        ],
        "message": [
            {"text": "Hi, I read that you opened a support hub in Lisbon in September.", "cites": ["f2"]},
            {"text": "Deskly is a help desk for support teams of 10 to 200 agents.", "cites": ["you"]},
            {"text": "Teams like yours cut reply times by 40% with us.", "cites": []},
            {"text": "Would a short call next week be useful?", "cites": []},
        ],
    }
    return ScriptedBackend([home, press, careers, {"quotes": []}, written])


def test_code_picks_the_pages_from_the_site_itself_and_never_from_another():
    picked = pick_pages(HOME, LINKS, 3)
    assert picked == [
        "https://www.acme.example/press",
        "https://www.acme.example/careers",
    ]  # one of each kind, in order
    assert pick_pages(HOME, LINKS, 1) == ["https://www.acme.example/press"]
    html = '<a href="/press#top">Press</a> <a href="mailto:x@acme.example">mail</a> <a href="https://[bad">x</a>'
    assert links_in(html, HOME) == [("https://www.acme.example/press", "Press")]


def test_a_brief_keeps_what_the_pages_state_and_lists_what_it_cut(web):
    backend = scripted()
    brief = build_brief(SELL, HOME, backend)
    assert brief.company == "Acme" and [e.url for e in brief.card.ledger.values()] == list(SITE)
    assert [c.id for c in brief.signals] == [
        "f1",
        "f2",
        "f3",
        "f6",
    ]  # code alone keeps the acquisition: see the next test
    assert brief.card.verdicts["f5"].reason == "figure_not_in_quote"  # "$40 million" is nowhere in its quote
    assert brief.skipped == [("Acme CEO Jane Doe said the hub will grow quickly", "it names a person (Jane Doe)")]
    kept = {x.text for x in brief.card.lines if x.kept}
    cut = {x.text: x.reason for x in brief.card.lines if not x.kept}
    assert "Hi, I read that you opened a support hub in Lisbon in September." in kept
    assert "Deskly is a help desk for support teams of 10 to 200 agents." in kept  # rests on the seller's own words
    assert "Would a short call next week be useful?" in kept
    assert cut["Acme probably has outgrown its current tools"] == "it cites no signal"
    assert cut["Teams like yours cut reply times by 40% with us."] == "it states a figure and cites no signal"
    s = brief.stats()
    assert (s["signals_supported"], s["signals_proposed"], s["left_out_for_naming_a_person"]) == (4, 5, 1)
    assert "f5" not in backend.prompts[4] and "Jane" not in backend.prompts[4]  # the writer never sees what was cut


def test_the_reader_cuts_a_signal_the_page_takes_back_and_a_line_that_adds_a_fact(web):
    def facts_reader(prompt):  # says no to the acquisition, whose next sentence on the page calls it off
        claims = [p.split("Claim: ")[1].split("\n")[0] for p in prompt.split("</pair>")[:-1]]
        return {
            "verdicts": [{"n": i + 1, "stated": "acquire" not in c, "gap": "called off"} for i, c in enumerate(claims)]
        }

    def advice_reader(prompt):
        items = prompt.split("</item>")[:-1]
        return {
            "verdicts": [
                {"n": i + 1, "adds_fact": "market leader" in it, "what": "market leader"} for i, it in enumerate(items)
            ]
        }

    lines = {
        "why_now": [{"text": "A new support hub means a growing support team", "cites": ["f2"]}],
        "message": [
            {"text": "I read that you opened a support hub in Lisbon.", "cites": ["f2"]},
            {"text": "As the market leader in freight software you must feel this.", "cites": ["f1"]},
        ],
    }
    reader = ScriptedBackend([facts_reader] * 3 + [advice_reader])
    brief = build_brief(SELL, HOME, scripted(lines), reader=reader)
    assert brief.card.verdicts["f3"].reason == "not_stated"  # the next sentence on the page calls the deal off
    assert any("the deal was called off" in p for p in reader.prompts)  # the reader was shown that sentence
    cut = {x.text: x.reason for x in brief.card.lines if not x.kept}
    assert "adds a fact" in cut["As the market leader in freight software you must feel this."]
    assert [x.text for x in brief.lines("message")] == ["I read that you opened a support hub in Lisbon."]
    assert "prompt" in panel_text(brief) and "not measured" in panel_text(brief)


def test_a_person_is_recognised_in_the_shapes_a_press_page_uses_and_places_are_not():
    for text in (
        "Acme CEO Jane Doe said the hub will grow",
        "Acme appointed Jane Doe as head of support",
        "Jane Doe, its new head of support, joined in May",
        "Dr. Jane Doe leads research at Acme",
        "Jane Smith-Jones was appointed to the board",
    ):
        assert names_a_person(text, "Acme"), text
    for text in (
        "Acme is hiring a Head of Support in New York",
        "Acme opened its Lisbon Support Hub in September",
        "Acme has 14 open roles in Customer Support",
        "Acme Cloud said to cut routing time",
        "Acme hired 40 engineers in North America",
    ):
        assert not names_a_person(text, "Acme Cloud"), text


def test_the_page_escapes_everything_links_every_signal_and_says_what_rests_on_the_user(web):
    brief = build_brief(SELL + " <b>fast</b>", HOME, scripted())
    html = render_html([brief])
    assert "&lt;b&gt;fast" in html and "<b>fast" not in html
    assert html.count("https://www.acme.example/press") >= 2 and "rests on what you sell, in your words" in html
    assert "$40 million" in html.split("Cut before it reached this page")[1]
    assert "$40 million" not in html.split("Cut before it reached this page")[0]
    assert "Jane Doe" not in html.split("Cut before it reached this page")[0]
    assert "is in your words and is not checked" in panel_text(brief)


def test_a_company_whose_pages_cannot_be_read_gets_no_lines_and_says_why(monkeypatch):
    def refused(url, **kw):
        raise FetchError("the site answered 403")

    monkeypatch.setattr("receipts.brief.pipeline.fetch_with_links", refused)
    brief = build_brief(SELL, HOME, ScriptedBackend([]))
    assert not brief.signals and not brief.card.lines and brief.card.unread[0][2] == "the site answered 403"
    assert "no signal about the company could be supported" in brief.card.notes[0]


def test_the_command_writes_the_page_the_data_and_the_ledger(web, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr("receipts.cli._backend", lambda kind, model: scripted())
    args = ["brief", "--sell", SELL, "--company", f"Acme={HOME}", "--reader-model", "none", "--out", str(tmp_path)]
    assert main(args) == 0
    data = json.loads((tmp_path / "brief.json").read_text())
    assert data[0]["company"] == "Acme" and data[0]["stats"]["signals_supported"] == 4
    assert data[0]["left_out"][0]["why"].startswith("it names a person")
    assert all("you" not in line["cites"] for line in data[0]["lines"])  # the user's own words are not a source
    assert (tmp_path / "brief.html").exists() and (tmp_path / "ledger-1.json").exists()
    assert "signals   4 of 5 supported" in capsys.readouterr().out
    assert main(["brief", "--sell", SELL, "--company", "Acme", "--out", str(tmp_path)]) == 2
    assert "--company takes an address" in capsys.readouterr().err


def test_the_brief_study_scores_three_bars_from_a_run_and_its_labels(web, tmp_path):
    import subprocess
    import sys
    from pathlib import Path

    study = Path(__file__).parent.parent / "bench" / "brief" / "study.py"
    brief = build_brief(SELL, HOME, scripted(), company="Acme")
    (tmp_path / "brief.json").write_text(json.dumps([brief.to_dict()]))
    out = subprocess.run(
        [sys.executable, str(study), "sheet", "--dir", str(tmp_path)], capture_output=True, text=True, check=True
    ).stdout
    signals = [json.loads(x) for x in (tmp_path / "sheet_signals.jsonl").read_text().splitlines()]
    lines = [json.loads(x) for x in (tmp_path / "sheet_lines.jsonl").read_text().splitlines()]
    assert "5 signals and 6 lines to label" in out and "kept" not in signals[0] and "kept" not in lines[0]
    assert all("ledger" in s and s["page"].startswith("https://www.acme.example") for s in signals)
    labels = [
        {
            "id": s["id"],
            "page_states": "$40 million" not in s["text"] and "acquire" not in s["text"],
            "names_a_person": False,
        }
        for s in signals
    ]
    labels += [
        {"id": x["id"], "adds_fact": "40%" in x["text"] or "next week" in x["text"], "names_a_person": False}
        for x in lines
    ]
    (tmp_path / "labels_final.jsonl").write_text("".join(json.dumps(r) + "\n" for r in labels))
    subprocess.run(
        [sys.executable, str(study), "score", "--dir", str(tmp_path)], capture_output=True, text=True, check=True
    )
    r = json.loads((tmp_path / "RESULT_brief.json").read_text())
    assert (r["kept_signals_the_page_states"]["k"], r["kept_signals_the_page_states"]["n"]) == (
        3,
        4,
    )  # code alone kept the acquisition
    assert not r["kept_signals_the_page_states"]["passes"]
    assert (r["true_signals_kept"]["k"], r["true_signals_kept"]["n"], r["true_signals_kept"]["passes"]) == (3, 3, True)
    assert r["kept_lines_that_add_a_fact"]["k"] == 1 and not r["kept_lines_that_add_a_fact"]["passes"]  # "next week"
    assert r["lines_cut"] == [2, 6] and r["lines_cut_that_added_no_fact"] == 1
