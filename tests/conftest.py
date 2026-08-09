import ssl
from collections.abc import Generator, Iterator
from contextlib import contextmanager
from unittest import mock

import pytest
import trustme

from python_socks.async_.asyncio._resolver import Resolver as AsyncioResolver
from python_socks.sync._resolver import SyncResolver
from tests.config import (
    HTTP_PROXY_PORT,
    HTTPS_PROXY_PORT,
    LOGIN,
    PASSWORD,
    PROXY_HOST_IPV4,
    PROXY_HOST_IPV6,
    PROXY_HOST_NAME_IPV4,
    PROXY_HOST_NAME_IPV6,
    SKIP_IPV6_TESTS,
    SOCKS4_PORT_NO_AUTH,
    SOCKS4_PROXY_PORT,
    SOCKS5_PROXY_PORT,
    SOCKS5_PROXY_PORT_NO_AUTH,
    TEST_HOST_IPV4,
    TEST_HOST_IPV6,
    TEST_HOST_NAME_IPV4,
    TEST_HOST_NAME_IPV6,
    TEST_PORT_IPV4,
    TEST_PORT_IPV4_HTTPS,
    TEST_PORT_IPV6,
)
from tests.http_server import HttpServer, HttpServerConfig
from tests.mocks import async_resolve_factory, sync_resolve_factory
from tests.proxy_server import ProxyConfig, ProxyServer
from tests.utils import wait_until_connectable


@contextmanager
def nullcontext() -> Generator[None, None, None]:
    yield None


@pytest.fixture(scope="session")
def target_ssl_ca() -> trustme.CA:
    return trustme.CA()


@pytest.fixture(scope="session")
def target_ssl_cert(target_ssl_ca: trustme.CA) -> trustme.LeafCert:
    return target_ssl_ca.issue_cert(
        "localhost",
        TEST_HOST_IPV4,
        TEST_HOST_IPV6,
        TEST_HOST_NAME_IPV4,
        TEST_HOST_NAME_IPV6,
    )


@pytest.fixture(scope="session")
def target_ssl_certfile(target_ssl_cert: trustme.LeafCert) -> Iterator[str]:
    with target_ssl_cert.cert_chain_pems[0].tempfile() as cert_path:
        yield cert_path


@pytest.fixture(scope="session")
def target_ssl_keyfile(target_ssl_cert: trustme.LeafCert) -> Iterator[str]:
    with target_ssl_cert.private_key_pem.tempfile() as private_key_path:
        yield private_key_path


@pytest.fixture(scope="session")
def target_ssl_context(target_ssl_ca: trustme.CA) -> ssl.SSLContext:
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    ssl_ctx.check_hostname = True
    target_ssl_ca.configure_trust(ssl_ctx)
    return ssl_ctx


@pytest.fixture(scope="session")
def proxy_ssl_ca() -> trustme.CA:
    return trustme.CA()


@pytest.fixture(scope="session")
def proxy_ssl_cert(proxy_ssl_ca: trustme.CA) -> trustme.LeafCert:
    return proxy_ssl_ca.issue_cert(
        "localhost",
        PROXY_HOST_IPV4,
        PROXY_HOST_IPV6,
        PROXY_HOST_NAME_IPV4,
        PROXY_HOST_NAME_IPV6,
    )


@pytest.fixture(scope="session")
def proxy_ssl_context(proxy_ssl_ca: trustme.CA) -> ssl.SSLContext:
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ssl_ctx.verify_mode = ssl.CERT_REQUIRED
    ssl_ctx.check_hostname = True
    proxy_ssl_ca.configure_trust(ssl_ctx)
    return ssl_ctx


@pytest.fixture(scope="session")
def proxy_server_ssl_context(proxy_ssl_cert: trustme.LeafCert) -> ssl.SSLContext:
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    proxy_ssl_cert.configure_cert(ssl_ctx)
    return ssl_ctx


@pytest.fixture(scope="session")
def proxy_ssl_certfile(proxy_ssl_cert: trustme.LeafCert) -> Iterator[str]:
    with proxy_ssl_cert.cert_chain_pems[0].tempfile() as cert_path:
        yield cert_path


@pytest.fixture(scope="session")
def proxy_ssl_keyfile(proxy_ssl_cert: trustme.LeafCert) -> Iterator[str]:
    with proxy_ssl_cert.private_key_pem.tempfile() as private_key_path:
        yield private_key_path


@pytest.fixture(scope="session", autouse=True)
def patch_resolvers() -> Iterator[None]:
    p1 = mock.patch.object(
        SyncResolver,
        attribute="resolve",
        new=sync_resolve_factory(SyncResolver),
    )

    p2 = mock.patch.object(
        AsyncioResolver,
        attribute="resolve",
        new=async_resolve_factory(AsyncioResolver),
    )

    try:
        from python_socks.async_.trio._resolver import (
            Resolver as TrioResolver,
        )
    except ImportError:
        p3 = nullcontext()
    else:
        p3 = mock.patch.object(  # type:ignore[assignment]
            TrioResolver,
            attribute="resolve",
            new=async_resolve_factory(TrioResolver),
        )

    try:
        from python_socks.async_.anyio._resolver import (
            Resolver as AnyioResolver,
        )
    except ImportError:
        p5 = nullcontext()
    else:
        p5 = mock.patch.object(  # type:ignore[assignment]
            AnyioResolver,
            attribute="resolve",
            new=async_resolve_factory(AnyioResolver),
        )

    with p1, p2, p3, p5:
        yield None


@pytest.fixture(scope="session", autouse=True)
def proxy_server2(proxy_server_ssl_context: ssl.SSLContext) -> Iterator[None]:
    config = [
        ProxyConfig(
            proxy_type="http",
            host=PROXY_HOST_IPV4,
            port=HTTP_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
        ),
        ProxyConfig(
            proxy_type="socks4",
            host=PROXY_HOST_IPV4,
            port=SOCKS4_PROXY_PORT,
            username=LOGIN,
            password=None,
        ),
        ProxyConfig(
            proxy_type="socks4",
            host=PROXY_HOST_IPV4,
            port=SOCKS4_PORT_NO_AUTH,
            username=None,
            password=None,
        ),
        ProxyConfig(
            proxy_type="socks5",
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
        ),
        ProxyConfig(
            proxy_type="socks5",
            host=PROXY_HOST_IPV4,
            port=SOCKS5_PROXY_PORT_NO_AUTH,
            username=None,
            password=None,
        ),
        ProxyConfig(
            proxy_type="http",
            host=PROXY_HOST_IPV4,
            port=HTTPS_PROXY_PORT,
            username=LOGIN,
            password=PASSWORD,
            ssl_context=proxy_server_ssl_context,
        ),
    ]

    if not SKIP_IPV6_TESTS:
        config.append(
            ProxyConfig(
                proxy_type="socks5",
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

    server.shutdown()


@pytest.fixture(scope="session", autouse=True)
def web_server2(target_ssl_certfile: str, target_ssl_keyfile: str) -> Iterator[None]:
    config = [
        HttpServerConfig(
            host=TEST_HOST_IPV4,
            port=TEST_PORT_IPV4,
        ),
        HttpServerConfig(
            host=TEST_HOST_IPV4,
            port=TEST_PORT_IPV4_HTTPS,
            ssl_certfile=target_ssl_certfile,
            ssl_keyfile=target_ssl_keyfile,
        ),
    ]

    if not SKIP_IPV6_TESTS:
        config.append(HttpServerConfig(host=TEST_HOST_IPV6, port=TEST_PORT_IPV6))

    server = HttpServer(config=config)
    server.start()
    for cfg in config:
        wait_until_connectable(host=cfg.host, port=cfg.port, timeout=10)

    yield None

    server.shutdown()
