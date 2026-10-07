from receipts.text import content_words, figures_in, html_to_text, norm, numbers_in, quote_match, quote_passage


def test_numbers_are_values_not_spellings():
    assert numbers_in("$1.5M") == numbers_in("1,500,000") == numbers_in("1.5 million") == ["1500000"]
    assert numbers_in("twenty-five seats") == ["25"]
    assert numbers_in("two hundred and fifty") == ["250"]
    assert numbers_in("10k users") == ["10000"]


def test_a_digit_glued_to_a_letter_is_a_name():
    assert numbers_in("G2 rated it in Q3") == []


def test_idioms_are_not_figures():
    assert numbers_in("no one asked, and a hundred reasons why") == []


def test_money_and_shares_keep_their_kind():
    assert figures_in("USD15 and .5% and 19 dollars") == [("15", "$"), ("0.5", "%"), ("19", "$")]
    assert figures_in("5m of cable") == [("5", "")] and figures_in("$5M") == [("5000000", "$")]


def test_a_figure_is_whole():
    assert "25" not in numbers_in("250 customers")


def test_quote_exact_ignores_case_spacing_and_quote_style():
    src = "HubSpot  was founded in 2006.\nIt’s based in Cambridge, Massachusetts."
    assert quote_match("hubspot was founded in 2006.", src) == "exact"
    assert quote_match("It's based in Cambridge", src) == "exact"


def test_a_quote_is_whole_words_and_whole_numbers():
    assert quote_match("The Growth plan costs $19", "The Growth plan costs $199 per agent per month") is None
    assert quote_match("serves 1,000", "Acme serves 10,000 customers") is None
    assert quote_match("supported on the Growth plan", "SSO is unsupported on the Growth plan") is None
    assert quote_match("costs $19", "It costs $19.99 a month") is None
    assert quote_match("costs $19", "It costs $19. Cancel any time.") == "exact"


def test_a_reworded_quote_is_not_on_the_page():
    assert (
        quote_match(
            "Freshdesk does offer a free plan for unlimited agents",
            "Freshdesk does not offer a free plan for unlimited agents",
        )
        is None
    )
    assert quote_match("Base acquired Zendesk for $50 million", "Base was acquired by Zendesk for $50 million") is None


def test_passage_is_the_whole_sentence_the_quote_was_cut_from():
    page = (
        "Acme has no free plan. In 2021 Zoom announced plans to acquire Five9 for $14.7 billion. The deal was rejected."
    )
    assert (
        quote_passage("acquire Five9 for $14.7 billion", page)
        == "in 2021 zoom announced plans to acquire five9 for $14.7 billion."
    )
    assert "not" in quote_passage("support SSO on the Growth plan", "Acme does not support SSO on the Growth plan.")
    assert (
        quote_passage("Starter\n$19 per seat", "Plans\nStarter\n$19 per seat\nPro\n$49 per seat")
        == "starter $19 per seat"
    )


def test_ellipsis_joins_table_lines_not_prose():
    table = "Pro\nBest for growing teams\n$49 /agent/month billed annually"
    assert quote_match("Pro ... $49 /agent/month", table) == "exact"
    assert quote_match("Pro ... $4", table) is None
    prose = "Freshdesk competes with Zendesk. Zendesk was fined by regulators in 2020 for data breaches."
    assert quote_match("Freshdesk ... was fined by regulators ... for data breaches", prose) is None
    far = "Pro\n" + "Another line\n" * 20 + "$89 /agent/month"
    assert quote_match("Pro ... $89 /agent/month", far) is None


def test_invented_quote_is_not_found():
    assert quote_match("Customers rate it 4.8 out of 5 on average", "A page about pricing and plans for teams.") is None


def test_stems_meet():
    assert content_words("prices priced pricing") == ["pric"] * 3
    assert norm("1,000 “users”") == '1000 "users"'


def test_html_to_text_drops_scripts_and_keeps_title():
    title, text = html_to_text(
        "<html><head><title>Pricing | Acme</title><style>p{}</style></head>"
        "<body><script>var x=1</script><h1>Plans</h1><p>Starter is $9.</p></body></html>"
    )
    assert title == "Pricing | Acme"
    assert "var x" not in text and "Starter is $9." in text and "Plans" in text


def test_html_title_ignores_svg_and_a_missing_head_close():
    title, text = html_to_text(
        "<html><head><title>Acme</title><body><svg><title>Globex logo</title></svg><p>Hello there.</p></body></html>"
    )
    assert title == "Acme" and text == "Hello there."


# ── A table row is one line, and a value carries the header of its column ───────────────────────────

TABLE = """<html><head><title>Acme pricing</title></head><body><h1>Plans</h1>
<table><thead><tr><th></th><th><div>Free</div><div>$0</div><a>Start</a></th><th>Pro<br>$49 /month</th></tr></thead>
<tbody><tr><th scope=row>File uploads</th><td>10MB</td><td>Unlimited</td></tr>
<tr><td>SSO</td><td></td><td><svg aria-label="yes"><path/></svg>Included</td></tr>
<tr><td colspan=3>All plans include support</td></tr></tbody></table>
<p>After the table.</p>
<div role="table"><div role="row"><span role="columnheader">Plan</span><span role="columnheader">Seats</span></div>
<div role="row"><span role="cell">Team</span><span role="cell">25 <b>seats</b></span></div></div>
<table><tr><td>Starter</td><td>$19</td></tr><tr><td>Growth</td><td>$29</td></tr></table>
<p>Unclosed <b>bold<p>next para</p><br/></body></html>"""


def test_a_table_row_is_one_line_and_each_value_carries_its_column():
    from receipts.text import html_to_text

    title, text = html_to_text(TABLE)
    lines = [x for x in text.split("\n") if x]
    assert title == "Acme pricing"
    assert "Free $0 Start | Pro $49 /month" in lines  # the header row, whole
    assert "File uploads | Free: 10MB | Pro: Unlimited" in lines  # a header is named by its first line
    assert "SSO | Pro: Included" in lines  # an empty cell says nothing, and so is left out
    assert "All plans include support" in lines  # a row that does not line up is written plainly
    assert "Team | Seats: 25 seats" in lines  # a table made of divs that names its parts
    assert "Starter | $19" in lines and "Growth | $29" in lines  # no header marked: none is guessed
    assert lines[-2:] == ["Unclosed bold", "next para"]  # tags left open do not lose the text


def test_a_value_quoted_from_a_row_is_checked_against_the_whole_row():
    from receipts import Claim, Ledger, check_claim
    from receipts.text import html_to_text, quote_passage

    _, text = html_to_text(TABLE + "<p>" + "Acme is a file service for small teams. " * 6 + "</p>")
    led = Ledger()
    ev = led.add_text("https://acme.example/pricing", text, "Acme pricing")
    assert (
        quote_passage("Pro: Unlimited", text) == "file uploads | free: 10mb | pro: unlimited"
    )  # the reader sees the row

    def decide(claim, quote):
        return check_claim(Claim("a", claim, quote, ev.id, "Acme"), led)

    assert decide("Acme Free allows file uploads of 10MB", "File uploads | Free: 10MB").supported
    assert decide("Acme Free allows file uploads of 20MB", "File uploads | Free: 10MB").reason == "figure_not_in_quote"
    assert decide("Acme Pro allows file uploads of 10MB", "File uploads | Pro: 10MB").reason == "quote_not_in_source"
    assert decide("Acme Pro costs $49 a month", "Pro $49 /month").supported
