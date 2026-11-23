from __future__ import annotations

import importlib

import pytest

from python_socks._helpers import parse_proxy_url
from tests.config import (
    SOCKS4_PROXY_PORT,
    TEST_HOST_IPV4,
    TEST_PORT_IPV4,
)


@pytest.mark.parametrize("credentials", ["admin", "ad%6Din", "admin:"])
@pytest.mark.parametrize("version", ["", ".v2"])
def test_sync_socks4_url_userid(credentials: str, version: str) -> None:
    proxy_class = importlib.import_module(f"python_socks.sync{version}").Proxy
    proxy = proxy_class.from_url(f"socks4://{credentials}@127.0.0.1:{SOCKS4_PROXY_PORT}")
    stream = proxy.connect(TEST_HOST_IPV4, TEST_PORT_IPV4)
    stream.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("credentials", ["admin", "ad%6Din", "admin:"])
@pytest.mark.parametrize("version", ["", ".v2"])
async def test_asyncio_socks4_url_userid(credentials: str, version: str) -> None:
    proxy_class = importlib.import_module(f"python_socks.async_.asyncio{version}").Proxy
    proxy = proxy_class.from_url(f"socks4://{credentials}@127.0.0.1:{SOCKS4_PROXY_PORT}")
    stream = await proxy.connect(TEST_HOST_IPV4, TEST_PORT_IPV4)
    if version:
        await stream.close()
    else:
        stream.close()


@pytest.mark.parametrize("scheme", ["http", "socks5"])
@pytest.mark.parametrize(
    ("credentials", "expected"),
    [
        ("admin", ("", "")),
        ("admin:", ("admin", "")),
        ("admin:secret", ("admin", "secret")),
    ],
)
def test_other_protocol_url_credentials(
    scheme: str, credentials: str, expected: tuple[str, str]
) -> None:
    assert parse_proxy_url(f"{scheme}://{credentials}@127.0.0.1:1080")[3:] == expected
