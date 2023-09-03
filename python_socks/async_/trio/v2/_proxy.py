import ssl

import trio

from ._connect import connect_tcp
from ._stream import TrioSocketStream
from .._resolver import Resolver
from ...._errors import ProxyConnectionError, ProxyTimeoutError, ProxyError

from ...._protocols.errors import ReplyError
from ...._connectors.socks5_async import Socks5AsyncConnector
from ...._connectors.socks4_async import Socks4AsyncConnector
from ...._connectors.http_async import HttpAsyncConnector

DEFAULT_TIMEOUT = 60


class TrioProxy:
    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
        proxy_ssl: ssl.SSLContext = None,
        forward: 'TrioProxy' = None,
    ):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_ssl = proxy_ssl
        self._forward = forward

        self._resolver = Resolver()

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext = None,
        timeout: float = None,
    ) -> TrioSocketStream:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        try:
            with trio.fail_after(timeout):
                return await self._connect(
                    dest_host=dest_host,
                    dest_port=dest_port,
                    dest_ssl=dest_ssl,
                )
        except trio.TooSlowError as e:
            raise ProxyTimeoutError('Proxy connection timed out: {}'.format(timeout)) from e

    async def _connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext = None,
    ) -> TrioSocketStream:
        try:
            if self._forward is None:
                stream = await connect_tcp(
                    host=self._proxy_host,
                    port=self._proxy_port,
                )
            else:
                stream = await self._forward.connect(
                    dest_host=self._proxy_host,
                    dest_port=self._proxy_port,
                )
        except OSError as e:
            raise ProxyConnectionError(
                e.errno,
                f"Couldn't connect to proxy {self._proxy_host}:{self._proxy_port} [{e.strerror}]",
            ) from e

        try:
            if self._proxy_ssl is not None:
                stream = await stream.start_tls(
                    hostname=self._proxy_host,
                    ssl_context=self._proxy_ssl,
                )

            await self._negotiate(
                stream=stream,
                dest_host=dest_host,
                dest_port=dest_port,
            )

            if dest_ssl is not None:
                stream = await stream.start_tls(
                    hostname=dest_host,
                    ssl_context=dest_ssl,
                )
        except BaseException:  # trio.Cancelled...
            with trio.CancelScope(shield=True):
                await stream.close()
            raise

        return stream

    async def _negotiate(
        self,
        stream: TrioSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        raise NotImplementedError


class Socks5Proxy(TrioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        rdns=None,
        proxy_ssl=None,
        forward: 'TrioProxy' = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            forward=forward,
        )
        self._username = username
        self._password = password
        self._rdns = rdns

    async def _negotiate(
        self,
        stream: TrioSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        connector = Socks5AsyncConnector(
            username=self._username,
            password=self._password,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            await connector.connect(stream=stream, host=dest_host, port=dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class Socks4Proxy(TrioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        user_id=None,
        rdns=None,
        proxy_ssl=None,
        forward: 'TrioProxy' = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            forward=forward,
        )
        self._user_id = user_id
        self._rdns = rdns

    async def _negotiate(
        self,
        stream: TrioSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        connector = Socks4AsyncConnector(
            user_id=self._user_id,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            await connector.connect(stream=stream, host=dest_host, port=dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class HttpProxy(TrioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        proxy_ssl=None,
        forward: 'TrioProxy' = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            forward=forward,
        )
        self._username = username
        self._password = password

    async def _negotiate(
        self,
        stream: TrioSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        connector = HttpAsyncConnector(
            username=self._username,
            password=self._password,
            resolver=self._resolver,
        )
        try:
            await connector.connect(stream=stream, host=dest_host, port=dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)
