import socket
import ssl

from ._connect import connect_tcp
from ._stream import SyncSocketStream
from .._resolver import SyncResolver
from ... import _abc as abc
from ..._errors import ProxyConnectionError, ProxyTimeoutError, ProxyError
from ..._proto.http_sync import HttpProto

from ..._protocols.errors import ReplyError
from ..._connectors.socks5_sync import Socks5SyncConnector
from ..._connectors.socks4_sync import Socks4SyncConnector

DEFAULT_TIMEOUT = 60


class SyncProxy(abc.SyncProxy):
    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
        proxy_ssl: ssl.SSLContext = None,
        forward: 'SyncProxy' = None,
    ):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_ssl = proxy_ssl
        self._forward = forward

        self._resolver = SyncResolver()

    def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext = None,
        timeout: float = None,
    ) -> SyncSocketStream:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        try:
            if self._forward is None:
                stream = connect_tcp(
                    host=self._proxy_host,
                    port=self._proxy_port,
                    timeout=timeout,
                )
            else:
                stream = self._forward.connect(
                    dest_host=self._proxy_host,
                    dest_port=self._proxy_port,
                    timeout=timeout,
                )
        except OSError as e:
            msg = 'Could not connect to proxy {}:{} [{}]'.format(
                self._proxy_host,
                self._proxy_port,
                e.strerror,
            )
            raise ProxyConnectionError(e.errno, msg) from e

        try:
            if self._proxy_ssl is not None:
                stream = stream.start_tls(
                    hostname=self._proxy_host,
                    ssl_context=self._proxy_ssl,
                )

            self._negotiate(
                stream=stream,
                dest_host=dest_host,
                dest_port=dest_port,
            )

            if dest_ssl is not None:
                stream = stream.start_tls(
                    hostname=dest_host,
                    ssl_context=dest_ssl,
                )

            return stream

        except socket.timeout as e:
            stream.close()
            raise ProxyTimeoutError(f'Proxy connection timed out: {timeout}') from e
        except Exception:
            stream.close()
            raise

    def _negotiate(
        self,
        stream: SyncSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        raise NotImplementedError


class Socks5Proxy(SyncProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        rdns=None,
        proxy_ssl=None,
        forward: 'SyncProxy' = None,
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

    def _negotiate(
        self,
        stream: SyncSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        connector = Socks5SyncConnector(
            username=self._username,
            password=self._password,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            connector.connect(stream=stream, host=dest_host, port=dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class Socks4Proxy(SyncProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        user_id=None,
        rdns=None,
        proxy_ssl=None,
        forward: 'SyncProxy' = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            forward=forward,
        )
        self._user_id = user_id
        self._rdns = rdns

    def _negotiate(
        self,
        stream: SyncSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        connector = Socks4SyncConnector(
            user_id=self._user_id,
            rdns=self._rdns,
            resolver=self._resolver,
        )
        try:
            connector.connect(stream=stream, host=dest_host, port=dest_port)
        except ReplyError as e:
            raise ProxyError(e, error_code=e.error_code)


class HttpProxy(SyncProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        proxy_ssl=None,
        forward: 'SyncProxy' = None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
            forward=forward,
        )
        self._username = username
        self._password = password

    def _negotiate(
        self,
        stream: SyncSocketStream,
        dest_host: str,
        dest_port: int,
    ):
        proto = HttpProto(
            stream=stream,
            dest_host=dest_host,
            dest_port=dest_port,
            username=self._username,
            password=self._password,
        )
        proto.negotiate()
