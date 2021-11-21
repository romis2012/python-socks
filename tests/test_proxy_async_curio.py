import ssl
from typing import Optional

import pytest

from yarl import URL

from python_socks import ProxyType, ProxyError, ProxyTimeoutError, ProxyConnectionError
from python_socks._abc import AsyncProxy
from python_socks.async_ import ProxyChain
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
    TEST_HOST_PEM_FILE,
    TEST_URL_IPV4_HTTPS,
)

curio = pytest.importorskip('curio')
import curio.io  # noqa: E402
import curio.ssl as curiossl  # noqa: E402
from python_socks.async_.curio._resolver import Resolver  # noqa: E402
from python_socks.async_.curio import Proxy  # noqa: E402


async def make_request(proxy: AsyncProxy, url: str, resolve_host=False, timeout=None):
    url = URL(url)

    dest_host = url.host
    if resolve_host:
        resolver = Resolver()
        _, dest_host = await resolver.resolve(url.host)

    sock: curio.io.Socket = await proxy.connect(
        dest_host=dest_host, dest_port=url.port, timeout=timeout
    )

    ssl_context: Optional[curiossl.CurioSSLContext] = None
    if url.scheme == 'https':
        _ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        _ssl_context.verify_mode = ssl.CERT_REQUIRED
        _ssl_context.load_verify_locations(TEST_HOST_PEM_FILE)
        ssl_context = curiossl.CurioSSLContext(_ssl_context)

    if ssl_context is not None:
        sock = await ssl_context.wrap_socket(
            sock, do_handshake_on_connect=False, server_hostname=url.host
        )

        await sock.do_handshake()

    stream = sock.as_stream()

    # fmt: off
    request = (
        'GET {rel_url} HTTP/1.1\r\n'
        'Host: {host}\r\n'
        'Connection: close\r\n\r\n'
    )
    # fmt: on

    request = request.format(rel_url=url.path_qs, host=url.host)
    request = request.encode('ascii')

    await stream.write(request)

    response = await stream.read(1024)

    status_line = response.split(b'\r\n', 1)[0]
    status_line = status_line.decode('utf-8', 'surrogateescape')
    version, status_code, *reason = status_line.split()

    return int(status_code)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
def test_socks5_proxy_ipv4(url, rdns, resolve_host):
    async def main():
        proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
        status_code = await make_request(proxy=proxy, url=url, resolve_host=resolve_host)
        assert status_code == 200

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_socks5_proxy_hostname_ipv4(url):
    async def main():
        proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
        status_code = await make_request(
            proxy=proxy,
            url=url,
        )
        assert status_code == 200

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
def test_socks5_proxy_ipv4_with_auth_none(url, rdns):
    async def main():
        proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
        status_code = await make_request(proxy=proxy, url=url)
        assert status_code == 200

    curio.run(main)


def test_socks5_proxy_with_invalid_credentials():
    async def main():
        proxy = Proxy.create(
            proxy_type=ProxyType.SOCKS5,
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD + 'aaa',
        )
        with pytest.raises(ProxyError):
            await make_request(proxy=proxy, url=TEST_URL_IPV4)

    curio.run(main)


def test_socks5_proxy_with_connect_timeout():
    async def main():
        proxy = Proxy.create(
            proxy_type=ProxyType.SOCKS5,
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
        )
        with pytest.raises(ProxyTimeoutError):
            await make_request(proxy=proxy, url=TEST_URL_IPV4, timeout=0.0001)

    curio.run(main)


def test_socks5_proxy_with_invalid_proxy_port(unused_tcp_port):
    async def main():
        proxy = Proxy.create(
            proxy_type=ProxyType.SOCKS5,
            host=PROXY_HOST_IPV4,
            port=unused_tcp_port,
            username=LOGIN,
            password=PASSWORD,
        )
        with pytest.raises(ProxyConnectionError):
            await make_request(proxy=proxy, url=TEST_URL_IPV4)

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
def test_socks5_proxy_ipv6(url):
    async def main():
        proxy = Proxy.from_url(SOCKS5_IPV6_URL)
        status_code = await make_request(proxy=proxy, url=url)
        assert status_code == 200

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
def test_socks4_proxy(url, rdns, resolve_host):
    async def main():
        proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
        status_code = await make_request(proxy=proxy, url=url, resolve_host=resolve_host)
        assert status_code == 200

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_http_proxy(url):
    async def main():
        proxy = Proxy.from_url(HTTP_PROXY_URL)
        status_code = await make_request(proxy=proxy, url=url)
        assert status_code == 200

    curio.run(main)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_proxy_chain(url):
    async def main():
        proxy = ProxyChain(
            [
                Proxy.from_url(SOCKS5_IPV4_URL),
                Proxy.from_url(SOCKS4_URL),
                Proxy.from_url(HTTP_PROXY_URL),
            ]
        )
        # noinspection PyTypeChecker
        status_code = await make_request(proxy=proxy, url=url)
        assert status_code == 200

    curio.run(main)
