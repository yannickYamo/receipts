from datetime import datetime, timezone

import pytest

from receipts import Claim, Ledger, check_claim, check_claims

PAGE = (
    "Acme Starter starts at $20 per seat per month. Acme does not support on-premise deployment. "
    "The Professional plan includes 5 seats. No credit card is required for the free trial."
)


@pytest.fixture
def ledger():
    led = Ledger()
    led.add_text("https://acme.example/pricing", PAGE, "Acme pricing", fetched_at="2026-01-01T00:00:00+00:00")
    return led


def claim(text, quote, subject="Acme", evidence=None, led=None):
    return Claim("c", text, quote, evidence or next(iter(led)), subject)


def test_supported(ledger):
    v = check_claim(
        claim(
            "Acme's Starter plan starts at $20 per seat each month",
            "Acme Starter starts at $20 per seat per month.",
            led=ledger,
        ),
        ledger,
    )
    assert v.supported and v.match == "exact" and v.url.endswith("/pricing")


@pytest.mark.parametrize(
    "text,quote,subject,reason",
    [
        (
            "Acme Starter starts at $15 per seat per month",
            "Acme Starter starts at $20 per seat per month.",
            "Acme",
            "figure_not_in_quote",
        ),
        (
            "Acme supports on-premise deployment",
            "Acme does not support on-premise deployment.",
            "Acme",
            "polarity_mismatch",
        ),
        ("Acme's free trial is not available", "The Professional plan includes 5 seats.", "Acme", "beyond_quote"),
        ("Globex Starter starts at $20 per seat", "The Professional plan includes 5 seats.", "Globex", "wrong_subject"),
        (
            "Acme is the market leader in every segment",
            "The Professional plan includes 5 seats.",
            "Acme",
            "beyond_quote",
        ),
        (
            "Acme Enterprise costs $150 per seat",
            "Enterprise costs $150 per seat per month.",
            "Acme",
            "quote_not_in_source",
        ),
        ("Acme is cheap", "", "Acme", "no_quote"),
    ],
)
def test_unsupported(ledger, text, quote, subject, reason):
    v = check_claim(claim(text, quote, subject, led=ledger), ledger)
    assert not v.supported and v.reason == reason


@pytest.mark.parametrize(
    "page,text,quote,subject",
    [
        (
            "Acme Growth costs $199 per agent per month.",
            "Acme Growth costs $19 per agent",
            "Acme Growth costs $19",
            "Acme",
        ),  # a clipped number
        (
            "Acme does not support SSO on the Growth plan.",
            "Acme supports SSO on the Growth plan",
            "support SSO on the Growth plan",
            "Acme",
        ),  # a clipped negation
        (
            "Acme has 19 agents and costs $49 per month.",
            "Acme costs $19 per month",
            "Acme has 19 agents and costs $49 per month.",
            "Acme",
        ),  # a count read as a price
        (
            "Acme Starter costs $19 per month.",
            "Acme Starter costs $15 per month",
            "Acme Starter costs $19 per month.",
            "Acme 15",
        ),  # a figure hidden in the subject
        (
            "Acme Starter costs USD19 per month.",
            "Acme Starter costs USD15 per month",
            "Acme Starter costs USD19 per month.",
            "Acme",
        ),
        (
            "Acme Starter costs $19 per month.",
            "Acme Starter costs $19 per month",
            "Acme Starter costs $19 per month.",
            "",
        ),  # no subject
        (
            "Acme announced the purchase of Trello for $425 million.",
            "Acme bought Trello for $425",
            "Acme announced the purchase of Trello for $425",
            "Acme",
        ),  # a clipped scale
    ],
)
def test_bypasses_found_in_review_are_closed(page, text, quote, subject):
    led = Ledger()
    ev = led.add_text("https://acme.example/pricing", page, "Acme pricing")
    assert not check_claim(Claim("c", text, quote, ev.id, subject), led).supported


def test_a_date_without_a_time_zone_is_read_as_utc(ledger):
    led = Ledger()
    ev = led.add_text("https://acme.example/p", "Acme Starter costs $19 per month.", "Acme", fetched_at="2026-01-01")
    c = Claim("c", "Acme Starter costs $19 per month", "Acme Starter costs $19 per month.", ev.id, "Acme")
    assert check_claim(c, led, max_age_days=30, now=datetime(2026, 6, 1, tzinfo=timezone.utc)).stale


def test_unknown_page(ledger):
    assert check_claim(Claim("c", "Acme is big", "Acme is big and old", "nope", "Acme"), ledger).reason == "no_evidence"


def test_a_negation_about_something_else_is_not_a_mismatch(ledger):
    v = check_claim(
        claim(
            "Acme's free trial needs a credit card? No: no credit card is required for the trial",
            "No credit card is required for the free trial.",
            led=ledger,
        ),
        ledger,
    )
    assert v.supported


def test_number_in_the_product_name_is_a_name():
    led = Ledger()
    ev = led.add_text(
        "https://example.com/m365", "Microsoft 365 Business Basic costs $6 per user per month.", "Microsoft 365 plans"
    )
    v = check_claim(
        Claim(
            "c",
            "Microsoft 365 Business Basic costs $6 per user per month",
            "Business Basic costs $6 per user per month.",
            ev.id,
            "Microsoft 365",
        ),
        led,
    )
    assert v.supported


def test_stale_is_flagged_not_cut(ledger):
    c = claim("Acme Professional includes 5 seats", "The Professional plan includes 5 seats.", led=ledger)
    now = datetime(2026, 6, 1, tzinfo=timezone.utc)
    assert check_claim(c, ledger, max_age_days=30, now=now).stale
    assert check_claim(c, ledger, max_age_days=30, now=now).supported
    assert not check_claim(c, ledger, max_age_days=365, now=now).stale


def test_report_counts(ledger):
    r = check_claims(
        [
            claim("Acme Professional includes 5 seats", "The Professional plan includes 5 seats.", led=ledger),
            claim("Acme Professional includes 50 seats", "The Professional plan includes 5 seats.", led=ledger),
        ],
        ledger,
    )
    assert r.to_dict()["supported"] == 1 and r.by_reason == {"figure_not_in_quote": 1}


def test_ledger_round_trip(tmp_path, ledger):
    ledger.save(tmp_path / "l.json")
    again = Ledger.load(tmp_path / "l.json")
    assert list(again) == list(ledger) and again[next(iter(again))].sha256 == ledger[next(iter(ledger))].sha256
