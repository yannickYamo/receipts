"""Properties of text.py, checked on generated pages. Every defect the audits found in the code check lived there."""

import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from receipts.text import carries, figures_in, norm, quote_context, quote_passage  # noqa: E402

WORDS = ["Acme", "plan", "costs", "agents", "includes", "Pro", "Starter", "storage", "billed", "annually", "users"]
word = st.sampled_from(WORDS)
price = st.integers(1, 9999).map(lambda n: f"${n}")
count = st.integers(2, 9999).map(str)
sentence = st.lists(st.one_of(word, word, price, count), min_size=3, max_size=9).map(lambda ws: " ".join(ws) + ".")
page = st.lists(sentence, min_size=1, max_size=8)


@settings(max_examples=200, deadline=None)
@given(page, st.data())
def test_a_whole_sentence_of_the_page_is_always_found_and_its_passage_holds_it(sentences, data):
    text = " ".join(sentences)
    quote = data.draw(st.sampled_from(sentences))
    passage = quote_passage(quote, text)
    assert passage is not None and norm(quote).rstrip(".") in passage
    before, between, after = quote_context(quote, text)
    assert between == "" and len(before) <= 400 and len(after) <= 400


@settings(max_examples=200, deadline=None)
@given(page, st.integers(1, 9999))
def test_a_price_that_is_not_on_the_page_is_never_found(sentences, n):
    text = " ".join(sentences)
    if f"${n}" not in text.replace(".", " ").split():
        assert quote_passage(f"${n}", text) is None
        assert (str(n), "$") not in figures_in(text)


@settings(max_examples=200, deadline=None)
@given(st.integers(1, 99999), st.sampled_from(["$", "€", "£"]))
def test_a_figure_keeps_its_value_and_its_kind(n, sign):
    money, plain = figures_in(f"It costs {sign}{n:,} a year"), figures_in(f"It has {n:,} agents")
    assert len(money) == 1 and money[0][1] == sign and money[0][0] == plain[0][0] and plain[0][1] == ""
    assert not carries(money[0], plain) and not carries(plain[0], money)  # money is not a count, either way
    other = "€" if sign == "$" else "$"
    assert not carries(money[0], figures_in(f"It costs {other}{n:,} a year"))


@settings(max_examples=200, deadline=None)
@given(st.integers(1, 999), st.integers(0, 9))
def test_a_number_is_not_found_inside_a_longer_one(n, digit):
    text = f"The plan costs ${n}{digit} per agent per month and nothing else."
    assert quote_passage(f"costs ${n}", text) is None
    assert quote_passage(f"costs ${n}{digit}", text) is not None
