from __future__ import annotations

import socket
from ssl import SSLContext

import pytest
from yarl import URL

from python_socks import ProxyConnectionError, ProxyError, ProxyTimeoutError, ProxyType
from python_socks.sync import Proxy
from python_socks.sync._resolver import SyncResolver
from tests.config import (
    HTTP_PROXY_PORT,
    HTTP_PROXY_URL,
    LOGIN,
    PASSWORD,
    PROXY_HOST_IPV4,
    SKIP_IPV6_TESTS,
    SOCKS4_URL,
    SOCKS5_IPV4_HOSTNAME_URL,
    SOCKS5_IPV4_URL,
    SOCKS5_IPV4_URL_WO_AUTH,
    SOCKS5_IPV6_URL,
    SOCKS5_PROXY_PORT,
    TEST_URL_IPV4,
    TEST_URL_IPV4_HTTPS,
    TEST_URL_IPv6,
)
from tests.patches import patch_sync_getaddrinfo


def make_request(
    *,
    proxy: Proxy,
    url: str | URL,
    resolve_host: bool = False,
    timeout: float | None = None,
    ssl_context: SSLContext | None = None,
) -> int:
    with patch_sync_getaddrinfo():
        url = URL(url)

        assert url.host is not None

        dest_host = url.host
        if resolve_host:
            resolver = SyncResolver()
            _, dest_host = resolver.resolve(url.host)

        sock: socket.socket = proxy.connect(
            dest_host=dest_host,  # type:ignore[arg-type]
            dest_port=url.port,  # type:ignore[arg-type]
            timeout=timeout,
        )

        if url.scheme == "https":
            assert ssl_context is not None
            sock = ssl_context.wrap_socket(sock=sock, server_hostname=url.host)

        request = "GET {rel_url} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n"
        request = request.format(rel_url=url.path_qs, host=url.host)
        request = request.encode("ascii")
        sock.sendall(request)

        response = sock.recv(1024)

        status_line = response.split(b"\r\n", 1)[0]
        _version, status_code, *_reason = status_line.split()

        sock.close()
        return int(status_code)


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize("rdns", (True, False))
@pytest.mark.parametrize("resolve_host", (True, False))
def test_socks5_proxy_ipv4(
    url: str,
    rdns: bool,
    resolve_host: bool,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


def test_socks5_proxy_hostname_ipv4() -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
    status_code = make_request(
        proxy=proxy,
        url=TEST_URL_IPV4,
    )
    assert status_code == 200


@pytest.mark.parametrize("rdns", (None, True, False))
def test_socks5_proxy_ipv4_with_auth_none(rdns: bool) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPV4)
    assert status_code == 200


def test_socks5_proxy_with_invalid_credentials() -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + "aaa",
    )
    with pytest.raises(ProxyError):
        make_request(proxy=proxy, url=TEST_URL_IPV4)


def test_socks5_proxy_with_connect_timeout() -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyTimeoutError):
        make_request(proxy=proxy, url=TEST_URL_IPV4, timeout=0.001)


def test_socks5_proxy_with_invalid_proxy_port(unused_tcp_port: int) -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=unused_tcp_port,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyConnectionError):
        make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
def test_socks5_proxy_ipv6() -> None:
    proxy = Proxy.from_url(SOCKS5_IPV6_URL)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPV4)
    assert status_code == 200


@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
@pytest.mark.parametrize("rdns", (True, False))
def test_socks5_proxy_hostname_ipv6(rdns: bool) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPv6)
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize("rdns", (None, True, False))
@pytest.mark.parametrize("resolve_host", (True, False))
def test_socks4_proxy(
    url: str,
    rdns: bool,
    resolve_host: bool,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
    status_code = make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_http_proxy(url: str, target_ssl_context: SSLContext) -> None:
    proxy = Proxy.from_url(HTTP_PROXY_URL)
    status_code = make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


def test_http_proxy_with_invalid_credentials() -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.HTTP,
        host=PROXY_HOST_IPV4,
        port=HTTP_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + "aaa",
    )
    with pytest.raises(ProxyError):
        make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_proxy_chain(
    url: str,
    target_ssl_context: SSLContext,
) -> None:
    proxy1 = Proxy.from_url(SOCKS5_IPV4_URL)
    proxy2 = Proxy.from_url(SOCKS4_URL, forward=proxy1)
    proxy3 = Proxy.from_url(HTTP_PROXY_URL, forward=proxy2)

    status_code = make_request(
        proxy=proxy3,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200
