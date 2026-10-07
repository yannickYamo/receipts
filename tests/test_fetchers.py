"""Other ways to get a page: a headless browser, Firecrawl, a file the user saved. The same checks, and a record of which."""

import json

import pytest

from receipts import Ledger
from receipts.cli import main
from receipts.fetch import FetchError, _allowed, fetch_firecrawl, fetch_page, fetch_rendered

TEXT = "Acme Starter costs $20 per seat per month. " * 8
HTML = f"<html><head><title>Acme pricing</title></head><body><p>{TEXT}</p><a href='/about'>About</a></body></html>"


@pytest.fixture
def public(monkeypatch):
    """Addresses resolve as public and robots.txt allows: the tests are about what happens after those checks."""
    monkeypatch.setattr("receipts.fetch.check_address", lambda url: None)
    monkeypatch.setattr("receipts.fetch.allowed_by_robots", lambda url, timeout=10: True)


# ── Firecrawl ───────────────────────────────────────────────────────────────────────────────────────


def firecrawl_says(markdown=TEXT, status=200, **more):
    return {
        "success": True,
        "data": {
            "markdown": markdown,
            "links": ["https://acme.example/about", 7],
            "metadata": {"title": "Acme pricing", "statusCode": status},
        },
    } | more


def test_firecrawl_is_asked_for_a_fresh_whole_page_and_its_text_is_what_it_returns(public):
    sent = []

    def post(url, headers, body, timeout):
        sent.append((url, headers, body))
        return firecrawl_says()

    title, text, links = fetch_firecrawl("https://acme.example/pricing", api_key="k", post=post)
    url, headers, body = sent[0]
    assert url == "https://api.firecrawl.dev/v2/scrape" and headers["Authorization"] == "Bearer k"
    assert body == {
        "url": "https://acme.example/pricing",
        "formats": ["markdown", "links"],
        "onlyMainContent": False,
        "maxAge": 0,
    }
    assert (title, text, links) == ("Acme pricing", TEXT.strip(), [("https://acme.example/about", "")])


def test_firecrawl_failures_are_fetch_errors_in_words(public, monkeypatch):
    for reply, why in (
        (firecrawl_says(status=403), "the site answered 403"),
        (firecrawl_says(markdown="short"), "almost no text"),
        ({"success": False, "error": "Payment required", "code": "insufficient_credits"}, "Payment required"),
        ({"data": None}, "returned no page"),
    ):
        with pytest.raises(FetchError, match=why):
            fetch_firecrawl("https://acme.example/pricing", api_key="k", post=lambda u, h, b, t, r=reply: r)
    monkeypatch.delenv("FIRECRAWL_API_KEY", raising=False)
    with pytest.raises(FetchError, match="FIRECRAWL_API_KEY"):
        fetch_firecrawl("https://acme.example/pricing")


def test_no_way_of_fetching_sends_a_private_address_anywhere_or_reads_past_a_refusal(monkeypatch):
    called = []
    post = lambda *a: called.append(a) or firecrawl_says()  # noqa: E731
    for url in ("http://127.0.0.1/admin", "http://169.254.169.254/latest/meta-data/", "file:///etc/passwd"):
        with pytest.raises(FetchError):
            fetch_firecrawl(url, api_key="k", post=post)
        with pytest.raises(FetchError):
            fetch_rendered(url, launch=lambda: pytest.fail("the browser must not start"))
    assert called == []  # the address was refused here, before anything was sent on
    monkeypatch.setattr("receipts.fetch.check_address", lambda url: None)
    monkeypatch.setattr("receipts.fetch.allowed_by_robots", lambda url, timeout=10: False)  # the site says no
    for fetch_it in (
        lambda: fetch_firecrawl("https://reviews.example/p", api_key="k", post=post),
        lambda: fetch_rendered("https://reviews.example/p", launch=lambda: pytest.fail("no")),
    ):
        with pytest.raises(FetchError, match="robots.txt does not allow it"):
            fetch_it()
    assert called == []
    with pytest.raises(FetchError, match="no such way"):
        fetch_page("https://acme.example/", "curl")


# ── The browser ─────────────────────────────────────────────────────────────────────────────────────


class FakeRoute:
    def __init__(self, browser, address, kind):
        self.browser, self.address = browser, address
        self.request = type("Request", (), {"url": address, "resource_type": kind})()

    def continue_(self):
        self.browser.sent.append(self.address)

    def abort(self):
        self.browser.aborted.append(self.address)


class FakeBrowser:
    """A stand-in for playwright: the page "requests" a list of addresses through the guard, then has content."""

    def __init__(self, requests, html=HTML, final="https://acme.example/pricing", redirects=()):
        self.requests, self.html, self.final, self.redirects = requests, html, final, redirects
        self.sent, self.aborted, self.closed = [], [], False
        self.chromium = self

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def launch(self):
        return self

    def new_context(self, **kw):
        self.context_options = kw
        return self

    def route(self, pattern, guard):
        self.guard = guard

    def on(self, event, watch):
        self.watch = watch

    def new_page(self):
        return self

    def goto(self, url, **kw):
        for address, kind in self.requests:
            route = FakeRoute(self, address, kind)
            self.watch(route.request)
            self.guard(route)
        for address in self.redirects:  # followed by the browser without passing the guard
            self.watch(FakeRoute(self, address, "document").request)

    def content(self):
        return self.html

    @property
    def url(self):
        return self.final

    def close(self):
        self.closed = True


def addresses(monkeypatch):
    def check(url):
        if "internal" in url or "127.0.0.1" in url or not url.startswith("http"):
            raise FetchError("the address is not on the public internet")

    monkeypatch.setattr("receipts.fetch.check_address", check)
    monkeypatch.setattr("receipts.fetch.allowed_by_robots", lambda url, timeout=10: True)


def test_the_browser_reads_the_page_after_its_scripts_ran_and_checks_every_request(monkeypatch):
    addresses(monkeypatch)
    browser = FakeBrowser(
        [
            ("https://acme.example/pricing", "document"),
            ("https://cdn.example/app.js", "script"),
            ("https://cdn.example/hero.png", "image"),
        ]
    )
    title, text, links = fetch_rendered("https://acme.example/pricing", launch=lambda: browser)
    assert (
        title == "Acme pricing"
        and "Acme Starter costs $20" in text
        and links == [("https://acme.example/about", "About")]
    )
    assert browser.sent == ["https://acme.example/pricing", "https://cdn.example/app.js"]
    assert browser.aborted == ["https://cdn.example/hero.png"] and browser.closed  # a page is read for its text
    assert (
        browser.context_options["service_workers"] == "block" and browser.context_options["accept_downloads"] is False
    )


def test_a_page_that_reaches_for_a_private_address_is_thrown_away(monkeypatch):
    addresses(monkeypatch)
    asks = FakeBrowser([("https://acme.example/pricing", "document"), ("http://127.0.0.1:8080/secrets", "fetch")])
    with pytest.raises(FetchError, match="not on the public internet"):
        fetch_rendered("https://acme.example/pricing", launch=lambda: asks)
    assert asks.sent == ["https://acme.example/pricing"] and asks.closed  # the request was never sent
    redirected = FakeBrowser(
        [("https://acme.example/pricing", "document")], redirects=["http://internal.example/admin"]
    )
    with pytest.raises(FetchError, match="not on the public internet"):
        fetch_rendered("https://acme.example/pricing", launch=lambda: redirected)
    landed = FakeBrowser([("https://acme.example/pricing", "document")], final="http://internal.example/")
    with pytest.raises(FetchError, match="not on the public internet"):
        fetch_rendered("https://acme.example/pricing", launch=lambda: landed)
    verdicts: dict[str, bool] = {}
    assert (
        _allowed("data:text/plain,hi", verdicts)
        and not _allowed("ftp://acme.example/x", verdicts)
        and not _allowed("http://[bad/", verdicts)
    )


def test_a_challenge_page_with_no_text_is_not_a_page(monkeypatch):
    addresses(monkeypatch)
    wall = FakeBrowser(
        [("https://reviews.example/p", "document")], html="<html><body>Checking your browser</body></html>"
    )
    with pytest.raises(FetchError, match="almost no text"):
        fetch_rendered("https://reviews.example/p", launch=lambda: wall)


# ── The ledger says how each page got here ──────────────────────────────────────────────────────────


def test_the_ledger_records_how_each_page_arrived_and_keeps_it_through_a_save(public, tmp_path, monkeypatch):
    monkeypatch.setattr("receipts.ledger.fetch", lambda url, **kw: ("Acme", TEXT))
    monkeypatch.setattr("receipts.ledger.fetch_page", lambda url, how, **kw: ("Acme", TEXT + how, []))
    led = Ledger()
    by_code = led.add_url("https://acme.example/a")
    by_browser = led.add_url("https://acme.example/b", via="browser")
    by_service = led.add_url("https://acme.example/c", via="firecrawl")
    by_hand = led.add_text("https://acme.example/d", TEXT + "saved", "Acme")
    led.save(tmp_path / "l.json")
    again = Ledger.load(tmp_path / "l.json")
    assert [again.via(e.id) for e in (by_code, by_browser, by_service, by_hand)] == [
        "code",
        "browser",
        "firecrawl",
        "supplied",
    ]
    assert again.how(by_browser.id) == "rendered by a headless browser, then read by code"
    assert again.how(by_hand.id) == "supplied by the user, not fetched"
    raw = json.loads((tmp_path / "l.json").read_text())
    for page in raw:
        del page["via"]  # a ledger written before this was recorded
    (tmp_path / "old.json").write_text(json.dumps(raw))
    assert Ledger.load(tmp_path / "old.json").how(by_code.id) == "not recorded"


def test_a_saved_page_is_added_as_supplied_and_can_be_checked_against(tmp_path, capsys):
    (tmp_path / "page.html").write_text(HTML)
    args = [
        "add",
        str(tmp_path / "page.html"),
        "--url",
        "https://reviews.example/acme",
        "--ledger",
        str(tmp_path / "l.json"),
    ]
    assert main(args) == 0 and "supplied by you, not fetched" in capsys.readouterr().out
    led = Ledger.load(tmp_path / "l.json")
    ev = next(iter(led.values()))
    assert ev.title == "Acme pricing" and led.via(ev.id) == "supplied" and "<p>" not in ev.text
    claim = {
        "id": "a",
        "text": "Acme Starter costs $20 per seat per month",
        "quote": "Acme Starter costs $20 per seat per month.",
        "evidence_id": ev.id,
        "subject": "Acme",
    }
    (tmp_path / "c.json").write_text(json.dumps([claim]))
    assert main(["check", str(tmp_path / "c.json"), "--ledger", str(tmp_path / "l.json"), "--code-only"]) == 0
    (tmp_path / "empty.html").write_text("<html><body>hi</body></html>")
    assert (
        main(["add", str(tmp_path / "empty.html"), "--url", "https://x.example/", "--ledger", str(tmp_path / "l.json")])
        == 2
    )


def test_a_card_shows_how_each_source_was_read(public, monkeypatch):
    from receipts.backends import ScriptedBackend
    from receipts.battlecard import build_card, render_html

    monkeypatch.setattr("receipts.ledger.fetch_page", lambda url, how, **kw: ("Acme pricing", TEXT, []))
    card = build_card(
        "Acme",
        "Globex",
        ScriptedBackend([{"facts": []}]),
        urls={"Acme": ["https://acme.example/pricing"]},
        fetcher="browser",
    )
    assert card.to_dict()["sources"][0]["via"] == "browser"
    assert "rendered by a headless browser, then read by code" in render_html(card)
