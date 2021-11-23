import socket
import ssl
from unittest import mock

import pytest
from yarl import URL

from python_socks import ProxyType, ProxyError, ProxyTimeoutError, ProxyConnectionError
from python_socks.sync import Proxy
from python_socks.sync import ProxyChain
from python_socks.sync._proxy import SyncProxy
from python_socks.sync._resolver import SyncResolver
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
    HTTP_PROXY_PORT,
    TEST_URL_IPV4,
    TEST_URL_IPv6,
    SOCKS5_IPV4_HOSTNAME_URL,
    TEST_HOST_PEM_FILE,
    TEST_URL_IPV4_HTTPS,
)
from tests.mocks import getaddrinfo_sync_mock


def read_status_code(sock: socket.socket) -> int:
    data = sock.recv(1024)
    status_line = data.split(b'\r\n', 1)[0]
    status_line = status_line.decode('utf-8', 'surrogateescape')
    version, status_code, *reason = status_line.split()
    return int(status_code)


def make_request(proxy: SyncProxy, url: str, resolve_host=False, timeout=None):
    with mock.patch('socket.getaddrinfo', new=getaddrinfo_sync_mock()):
        url = URL(url)

        dest_host = url.host
        if resolve_host:
            resolver = SyncResolver()
            _, dest_host = resolver.resolve(url.host)

        sock: socket.socket = proxy.connect(
            dest_host=dest_host, dest_port=url.port, timeout=timeout
        )

        if url.scheme == 'https':
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            ssl_context.load_verify_locations(TEST_HOST_PEM_FILE)

            sock = ssl_context.wrap_socket(sock=sock, server_hostname=url.host)

        request = 'GET {rel_url} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n\r\n'
        request = request.format(rel_url=url.path_qs, host=url.host)
        request = request.encode('ascii')
        sock.sendall(request)

        status_code = read_status_code(sock)
        sock.close()
        return status_code


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
def test_socks5_proxy_ipv4(url, rdns, resolve_host):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = make_request(proxy=proxy, url=url, resolve_host=resolve_host)
    assert status_code == 200


def test_socks5_proxy_hostname_ipv4():
    proxy = Proxy.from_url(SOCKS5_IPV4_HOSTNAME_URL)
    status_code = make_request(
        proxy=proxy,
        url=TEST_URL_IPV4,
    )
    assert status_code == 200


@pytest.mark.parametrize('rdns', (None, True, False))
def test_socks5_proxy_ipv4_with_auth_none(rdns):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL_WO_AUTH, rdns=rdns)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPV4)
    assert status_code == 200


def test_socks5_proxy_with_invalid_credentials():
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + 'aaa',
    )
    with pytest.raises(ProxyError):
        make_request(proxy=proxy, url=TEST_URL_IPV4)


def test_socks5_proxy_with_connect_timeout():
    proxy = Proxy.create(
        proxy_type=ProxyType.SOCKS5,
        host=PROXY_HOST_IPV4,
        port=SOCKS5_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD,
    )
    with pytest.raises(ProxyTimeoutError):
        make_request(proxy=proxy, url=TEST_URL_IPV4, timeout=0.001)


def test_socks5_proxy_with_invalid_proxy_port(unused_tcp_port):
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
def test_socks5_proxy_ipv6():
    proxy = Proxy.from_url(SOCKS5_IPV6_URL)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPV4)
    assert status_code == 200


@pytest.mark.skipif(SKIP_IPV6_TESTS, reason="TravisCI doesn't support ipv6")
@pytest.mark.parametrize('rdns', (True, False))
def test_socks5_proxy_hostname_ipv6(rdns):
    proxy = Proxy.from_url(SOCKS5_IPV4_URL, rdns=rdns)
    status_code = make_request(proxy=proxy, url=TEST_URL_IPv6)
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
@pytest.mark.parametrize('rdns', (None, True, False))
@pytest.mark.parametrize('resolve_host', (True, False))
def test_socks4_proxy(url, rdns, resolve_host):
    proxy = Proxy.from_url(SOCKS4_URL, rdns=rdns)
    status_code = make_request(proxy=proxy, url=url, resolve_host=resolve_host)
    assert status_code == 200


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_http_proxy(url):
    proxy = Proxy.from_url(HTTP_PROXY_URL)
    status_code = make_request(proxy=proxy, url=url)
    assert status_code == 200


def test_http_proxy_with_invalid_credentials():
    proxy = Proxy.create(
        proxy_type=ProxyType.HTTP,
        host=PROXY_HOST_IPV4,
        port=HTTP_PROXY_PORT,
        username=LOGIN,
        password=PASSWORD + 'aaa',
    )
    with pytest.raises(ProxyError):
        make_request(proxy=proxy, url=TEST_URL_IPV4)


@pytest.mark.parametrize('url', (TEST_URL_IPV4, TEST_URL_IPV4_HTTPS))
def test_proxy_chain(url):
    proxy = ProxyChain(
        [
            Proxy.from_url(SOCKS5_IPV4_URL),
            Proxy.from_url(SOCKS4_URL),
            Proxy.from_url(HTTP_PROXY_URL),
        ]
    )
    # noinspection PyTypeChecker
    status_code = make_request(proxy=proxy, url=TEST_URL_IPV4_HTTPS)
    assert status_code == 200
