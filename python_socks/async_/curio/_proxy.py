import curio
import curio.io

from ..._errors import ProxyConnectionError, ProxyTimeoutError
from ..._proto.http_async import HttpProto
from ..._proto.socks4_async import Socks4Proto
from ..._proto.socks5_async import Socks5Proto
from ._stream import CurioSocketStream
from ._resolver import Resolver
from ._connect import connect_tcp

from ... import _abc as abc

DEFAULT_TIMEOUT = 60


class CurioProxy(abc.AsyncProxy):
    def __init__(
        self,
        proxy_host: str,
        proxy_port: int,
    ):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._dest_host = None
        self._dest_port = None
        self._timeout = None

        self._stream = None
        self._resolver = Resolver()

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        timeout: float = None,
        _socket=None,
    ) -> curio.io.Socket:
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._timeout = timeout

        try:
            return await curio.timeout_after(self._timeout, self._connect, _socket)
        except OSError as e:
            await self._close()
            msg = 'Could not connect to proxy {}:{} [{}]'.format(
                self._proxy_host,
                self._proxy_port,
                e.strerror,
            )
            raise ProxyConnectionError(e.errno, msg) from e
        except curio.TaskTimeout as e:
            await self._close()
            raise ProxyTimeoutError('Proxy connection timed out: %s' % self._timeout) from e
        except Exception:
            await self._close()
            raise

    async def _connect(self, _socket=None):
        if _socket is None:
            _socket = await connect_tcp(
                host=self._proxy_host,
                port=self._proxy_port,
            )
        self._stream = CurioSocketStream(_socket)
        await self._negotiate()
        return _socket

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


class Socks5Proxy(CurioProxy):
    def __init__(self, proxy_host, proxy_port, username=None, password=None, rdns=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
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


class Socks4Proxy(CurioProxy):
    def __init__(self, proxy_host, proxy_port, user_id=None, rdns=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
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


class HttpProxy(CurioProxy):
    def __init__(self, proxy_host, proxy_port, username=None, password=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
        self._username = username
        self._password = password

    async def _negotiate(self):
        proto = HttpProto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
        )
        await proto.negotiate()
