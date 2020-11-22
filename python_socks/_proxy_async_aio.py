import asyncio
import sys

import async_timeout

from ._errors import ProxyConnectionError, ProxyTimeoutError
from ._proxy_async import (
    AsyncProxy,
    Socks4ProxyNegotiator,
    Socks5ProxyNegotiator,
    HttpProxyNegotiator
)
from ._proxy_factory import ProxyFactory
from ._types import ProxyType
from ._stream_async_aio import AsyncioSocketStream

DEFAULT_TIMEOUT = 60


class AsyncioProxyConnection(AsyncProxy):
    def __init__(self, proxy_host, proxy_port,
                 loop: asyncio.AbstractEventLoop = None):

        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._dest_host = None
        self._dest_port = None
        self._timeout = None

        self._stream = AsyncioSocketStream(loop=loop)

    async def connect(self, dest_host, dest_port, timeout=None, _socket=None):
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._timeout = timeout

        try:
            await self._connect(_socket=_socket)
        except asyncio.TimeoutError as e:
            raise ProxyTimeoutError(
                'Proxy connection timed out: %s'
                % self._timeout) from e

        return self._stream.socket

    async def _connect(self, _socket=None):
        async with async_timeout.timeout(self._timeout):
            try:
                await self._stream.open_connection(
                    host=self._proxy_host,
                    port=self._proxy_port,
                    timeout=self._timeout,
                    _socket=_socket
                )
            except OSError as e:
                await self._stream.close()
                msg = ('Can not connect to proxy %s:%s [%s]' %
                       (self._proxy_host, self._proxy_port, e.strerror))
                raise ProxyConnectionError(e.errno, msg) from e
            except Exception:  # pragma: no cover
                await self._stream.close()
                raise

            try:
                await self.negotiate()
            except asyncio.CancelledError:  # pragma: no cover
                # https://bugs.python.org/issue30064
                # https://bugs.python.org/issue34795
                if self._can_be_closed_safely():
                    await self._stream.close()
                raise
            except Exception:
                await self._stream.close()
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

        return (sys.version_info[:2] >= (3, 8)
                or is_proactor_event_loop()
                or is_uvloop_event_loop())

    async def negotiate(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_host(self):
        return self._proxy_host

    @property
    def proxy_port(self):
        return self._proxy_port


class Socks5Proxy(Socks5ProxyNegotiator, AsyncioProxyConnection):
    def __init__(self, proxy_host, proxy_port,
                 username=None, password=None, rdns=None,
                 loop: asyncio.AbstractEventLoop = None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port,
                         loop=loop)
        self._username = username
        self._password = password
        self._rdns = rdns


class Socks4Proxy(Socks4ProxyNegotiator, AsyncioProxyConnection):
    def __init__(self, proxy_host, proxy_port,
                 user_id=None, rdns=None,
                 loop: asyncio.AbstractEventLoop = None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port,
                         loop=loop)
        self._user_id = user_id
        self._rdns = rdns


class HttpProxy(HttpProxyNegotiator, AsyncioProxyConnection):
    def __init__(self, proxy_host, proxy_port,
                 username=None, password=None,
                 loop: asyncio.AbstractEventLoop = None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port,
                         loop=loop)
        self._username = username
        self._password = password


class Proxy(ProxyFactory):
    types = {
        ProxyType.SOCKS4: Socks4Proxy,
        ProxyType.SOCKS5: Socks5Proxy,
        ProxyType.HTTP: HttpProxy,
    }
