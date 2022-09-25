import asyncio
import socket

import pytest  # noqa
from yarl import URL  # noqa

from python_socks import ProxyType, ProxyError, ProxyTimeoutError, ProxyConnectionError
from python_socks._abc import AsyncProxy
from python_socks.async_ import ProxyChain
from python_socks.async_.asyncio import Proxy
from python_socks.async_.asyncio._resolver import Resolver
from tests.config import (
    PROXY_HOST_IPV4,
    SOCKS5_PROXY_PORT,
    LOGIN,
    PASSWORD,
    SKIP_IPV6_TESTS,
    SOCKS5_IPV4_URL,
    SOCKS5_IPV4_URL_WO_AUTH,
    SOCKS5_IPV6_URL,
    SOCKS4_URL,
    HTTP_PROXY_URL,
    TEST_URL_IPV4,
    SOCKS5_IPV4_HOSTNAME_URL,
    TEST_URL_IPV4_HTTPS,
)


async def make_request(
    proxy: AsyncProxy,
    url: str,
    resolve_host=False,
    timeout=None,
    ssl_context=None,
):
    loop = asyncio.get_event_loop()

    url = URL(url)

    dest_host = url.host
    if resolve_host:
        resolver = Resolver(loop=loop)
        _, dest_host = await resolver.resolve(url.host)

    sock: socket.socket = await proxy.connect(
        dest_host=dest_host, dest_port=url.port, timeout=timeout
    )

    if url.scheme == 'https':
        dest_ssl = ssl_context
    else:
        dest_ssl = None

    # noinspection PyTypeChecker
    reader, writer = await asyncio.open_connection(
        host=None,
        port=None,
        sock=sock,
        ssl=dest_ssl,
        server_hostname=url.host if dest_ssl else None,
    )

    request = 'GET {rel_url} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'
    request = request.format(rel_url=url.path_qs, host=url.host)
    request = request.encode('ascii')

    writer.write(request)

    status_line = await reader.readline()
    version, status_code, *reason = status_line.split()

    writer.transport.close()

    return int(status_code)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
@pytest.mark.asyncio
async def test_socks5_proxy_ipv4(url, rdns, resolve_host, target_ssl_context):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.asyncio
async def test_socks5_proxy_hostname_ipv4(url, target_ssl_context):
    proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.asyncio
async def test_socks5_proxy_ipv4_with_auth_none(url, rdns, target_ssl_context):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.asyncio
async def test_socks5_proxy_with_invalid_credentials():
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + 'aaa',
    )
    with pytest.raises(ProxyError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.asyncio
async def test_socks5_proxy_with_connect_timeout():
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyTimeoutError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4, timeout=0.0001)


@pytest.mark.asyncio
async def test_socks5_proxy_with_invalid_proxy_port(unused_tcp_port):
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=unused_tcp_port,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyConnectionError):
        await make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
@pytest.mark.asyncio
async def test_socks5_proxy_ipv6(url, target_ssl_context):
    proxy = Proxy.from_url(SOCKS5_IPV6_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
@pytest.mark.asyncio
async def test_socks4_proxy(url, rdns, resolve_host, target_ssl_context):
    proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.asyncio
async def test_http_proxy(url, target_ssl_context):
    proxy = Proxy.from_url(HTTP_PROXY_URL)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.asyncio
async def test_proxy_chain(url, target_ssl_context):
    proxy = ProxyChain(
        [
            Proxy.from_url(SOCKS5_IPV4_URL),
            Proxy.from_url(SOCKS4_URL),
            Proxy.from_url(HTTP_PROXY_URL),
        ]
    )
    # noinspection PyTypeChecker
    status_code = await make_request(
        proxy=proxy,
        url=url,
        ssl_context=target_ssl_context,
    )
    assert status_code == 200
