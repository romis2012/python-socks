from __future__ import annotations

import asyncio
import socket
import sys
from typing import Any

from ..._connectors.factory_async import create_connector
from ..._errors import (
    IncompleteReadError,
    ProxyConnectionError,
    ProxyError,
    ProxyTimeoutError,
)
from ..._helpers import parse_proxy_url
from ..._protocols.errors import ReplyError
from ..._types import ProxyType
from ._connect import connect_tcp
from ._resolver import Resolver
from ._stream import AsyncioSocketStream

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout

DEFAULT_TIMEOUT = 60


class AsyncioProxy:
    def __init__(
        self,
        proxy_type: ProxyType,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        rdns: bool | None = None,  # noqa: FBT001
        forward: AsyncioProxy | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._proxy_type = proxy_type
        self._proxy_host = host
        self._proxy_port = port
        self._password = password
        self._username = username
        self._rdns = rdns
        self._forward = forward

        self._resolver = Resolver(loop=loop)

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> socket.socket:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        local_addr = kwargs.get("local_addr")

        try:
            async with async_timeout.timeout(timeout):
                return await self._connect(
                    dest_host=dest_host,
                    dest_port=dest_port,
                    local_addr=local_addr,
                )
        except asyncio.TimeoutError as e:
            raise ProxyTimeoutError(f"Proxy connection timed out: {timeout}") from e

    async def _connect(
        self,
        dest_host: str,
        dest_port: int,
        local_addr: tuple[str, int] | None = None,
    ) -> socket.socket:
        if self._forward is not None:
            sock = await self._forward.connect(
                dest_host=self._proxy_host,
                dest_port=self._proxy_port,
                timeout=None,
            )
        else:
            try:
                sock = await connect_tcp(
                    host=self._proxy_host,
                    port=self._proxy_port,
                    loop=self._loop,
                    local_addr=local_addr,
                )
            except OSError as e:
                msg = (
                    f"Could not connect to proxy "
                    f"{self._proxy_host}:{self._proxy_port} [{e.strerror}]"
                )
                raise ProxyConnectionError(e.errno, msg) from e

        stream = AsyncioSocketStream(sock=sock, loop=self._loop)

        try:
            connector = create_connector(
                proxy_type=self._proxy_type,
                username=self._username,
                password=self._password,
                rdns=self._rdns,
                resolver=self._resolver,
            )
            await connector.connect(
                stream=stream,
                host=dest_host,
                port=dest_port,
            )

            return sock
        except ReplyError as e:
            await stream.close()
            raise ProxyError(e, error_code=e.error_code) from e
        except IncompleteReadError as e:
            await stream.close()
            raise ProxyError(e) from e
        except (asyncio.CancelledError, Exception):  # pragma: no cover
            await stream.close()
            raise

    @classmethod
    def create(
        cls, *args: Any, **kwargs: Any
    ) -> AsyncioProxy:  # for backward compatibility
        return cls(*args, **kwargs)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> AsyncioProxy:
        url_args = parse_proxy_url(url)
        return cls(*url_args, **kwargs)
