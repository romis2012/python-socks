from __future__ import annotations

import asyncio
import ssl
import sys
import warnings
from typing import Any

from ...._connectors.factory_async import create_connector
from ...._errors import (
    IncompleteReadError,
    ProxyConnectionError,
    ProxyError,
    ProxyTimeoutError,
)
from ...._helpers import parse_proxy_url
from ...._protocols.errors import ReplyError
from ...._types import ProxyType
from .._resolver import Resolver
from ._connect import connect_tcp
from ._stream import AsyncioSocketStream

if sys.version_info >= (3, 11):
    import asyncio as async_timeout
else:
    import async_timeout


DEFAULT_TIMEOUT = 60


class AsyncioProxy:
    def __init__(  # noqa: PLR0913, PLR0917
        self,
        proxy_type: ProxyType,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        rdns: bool | None = None,  # noqa: FBT001
        proxy_ssl: ssl.SSLContext | None = None,
        forward: AsyncioProxy | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        if loop is not None:  # pragma: no cover
            warnings.warn(
                "The loop argument is deprecated "
                "and scheduled for removal in the future.",
                DeprecationWarning,
                stacklevel=2,
            )

        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._proxy_type = proxy_type
        self._proxy_host = host
        self._proxy_port = port
        self._username = username
        self._password = password
        self._rdns = rdns

        self._proxy_ssl = proxy_ssl
        self._forward = forward

        self._resolver = Resolver(loop=loop)

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> AsyncioSocketStream:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        local_addr = kwargs.get("local_addr")
        try:
            async with async_timeout.timeout(timeout):
                return await self._connect(
                    dest_host=dest_host,
                    dest_port=dest_port,
                    dest_ssl=dest_ssl,
                    local_addr=local_addr,
                )
        except asyncio.TimeoutError as e:
            raise ProxyTimeoutError(f"Proxy connection timed out: {timeout}") from e

    async def _connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        local_addr: tuple[str, int] | None = None,
    ) -> AsyncioSocketStream:
        if self._forward is None:
            try:
                stream = await connect_tcp(
                    host=self._proxy_host,
                    port=self._proxy_port,
                    loop=self._loop,
                    local_addr=local_addr,
                )
            except OSError as e:
                raise ProxyConnectionError(
                    e.errno,
                    "Couldn't connect to proxy"
                    f" {self._proxy_host}:{self._proxy_port} [{e.strerror}]",
                ) from e
        else:
            stream = await self._forward.connect(
                dest_host=self._proxy_host,
                dest_port=self._proxy_port,
            )

        try:
            if self._proxy_ssl is not None:
                stream = await stream.start_tls(
                    hostname=self._proxy_host,
                    ssl_context=self._proxy_ssl,
                )

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

            if dest_ssl is not None:
                stream = await stream.start_tls(
                    hostname=dest_host,
                    ssl_context=dest_ssl,
                )
        except ReplyError as e:
            await stream.close()
            raise ProxyError(e, error_code=e.error_code) from e
        except IncompleteReadError as e:
            await stream.close()
            raise ProxyError(e) from e
        except (asyncio.CancelledError, Exception):
            await stream.close()
            raise

        return stream

    @classmethod
    def create(
        cls, *args: Any, **kwargs: Any
    ) -> AsyncioProxy:  # for backward compatibility
        return cls(*args, **kwargs)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> AsyncioProxy:
        url_args = parse_proxy_url(url)
        return cls(*url_args, **kwargs)
