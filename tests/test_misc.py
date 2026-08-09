import pytest

from python_socks._helpers import is_ip_address
from python_socks._protocols.http import BasicAuth, ConnectRequest


@pytest.mark.parametrize("address", ("::1", b"::1", "127.0.0.1", b"127.0.0.1"))
def test_is_ip_address(address: str) -> None:
    assert is_ip_address(address)


def test_basic_auth() -> None:
    login = "login"
    password = "password"  # noqa: S105

    auth1 = BasicAuth(login=login, password=password)
    auth2 = BasicAuth.decode(auth1.encode())

    assert auth2.login == login
    assert auth2.password == password


def test_connect_request_brackets_ipv6_host() -> None:
    """RFC 7230 § 5.4: literal IPv6 in host:port MUST be bracketed."""
    req = ConnectRequest(
        host="2001:db8::1",
        port=443,
        username=None,
        password=None,
    )
    raw = req.dumps()
    first_line = raw.split(b"\r\n", 1)[0]
    assert first_line == b"CONNECT [2001:db8::1]:443 HTTP/1.1"
    assert b"Host: [2001:db8::1]:443\r\n" in raw


def test_connect_request_does_not_bracket_ipv4_host() -> None:
    req = ConnectRequest(
        host="192.0.2.1",
        port=443,
        username=None,
        password=None,
    )
    raw = req.dumps()
    assert raw.split(b"\r\n", 1)[0] == b"CONNECT 192.0.2.1:443 HTTP/1.1"
    assert b"Host: 192.0.2.1:443\r\n" in raw


def test_connect_request_does_not_bracket_hostname() -> None:
    req = ConnectRequest(
        host="example.com",
        port=443,
        username=None,
        password=None,
    )
    raw = req.dumps()
    assert raw.split(b"\r\n", 1)[0] == b"CONNECT example.com:443 HTTP/1.1"
    assert b"Host: example.com:443\r\n" in raw
