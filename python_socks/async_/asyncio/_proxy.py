import asyncio
import socket
import sys
from typing import Optional

import async_timeout

from ..._errors import ProxyConnectionError, ProxyTimeoutError, ProxyError
from ._stream import AsyncioSocketStream
from ._resolver import Resolver

from ..._protocols.errors import ReplyError
from ..._connectors.socks5_async import Socks5AsyncConnector
from ..._connectors.socks4_async import Socks4AsyncConnector
from ..._connectors.http_async import HttpAsyncConnector

from ._connect import connect_tcp
from ... import _abc as abc

DEFAULT_TIMEOUT = 60


class AsyncioProxy(abc.AsyncProxy):
    _stream: Optional[abc.AsyncSocketStream]

    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
        loop: asyncio.AbstractEventLoop = None,
    ):
        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._dest_host = None
        self._dest_port = None
        self._timeout = None

        self._stream = None
        self._resolver = Resolver(loop=loop)

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        timeout: float = None,
        _socket=None,
    ) -> socket.socket:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._timeout = timeout

        try:
            return await self._connect(_socket=_socket)
        except asyncio.TimeoutError as e:
            raise ProxyTimeoutError('Proxy connection timed out: {}'.format(self._timeout)) from e

    async def _connect(self, _socket=None) -> socket.socket:
        async with async_timeout.timeout(self._timeout):
            try:
                if _socket is None:
                    _socket = await connect_tcp(
                        host=self._proxy_host,
                        port=self._proxy_port,
                        loop=self._loop,
                    )

                self._stream = AsyncioSocketStream(sock=_socket, loop=self._loop)
                await self._negotiate()
                return _socket
            except OSError as e:
                await self._close()
                msg = 'Could not connect to proxy {}:{} [{}]'.format(
                    self._proxy_host,
                    self._proxy_port,
                    e.strerror,
                )
                raise ProxyConnectionError(e.errno, msg) from e
            except asyncio.CancelledError:  # pragma: no cover
                # https://bugs.python.org/issue30064
                # https://bugs.python.org/issue34795
                if self._can_be_closed_safely():
                    await self._close()
                raise
            except Exception:  # pragma: no cover
                await self._close()
                raise

    def _can_be_closed_safely(self):  # pragma: no cover
        def is_proactor_event_loop():
            try:
                from asyncio import ProactorEventLoop  # noqa
            except ImportError:
                return False
            return isinstance(self._loop, ProactorEventLoop)

        def is_uvloop_event_loop():
            try:
                from uvloop import Loop  # noqa
            except ImportError:
                return False
            return isinstance(self._loop, Loop)

        return sys.version_info[:2] >= (3, 8) or is_proactor_event_loop() or is_uvloop_event_loop()

    async def _negotiate(self):
        raise NotImplementedError()  # pragma: no cover

    async def _close(self):
        if self._stream is not None:
            await self._stream.close()

    @property
    def proxy_host(self):
        return self._proxy_host

    @property
    def proxy_port(self):
        return self._proxy_port


class Socks5Proxy(AsyncioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        rdns=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port, loop=loop)
        self._username = username
        self._password = password
        self._rdns = rdns

    async def _negotiate(self):
        connector = Socks5AsyncConnector(
            username=self._username,
            password=self._password,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            await connector.connect(self._stream, host=self._dest_host, port=self._dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class Socks4Proxy(AsyncioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        user_id=None,
        rdns=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port, loop=loop)
        self._user_id = user_id
        self._rdns = rdns

    async def _negotiate(self):
        connector = Socks4AsyncConnector(
            user_id=self._user_id,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            await connector.connect(self._stream, host=self._dest_host, port=self._dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class HttpProxy(AsyncioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port, loop=loop)
        self._username = username
        self._password = password

    async def _negotiate(self):
        connector = HttpAsyncConnector(
            username=self._username,
            password=self._password,
            resolver=self._resolver,
        )
        try:
            await connector.connect(self._stream, host=self._dest_host, port=self._dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)
