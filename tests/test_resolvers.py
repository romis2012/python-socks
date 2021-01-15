import socket
from unittest.mock import MagicMock, patch

import curio
import pytest

from python_socks._resolver_async_aio import Resolver as AsyncioResolver
from python_socks._resolver_async_trio import Resolver as TrioResolver
from python_socks._resolver_async_curio import Resolver as CurioResolver
from python_socks._resolver_sync import SyncResolver

RET_FAMILY = socket.AF_INET
RET_HOST = '127.0.0.1'

RET_VALUE = [(
    RET_FAMILY,
    socket.SOCK_STREAM,
    6,
    '',
    (RET_HOST, 0)
)]


async def get_value_async():
    return RET_VALUE


TEST_HOST_NAME = 'fake.host.name'


@patch('socket.getaddrinfo', return_value=RET_VALUE)
def test_sync_resolver_1(_):
    resolver = SyncResolver()
    family, host = resolver.resolve(host=TEST_HOST_NAME)
    assert family == RET_FAMILY
    assert host == RET_HOST


@patch('socket.getaddrinfo', return_value=[])
def test_sync_resolver_2(_):
    with pytest.raises(OSError):
        resolver = SyncResolver()
        resolver.resolve(host=TEST_HOST_NAME)


@pytest.mark.asyncio
async def test_asyncio_resolver():
    loop = MagicMock()
    loop.getaddrinfo = MagicMock()
    loop.getaddrinfo.return_value = get_value_async()
    resolver = AsyncioResolver(loop)
    family, host = await resolver.resolve(host=TEST_HOST_NAME)
    assert family == RET_FAMILY
    assert host == RET_HOST


@pytest.mark.trio
async def test_trio_resolver():
    getaddrinfo = MagicMock()
    getaddrinfo.return_value = get_value_async()
    # with patch('trio.socket.getaddrinfo', return_value=get_value_async()):
    with patch('trio.socket.getaddrinfo', new=getaddrinfo):
        resolver = TrioResolver()
        family, host = await resolver.resolve(host=TEST_HOST_NAME)
        assert family == RET_FAMILY
        assert host == RET_HOST


def test_curio_resolver():
    getaddrinfo = MagicMock()
    getaddrinfo.return_value = get_value_async()
    to_patch = 'python_socks._resolver_async_curio.getaddrinfo'

    async def run():
        # with patch(to_patch, return_value=get_value_async()):
        with patch(to_patch, new=getaddrinfo):
            resolver = CurioResolver()
            family, host = await resolver.resolve(host=TEST_HOST_NAME)
            assert family == RET_FAMILY
            assert host == RET_HOST

    curio.run(run)
