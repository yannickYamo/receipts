"""Fetching a page. Code does this, never a model: the text in the ledger is what the site served.

The addresses come from a model, so the fetcher treats them as hostile: only http and https, only
hosts on the public internet (no localhost, no private or link-local ranges, checked again on every
redirect), a size cap, one overall deadline, and every failure comes back as a FetchError.

The connection goes to the address that was checked. The host name is looked up once, every address
it gives is checked, and the socket is opened to one of those: a name that answers "public" to a
check and "127.0.0.1" to the connection a moment later gets no second lookup to answer. Proxies from
the environment are not used, since a proxy would do its own lookup.
"""

from __future__ import annotations

import http.client
import ipaddress
import socket
import ssl
import time
import urllib.error
import urllib.request
import urllib.robotparser
from urllib.parse import urlsplit

from .text import html_to_text

USER_AGENT = "claim-receipts/0.1 (evidence fetcher; one request per page)"
MAX_BYTES = 3_000_000


class FetchError(Exception):
    """A page that could not be read, with the reason a person would act on."""


_NAT64 = ipaddress.ip_network("64:ff9b::/96")


def _is_public(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Is this an address on the public internet? An IPv4 address carried inside an IPv6 one is unwrapped first."""
    if ip.version == 6:
        inner = ip.ipv4_mapped or (
            ipaddress.IPv4Address(int(ip) & 0xFFFFFFFF) if ip in _NAT64 or int(ip) >> 32 == 0 else None
        )
        if inner is not None:
            return _is_public(inner)
    return ip.is_global and not ip.is_multicast


def check_address(url: str) -> None:
    """Raise FetchError unless `url` is an http(s) address of a host on the public internet."""
    try:
        parts = urlsplit(url)
        host, _ = parts.hostname, parts.port  # .port raises on a malformed port
    except ValueError as e:
        raise FetchError("not a valid address") from e
    if parts.scheme not in ("http", "https") or not host or any(c.isspace() for c in url):
        raise FetchError("not an http(s) address")
    try:
        found = socket.getaddrinfo(host, None)
    except (socket.gaierror, UnicodeError) as e:
        raise FetchError("the host does not resolve") from e
    for info in found:
        if not _is_public(ipaddress.ip_address(info[4][0].split("%")[0])):
            raise FetchError("the address is not on the public internet")


def _connect_checked(host: str, port: int, timeout: float | None) -> socket.socket:
    """A socket to `host`, opened to an address that was checked. One lookup: what is checked is what is dialled."""
    try:
        found = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (socket.gaierror, UnicodeError) as e:
        raise FetchError("the host does not resolve") from e
    if not found or not all(_is_public(ipaddress.ip_address(info[4][0].split("%")[0])) for info in found):
        raise FetchError("the address is not on the public internet")
    last: OSError | None = None
    for family, kind, proto, _, address in found:
        sock = socket.socket(family, kind, proto)
        try:
            sock.settimeout(timeout)
            sock.connect(address)  # an address, never the name
            return sock
        except OSError as e:
            sock.close()
            last = e
    raise last or OSError("no address to connect to")


class _CheckedHTTP(http.client.HTTPConnection):
    def connect(self):
        self.sock = _connect_checked(self.host, self.port, self.timeout)


class _CheckedHTTPS(http.client.HTTPSConnection):
    def connect(self):
        plain = _connect_checked(self.host, self.port, self.timeout)
        self.sock = _TLS.wrap_socket(plain, server_hostname=self.host)  # the certificate is still the name's


_TLS = ssl.create_default_context()


class _CheckedHTTPHandler(urllib.request.HTTPHandler):
    def http_open(self, req):
        return self.do_open(_CheckedHTTP, req)


class _CheckedHTTPSHandler(urllib.request.HTTPSHandler):
    def https_open(self, req):
        return self.do_open(_CheckedHTTPS, req)


class _CheckedRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        check_address(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


# No proxy from the environment: a proxy looks the name up itself, past the check.
_opener = urllib.request.build_opener(
    urllib.request.ProxyHandler({}), _CheckedHTTPHandler, _CheckedHTTPSHandler, _CheckedRedirects
)


def allowed_by_robots(url: str, timeout: float = 10) -> bool:
    """Does the site's robots.txt allow this fetch? A site that guards its robots.txt (401, 403) is read as "no"."""
    parts = urlsplit(url)
    rp = urllib.robotparser.RobotFileParser()
    try:
        req = urllib.request.Request(f"{parts.scheme}://{parts.netloc}/robots.txt", headers={"User-Agent": USER_AGENT})
        with _opener.open(req, timeout=timeout) as r:
            rp.parse(r.read(200_000).decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        return e.code not in (401, 403)
    except Exception:
        return True  # no robots.txt to read: nothing forbids the fetch
    return rp.can_fetch(USER_AGENT, url)


def _read_body(response, deadline: float) -> bytes:
    """The response body, up to MAX_BYTES and before `deadline`. Raises FetchError past either."""
    chunks: list[bytes] = []
    size = 0
    while chunk := response.read1(65_536):  # read1 returns after one packet, so the deadline is checked often
        size += len(chunk)
        if size > MAX_BYTES:
            raise FetchError("the page is larger than 3 MB")
        if time.monotonic() > deadline:
            raise FetchError("the page took too long to arrive")
        chunks.append(chunk)
    return b"".join(chunks)


def _decode(raw: bytes, charset: str) -> str:
    try:
        return raw.decode(charset, "replace")
    except LookupError:  # a charset the site made up
        return raw.decode("utf-8", "replace")


def fetch(url: str, *, timeout: float = 20, respect_robots: bool = True) -> tuple[str, str]:
    """(title, text) of the page at `url`. Raises FetchError when it cannot be read as text."""
    check_address(url)
    if respect_robots and not allowed_by_robots(url):
        raise FetchError("the site's robots.txt does not allow it")
    deadline = time.monotonic() + 2 * timeout
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain;q=0.9"})
        with _opener.open(req, timeout=timeout) as r:
            kind = r.headers.get_content_type()
            if kind not in ("text/html", "text/plain", "application/xhtml+xml"):
                raise FetchError(f"not a text page ({kind})")
            body = _decode(_read_body(r, deadline), r.headers.get_content_charset() or "utf-8")
    except urllib.error.HTTPError as e:
        raise FetchError(f"the site answered {e.code}") from e
    except (urllib.error.URLError, http.client.HTTPException, TimeoutError, OSError, ValueError) as e:
        raise FetchError(f"could not connect ({getattr(e, 'reason', e)})") from e
    title, text = html_to_text(body) if kind != "text/plain" else ("", body.strip())
    if len(text) < 200:
        raise FetchError("the page has almost no text without JavaScript")
    return title, text
