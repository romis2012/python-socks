import socket
import ssl
import trio  # noqa

import pytest  # noqa
from yarl import URL  # noqa

from python_socks import (
    ProxyType,
    ProxyError,
    ProxyTimeoutError,
    ProxyConnectionError
)

from python_socks._proxy_async import AsyncProxy  # noqa
from python_socks.async_.trio import Proxy
from python_socks.async_ import ProxyChain
# noinspection PyUnresolvedReferences,PyProtectedMember
from python_socks._resolver_async_trio import Resolver

from tests.config import (
    PROXY_HOST_IPV4, SOCKS5_PROXY_PORT, LOGIN, PASSWORD, SKIP_IPV6_TESTS,
    SOCKS5_IPV4_URL, SOCKS5_IPV4_URL_WO_AUTH, SOCKS5_IPV6_URL, SOCKS4_URL,
    HTTP_PROXY_URL, TEST_URL_IPV4, SOCKS5_IPV4_HOSTNAME_URL,
    TEST_HOST_PEM_FILE, TEST_URL_IPV4_HTTPS
)


async def make_request(proxy: AsyncProxy,
                       url: str, resolve_host=False, timeout=None):
    url = URL(url)

    dest_host = url.host
    if resolve_host:
        resolver = Resolver()
        _, dest_host = await resolver.resolve(url.host)

    sock: socket.socket = await proxy.connect(
        dest_host=dest_host,
        dest_port=url.port,
        timeout=timeout
    )

    ssl_context = None
    if url.scheme == 'https':
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        ssl_context.verify_mode = ssl.CERT_REQUIRED
        ssl_context.load_verify_locations(TEST_HOST_PEM_FILE)

    stream = trio.SocketStream(sock)

    if ssl_context is not None:
        stream = trio.SSLStream(
            stream, ssl_context,
            server_hostname=url.host
        )
        await stream.do_handshake()

    request = (
        'GET {rel_url} HTTP/1.1\r\n'
        'Host: {host}\r\n'
        'Connection: close\r\n\r\n'
    )
    request = request.format(rel_url=url.path_qs, host=url.host)
    request = request.encode('ascii')

    await stream.send_all(request)

    response = await stream.receive_some(1024)

    status_line = response.split(b'\r\n', 1)[0]
    status_line = status_line.decode('utf-8', 'surrogateescape')
    version, status_code, *reason = status_line.split()

    return int(status_code)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
@pytest.mark.trio
async def test_socks5_proxy_ipv4(url, rdns, resolve_host):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_socks5_proxy_hostname_ipv4(url):
    proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
    status_code = await make_request(proxy=proxy, url=url, )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.trio
async def test_socks5_proxy_ipv4_with_auth_none(url, rdns):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
    status_code = await make_request(proxy=proxy, url=url)
    assert status_code == 200


@pytest.mark.trio
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


@pytest.mark.trio
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


@pytest.mark.trio
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
@pytest.mark.trio
async def test_socks5_proxy_ipv6(url):
    proxy = Proxy.from_url(SOCKS5_IPV6_URL)
    status_code = await make_request(proxy=proxy, url=url)
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
@pytest.mark.trio
async def test_socks4_proxy(url, rdns, resolve_host):
    proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
    status_code = await make_request(
        proxy=proxy,
        url=url,
        resolve_host=resolve_host
    )
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_http_proxy(url):
    proxy = Proxy.from_url(HTTP_PROXY_URL)
    status_code = await make_request(proxy=proxy, url=url)
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.trio
async def test_proxy_chain(url):
    proxy = ProxyChain([
        Proxy.from_url(SOCKS5_IPV4_URL),
        Proxy.from_url(SOCKS4_URL),
        Proxy.from_url(HTTP_PROXY_URL),
    ])
    # noinspection PyTypeChecker
    status_code = await make_request(proxy=proxy, url=url)
    assert status_code == 200
