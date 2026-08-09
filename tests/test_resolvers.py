from __future__ import annotations

import asyncio
import socket
from typing import Any
from unittest.mock import patch

import pytest

from python_socks.async_.asyncio._resolver import Resolver as AsyncioResolver
from python_socks.sync._resolver import SyncResolver
from tests.mocks import AddrInfo
from tests.patches import (
    patch_asyncio_getaddrinfo,
    patch_sync_getaddrinfo,
)

RET_FAMILY = socket.AF_INET
RET_HOST = "127.0.0.1"
RET_VALUE: AddrInfo = [(RET_FAMILY, socket.SOCK_STREAM, 6, "", (RET_HOST, 0))]


def sync_getaddrinfo_mock(*_args: Any, **_kwargs: Any) -> AddrInfo:
    return RET_VALUE


async def async_getaddrinfo_mock(*_args: Any, **_kwargs: Any) -> AddrInfo:
    return RET_VALUE


TEST_HOST_NAME = "fake.host.name"


def test_sync_resolver_1() -> None:

    with patch_sync_getaddrinfo(new=sync_getaddrinfo_mock):
        resolver = SyncResolver()
        family, host = resolver.resolve(host=TEST_HOST_NAME)
        assert family == RET_FAMILY
        assert host == RET_HOST


def test_sync_resolver_2() -> None:
    with patch_sync_getaddrinfo(new=lambda *_, **__: []):  # noqa: SIM117
        with pytest.raises(OSError):  # noqa: PT012
            resolver = SyncResolver()
            resolver.resolve(host=TEST_HOST_NAME)


@pytest.mark.asyncio
async def test_asyncio_resolver() -> None:
    async def getaddrinfo(*_args: Any, **_kwargs: Any) -> AddrInfo:
        return RET_VALUE

    loop = asyncio.get_event_loop()
    with patch_asyncio_getaddrinfo(loop=loop, new=getaddrinfo):
        resolver = AsyncioResolver(loop)
        family, host = await resolver.resolve(host=TEST_HOST_NAME)
        assert family == RET_FAMILY
        assert host == RET_HOST


@pytest.mark.trio
async def test_trio_resolver() -> None:
    pytest.importorskip("trio")
    from python_socks.async_.trio._resolver import Resolver as TrioResolver

    with patch("trio.socket.getaddrinfo", new=async_getaddrinfo_mock):
        resolver = TrioResolver()
        family, host = await resolver.resolve(host=TEST_HOST_NAME)
        assert family == RET_FAMILY
        assert host == RET_HOST


@pytest.mark.anyio
async def test_anyio_resolver() -> None:
    pytest.importorskip("anyio")
    from python_socks.async_.anyio._resolver import Resolver as AnyioResolver

    with patch("anyio.getaddrinfo", new=async_getaddrinfo_mock):
        resolver = AnyioResolver()
        family, host = await resolver.resolve(host=TEST_HOST_NAME)
        assert family == RET_FAMILY
        assert host == RET_HOST
