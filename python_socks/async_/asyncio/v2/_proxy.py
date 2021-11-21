import asyncio

import async_timeout

from ...._errors import ProxyConnectionError, ProxyTimeoutError
from ...._proto.http_async import HttpProto
from ...._proto.socks4_async import Socks4Proto
from ...._proto.socks5_async import Socks5Proto

from .._resolver import Resolver
from ._stream import AsyncioSocketStream
from ._connect import connect_tcp

DEFAULT_TIMEOUT = 60


class AsyncioProxy:
    def __init__(
        self,
        proxy_host,
        proxy_port,
        proxy_ssl=None,
        loop: asyncio.AbstractEventLoop = None,
    ):

        if loop is None:
            loop = asyncio.get_event_loop()

        self._loop = loop

        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_ssl = proxy_ssl

        self._dest_host = None
        self._dest_port = None
        self._dest_ssl = None
        self._timeout = None

        self._stream = None
        self._resolver = Resolver(loop=loop)

    async def connect(
        self,
        dest_host,
        dest_port,
        dest_ssl=None,
        timeout=None,
        _stream: AsyncioSocketStream = None,
    ) -> AsyncioSocketStream:

        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._dest_ssl = dest_ssl
        self._timeout = timeout

        try:
            return await self._connect(_stream)
        except asyncio.TimeoutError as e:
            raise ProxyTimeoutError('Proxy connection timed out: {}'.format(self._timeout)) from e

    async def _connect(self, _stream: AsyncioSocketStream) -> AsyncioSocketStream:
        async with async_timeout.timeout(self._timeout):
            try:
                if _stream is None:
                    reader, writer = await connect_tcp(
                        host=self._proxy_host,
                        port=self._proxy_port,
                        loop=self._loop,
                    )
                    self._stream = AsyncioSocketStream(
                        loop=self._loop,
                        reader=reader,
                        writer=writer,
                    )
                else:
                    self._stream = _stream

                if self._proxy_ssl is not None:  # pragma: no cover
                    await self._stream.start_tls(
                        hostname=self._proxy_host,
                        ssl_context=self._proxy_ssl,
                    )

                await self._negotiate()

                if self._dest_ssl is not None:
                    await self._stream.start_tls(
                        hostname=self._dest_host,
                        ssl_context=self._dest_ssl,
                    )

                return self._stream

            except OSError as e:
                await self._close()
                msg = 'Could not connect to proxy {}:{} [{}]'.format(
                    self._proxy_host,
                    self._proxy_port,
                    e.strerror,
                )
                raise ProxyConnectionError(e.errno, msg) from e
            except (asyncio.CancelledError, Exception):
                await self._close()
                raise

    async def _negotiate(self):
        raise NotImplementedError()

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
        proxy_ssl=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            loop=loop,
        )
        self._username = username
        self._password = password
        self._rdns = rdns

    async def _negotiate(self):
        proto = Socks5Proto(
            stream=self._stream,
            resolver=self._resolver,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
            rdns=self._rdns,
        )
        await proto.negotiate()


class Socks4Proxy(AsyncioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        user_id=None,
        rdns=None,
        proxy_ssl=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            loop=loop,
        )
        self._user_id = user_id
        self._rdns = rdns

    async def _negotiate(self):
        proto = Socks4Proto(
            stream=self._stream,
            resolver=self._resolver,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            user_id=self._user_id,
            rdns=self._rdns,
        )
        await proto.negotiate()


class HttpProxy(AsyncioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        proxy_ssl=None,
        loop: asyncio.AbstractEventLoop = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            loop=loop,
        )
        self._username = username
        self._password = password

    async def _negotiate(self):
        proto = HttpProto(
            stream=self._stream,  # noqa
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
        )
        await proto.negotiate()
