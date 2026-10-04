import pytest

from receipts.fetch import FetchError, check_address, fetch


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/admin",
        "http://localhost:8000/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "http://[::1]/",
        "ftp://example.com/file",
        "file:///etc/passwd",
        "http://exa mple.com/",
        "http://example.com:port/",
        "http://[bad/",
    ],
)
def test_addresses_a_model_must_not_reach_are_refused(url):
    with pytest.raises(FetchError):
        check_address(url)
    with pytest.raises(FetchError):
        fetch(url, respect_robots=False)
