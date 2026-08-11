from __future__ import annotations

from ssl import SSLContext

import pytest
from yarl import URL

from python_socks import ProxyConnectionError, ProxyError, ProxyTimeoutError, ProxyType
from tests.config import (
    HTTP_PROXY_URL,
    HTTPS_PROXY_URL,
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
)

trio = pytest.importorskip("trio")

from python_socks.async_.trio._resolver import Resolver
from python_socks.async_.trio.v2 import Proxy
from tests.patches import patch_trio_getaddrinfo


async def make_request(
    *,
    proxy: Proxy,
    url: str | URL,
    resolve_host: bool = False,
    timeout: float | None = None,
    ssl_context: SSLContext | None = None,
) -> int:
    with patch_trio_getaddrinfo():
        url = URL(url)

        assert url.host is not None

        dest_host = url.host
        if resolve_host:
            resolver = Resolver()
            _, dest_host = await resolver.resolve(url.host)

        dest_ssl = ssl_context if url.scheme == "https" else None

        stream = await proxy.connect(
            dest_host=dest_host,  # type:ignore[arg-type]
            dest_port=url.port,  # type:ignore[arg-type]
            dest_ssl=dest_ssl,
            timeout=timeout,
        )

        # fmt: off
        request = (
            "GET {rel_url} HTTP/1.1\r\n"
            "Host: {host}\r\n"
            "Connection: close\r\n\r\n"
        )
        # fmt: on

        request = request.format(rel_url=url.path_qs, host=url.host)
        request = request.encode("ascii")

        await stream.write(request)

        response = await stream.read(1024)

        status_line = response.split(b"\r\n", 1)[0]
        _version, status_code, *_reason = status_line.split()

        await stream.close()

        return int(status_code)


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize("rdns", (True, False))
@pytest.mark.parametrize("resolve_host", (True, False))
@pytest.mark.trio
async def test_socks5_proxy_ipv4(
    url: str,
    rdns: bool,
    resolve_host: bool,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_socks5_proxy_hostname_ipv4(
    url: str,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize("rdns", (None, True, False))
@pytest.mark.trio
async def test_socks5_proxy_ipv4_with_auth_none(
    url: str,
    rdns: bool,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.trio
async def test_socks5_proxy_with_invalid_credentials() -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + "aaa",
    )
    with pytest.raises(ProxyError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.trio
async def test_socks5_proxy_with_connect_timeout() -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyTimeoutError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4, timeout=0.0001)


@pytest.mark.trio
async def test_socks5_proxy_with_invalid_proxy_port(unused_tcp_port: int) -> None:
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=unused_tcp_port,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyConnectionError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
@pytest.mark.trio
async def test_socks5_proxy_ipv6(url: str, target_ssl_context: SSLContext) -> None:
    proxy = Proxy.from_url(SOCKS5_IPV6_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize("rdns", (None, True, False))
@pytest.mark.parametrize("resolve_host", (True, False))
@pytest.mark.trio
async def test_socks4_proxy(
    url: str,
    rdns: bool,
    resolve_host: bool,
    target_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_http_proxy(url: str, target_ssl_context: SSLContext) -> None:
    proxy = Proxy.from_url(HTTP_PROXY_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_secure_proxy(
    url: str,
    target_ssl_context: SSLContext,
    proxy_ssl_context: SSLContext,
) -> None:
    proxy = Proxy.from_url(HTTPS_PROXY_URL, proxy_ssl=proxy_ssl_context)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize("url", (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_proxy_chain(url: str, target_ssl_context: SSLContext) -> None:
    proxy_urls = [SOCKS5_IPV4_URL, SOCKS4_URL, HTTP_PROXY_URL]
    forward = None
    proxy = None
    for proxy_url in proxy_urls:
        proxy = Proxy.from_url(proxy_url, forward=forward)
        forward = proxy

    assert proxy is not None

    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200
