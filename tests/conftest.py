from contextlib import contextmanager
from unittest import mock

import pytest

from python_socks.async_.asyncio._resolver import Resolver as AsyncioResolver
from python_socks.sync._resolver import SyncResolver
from tests.config import (
    PROXY_HOST_IPV4,
    PROXY_HOST_IPV6,
    SOCKS5_PROXY_PORT,
    LOGIN,
    PASSWORD,
    SKIP_IPV6_TESTS,
    HTTP_PROXY_PORT,
    SOCKS4_PORT_NO_AUTH,
    SOCKS4_PROXY_PORT,
    SOCKS5_PROXY_PORT_NO_AUTH,
    TEST_PORT_IPV4,
    TEST_PORT_IPV6,
    TEST_HOST_IPV4,
    TEST_HOST_IPV6,
    TEST_PORT_IPV4_HTTPS,
    TEST_HOST_CERT_FILE,
    TEST_HOST_KEY_FILE,
    HTTPS_PROXY_PORT, PROXY_HOST_CERT_FILE, PROXY_HOST_KEY_FILE,
)
from tests.http_server import HttpServer, HttpServerConfig
from tests.mocks import sync_resolve_factory, async_resolve_factory
from tests.proxy_server import ProxyConfig, ProxyServer
from tests.utils import wait_until_connectable


@contextmanager
def nullcontext():
    yield None


# @pytest.fixture(scope='session', autouse=True)
# def patch_socket_getaddrinfo():
#     with mock.patch('socket.getaddrinfo', side_effect=getaddrinfo):
#         yield None


@pytest.fixture(scope='session', autouse=True)
def patch_resolvers():
    p1 = mock.patch.object(
        SyncResolver, attribute='resolve', new=sync_resolve_factory(SyncResolver)
    )

    p2 = mock.patch.object(
        AsyncioResolver, attribute='resolve', new=async_resolve_factory(AsyncioResolver)
    )

    try:
        # noinspection PyProtectedMember
        from python_socks.async_.trio._resolver import Resolver as TrioResolver
    except ImportError:
        p3 = nullcontext()
    else:
        p3 = mock.patch.object(
            TrioResolver, attribute='resolve', new=async_resolve_factory(TrioResolver)
        )

    try:
        # noinspection PyProtectedMember
        from python_socks.async_.curio._resolver import Resolver as CurioResolver
    except ImportError:
        p4 = nullcontext()
    else:
        p4 = mock.patch.object(
            CurioResolver, attribute='resolve', new=async_resolve_factory(CurioResolver)
        )

    try:
        from python_socks.async_.anyio._resolver import Resolver as AnyioResolver
    except ImportError:
        p5 = nullcontext()
    else:
        p5 = mock.patch.object(
            AnyioResolver, attribute='resolve', new=async_resolve_factory(AnyioResolver)
        )

    with p1, p2, p3, p4, p5:
        yield None


@pytest.fixture(scope='session', autouse=True)
def proxy_server():
    config = [
        ProxyConfig(
            proxy_type='http',
            host=PROXY_HOST_IPV4,
            port=HTTP_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
        ),
        ProxyConfig(
            proxy_type='socks4',
            host=PROXY_HOST_IPV4,
            port=SOCKS4_PROXY_PORT,
            username=LOGIN,
            password=None,
        ),
        ProxyConfig(
            proxy_type='socks4',
            host=PROXY_HOST_IPV4,
            port=SOCKS4_PORT_NO_AUTH,
            username=None,
            password=None,
        ),
        ProxyConfig(
            proxy_type='socks5',
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
        ),
        ProxyConfig(
            proxy_type='socks5',
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT_NO_AUTH,
            username=None,
            password=None,
        ),
        ProxyConfig(
            proxy_type='http',
            # host=PROXY_HOST_NAME_IPV4,
            host=PROXY_HOST_IPV4,
            port=HTTPS_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
            ssl_certfile=PROXY_HOST_CERT_FILE,
            ssl_keyfile=PROXY_HOST_KEY_FILE,
        ),
    ]

    if not SKIP_IPV6_TESTS:
        config.append(
            ProxyConfig(
                proxy_type='socks5',
                host=PROXY_HOST_IPV6,
                port=SOCKS5_PROXY_PORT,
                username=LOGIN,
                password=PASSWORD,
            ),
        )

    server = ProxyServer(config=config)
    server.start()
    for cfg in config:
        wait_until_connectable(host=cfg.host, port=cfg.port, timeout=10)

    yield None

    server.terminate()


@pytest.fixture(scope='session', autouse=True)
def web_server():
    config = [
        HttpServerConfig(
            host=TEST_HOST_IPV4,
            port=TEST_PORT_IPV4,
        ),
        HttpServerConfig(
            host=TEST_HOST_IPV4,
            port=TEST_PORT_IPV4_HTTPS,
            certfile=TEST_HOST_CERT_FILE,
            keyfile=TEST_HOST_KEY_FILE,
        ),
    ]

    if not SKIP_IPV6_TESTS:
        config.append(HttpServerConfig(host=TEST_HOST_IPV6, port=TEST_PORT_IPV6))

    server = HttpServer(config=config)
    server.start()
    for cfg in config:
        server.wait_until_connectable(host=cfg.host, port=cfg.port)

    yield None

    server.terminate()
