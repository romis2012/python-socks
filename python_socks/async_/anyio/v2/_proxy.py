from __future__ import annotations

import ssl
from typing import Any

import anyio

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
from ._stream import AnyioSocketStream

DEFAULT_TIMEOUT = 60


class AnyioProxy:
    def __init__(
        self,
        proxy_type: ProxyType,
        host: str,
        port: int,
        username: str | None = None,
        password: str | None = None,
        rdns: bool | None = None,  # noqa: FBT001
        proxy_ssl: ssl.SSLContext | None = None,
        forward: AnyioProxy | None = None,
    ) -> None:
        self._proxy_type = proxy_type
        self._proxy_host = host
        self._proxy_port = port
        self._username = username
        self._password = password
        self._rdns = rdns

        self._proxy_ssl = proxy_ssl
        self._forward = forward

        self._resolver = Resolver()

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        timeout: float | None = None,
        **kwargs: Any,
    ) -> AnyioSocketStream:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        try:
            with anyio.fail_after(timeout):
                return await self._connect(
                    dest_host=dest_host,
                    dest_port=dest_port,
                    dest_ssl=dest_ssl,
                    **kwargs,
                )
        except TimeoutError as e:
            raise ProxyTimeoutError(f"Proxy connection timed out: {timeout}") from e

    async def _connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        **kwargs: Any,
    ) -> AnyioSocketStream:
        if self._forward is None:
            try:
                stream = await connect_tcp(
                    host=self._proxy_host,
                    port=self._proxy_port,
                    **kwargs,
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
                **kwargs,
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
        except BaseException:
            with anyio.CancelScope(shield=True):
                await stream.close()
            raise

        return stream

    @classmethod
    def create(
        cls, *args: Any, **kwargs: Any
    ) -> AnyioProxy:  # for backward compatibility
        return cls(*args, **kwargs)

    @classmethod
    def from_url(cls, url: str, **kwargs: Any) -> AnyioProxy:
        url_args = parse_proxy_url(url)
        return cls(*url_args, **kwargs)
