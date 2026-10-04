"""One test for each defect a pre-publication audit found. Each failed before its fix."""

import pytest

from receipts import Claim, Ledger, check_claim
from receipts.backends import ScriptedBackend
from receipts.cli import main
from receipts.fetch import FetchError, check_address
from receipts.reader import answers, check_with_reader
from receipts.text import figures_in, quote_passage


def verdict(page, text, quote, subject="Acme", title="Acme pricing", url="https://acme.example/pricing"):
    led = Ledger()
    ev = led.add_text(url, page, title)
    return check_claim(Claim("c", text, quote, ev.id, subject), led)


@pytest.mark.parametrize(
    "page,text,quote",
    [
        ("Acme price does not incl. taxes and fees.", "Acme price covers taxes and fees", "taxes and fees"),
        ("Acme is non-compliant with SOC 2 rules.", "Acme is compliant with SOC 2 rules", "compliant with SOC 2 rules"),
        ("Acme costs $19 per agent.", "Acme has 19 agents", "Acme costs $19 per agent."),
        ("Acme grew 19% last year.", "Acme grew by 19 customers last year", "Acme grew 19% last year."),
        ("Acme costs €19 per agent.", "Acme costs $19 per agent", "Acme costs €19 per agent."),
        (
            "Acme 2 runs version 1.2.3 of the engine.",
            "Acme 2 runs version 1.2.9 of the engine",
            "runs version 1.2.3 of the engine",
        ),
        ("Acme стоит 19 долларов.", "Acme оштрафована на 19 миллионов", "Acme стоит 19 долларов."),
    ],
)
def test_false_claims_that_used_to_pass(page, text, quote):
    assert not verdict(page, text, quote).supported


def test_a_price_is_not_part_of_the_product_name():
    v = verdict(
        "Microsoft 365 Basic costs $6.00 per user.",
        "Microsoft 365 costs $365 per year",
        "Microsoft 365 Basic costs $6.00 per user.",
        subject="Microsoft 365",
        title="Microsoft 365 plans",
    )
    assert v.reason == "figure_not_in_quote"


@pytest.mark.parametrize(
    "page,text,quote",
    [
        ("Acme has 5M users worldwide.", "Acme has 5 million users worldwide", "Acme has 5M users worldwide."),
        (
            "Acme takes five percent of each sale.",
            "Acme takes 5% of each sale",
            "Acme takes five percent of each sale.",
        ),
        ("Acme takes 5-15% of each sale.", "Acme takes 5% to 15% of each sale", "Acme takes 5-15% of each sale."),
        ("Acme raised $3-billion in 2021.", "Acme raised $3 billion in 2021", "Acme raised $3-billion in 2021."),
        ("Acme is fast... and it costs $49 a month.", "Acme costs $49 a month", "fast... and it costs $49 a month"),
        ("Acme café plan costs $9.", "Acme café plan costs $9", "Acme café plan costs $9."),
    ],
)
def test_true_claims_that_used_to_be_cut(page, text, quote):
    assert verdict(page, text, quote).supported


@pytest.mark.parametrize(
    "subject,title,url",
    [
        ("3M", "3M company profile", "https://example.org/3m"),
        ("Any.do", "Any.do pricing", "https://www.any.do/pricing"),
        ("Яндекс", "Яндекс цены", "https://example.org/y"),
    ],
)
def test_real_names_can_be_subjects(subject, title, url):
    v = verdict(
        f"{subject} costs $9 per month.",
        f"{subject} costs $9 per month",
        f"{subject} costs $9 per month.",
        subject,
        title,
        url,
    )
    assert v.supported


def test_the_ending_of_an_address_names_nothing():
    v = verdict(
        "The plan costs $9 per month.",
        "Com costs $9 per month",
        "The plan costs $9 per month.",
        subject="Com",
        title="Pricing",
        url="https://www.globex.com/pricing",
    )
    assert v.reason == "wrong_subject"


def test_passage_keeps_abbreviations_whole():
    page = "Acme Inc. was founded in the U.S. in 2010. It moved later."
    assert quote_passage("founded in the U.S. in 2010", page) == "acme inc. was founded in the u.s. in 2010."


def test_figures_read_as_written():
    assert figures_in("5m of cable, 5M users, 10k seats") == [("5", ""), ("5000000", ""), ("10000", "")]
    assert figures_in("$5-15 and 3 to 5 million") == [("5", "$"), ("15", "$"), ("3000000", ""), ("5000000", "")]
    assert figures_in("version 1.2.3") == []


def test_two_claims_with_one_id_cannot_stand_in_for_each_other():
    led = Ledger()
    ev = led.add_text("https://acme.example/p", "Acme costs $19 per month. Acme has a free trial.", "Acme")
    claims = [
        Claim("a", "Acme has a free trial for teams", "Acme has a free trial.", ev.id, "Acme"),
        Claim("a", "Acme costs $19 per month", "Acme costs $19 per month.", ev.id, "Acme"),
    ]
    reader = ScriptedBackend(
        [{"verdicts": [{"n": 1, "stated": False, "gap": "for teams"}, {"n": 2, "stated": True, "gap": ""}]}]
    )
    assert [v.supported for v in check_with_reader(claims, led, reader).verdicts] == [False, True]


@pytest.mark.parametrize("reply", [{"verdicts": ["x"]}, {"verdicts": None}, ["x"], None, {"verdicts": [{"n": 1}]}])
def test_a_malformed_reader_reply_cuts_instead_of_crashing(reply):
    led = Ledger()
    ev = led.add_text("https://acme.example/p", "Acme costs $19 per month.", "Acme")
    claims = [Claim("a", "Acme costs $19 per month", "Acme costs $19 per month.", ev.id, "Acme")]
    assert answers(reply) in ([], [{"n": 1}])
    assert check_with_reader(claims, led, ScriptedBackend([reply])).verdicts[0].reason == "unread"


@pytest.mark.parametrize("url", ["http://[::127.0.0.1]/", "http://[64:ff9b::7f00:1]/", "http://224.0.0.1/"])
def test_wrapped_and_multicast_addresses_are_refused(url):
    with pytest.raises(FetchError):
        check_address(url)


@pytest.mark.parametrize("content", ['["not an object"]', '{"no_claims": 1}', "not json"])
def test_cli_reports_bad_input_without_a_traceback(tmp_path, capsys, content):
    Ledger().save(tmp_path / "l.json")
    (tmp_path / "c.json").write_text(content)
    assert main(["check", str(tmp_path / "c.json"), "--ledger", str(tmp_path / "l.json"), "--code-only"]) == 2
    assert main(["check", str(tmp_path / "missing.json"), "--ledger", str(tmp_path / "l.json"), "--code-only"]) == 2
    assert "receipts:" in capsys.readouterr().err
