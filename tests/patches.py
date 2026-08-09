from asyncio import AbstractEventLoop
from typing import Any
from unittest.mock import patch

from tests.mocks import getaddrinfo_async_mock, getaddrinfo_sync_mock


def patch_sync_getaddrinfo(*, new: Any = None, **kwargs: Any) -> Any:
    if new is None:
        new = getaddrinfo_sync_mock()

    return patch(
        "socket.getaddrinfo",
        new=new,
        **kwargs,
    )


def patch_asyncio_getaddrinfo(
    loop: AbstractEventLoop,
    new: Any = None,
    **kwargs: Any,
) -> Any:
    if new is None:
        new = getaddrinfo_async_mock(loop.getaddrinfo)

    return patch.object(
        loop,
        attribute="getaddrinfo",
        new=new,
        **kwargs,
    )


def patch_anyio_getaddrinfo(new: Any = None, **kwargs: Any) -> Any:
    import anyio

    if new is None:
        new = getaddrinfo_async_mock(anyio.getaddrinfo)

    return patch(
        "anyio._core._sockets.getaddrinfo",
        new=new,
        **kwargs,
    )


def patch_trio_getaddrinfo(new: Any = None, **kwargs: Any) -> Any:
    import trio

    if new is None:
        new = getaddrinfo_async_mock(trio.socket.getaddrinfo)

    return patch(
        "trio._highlevel_open_tcp_stream.getaddrinfo",
        new=new,
        **kwargs,
    )
