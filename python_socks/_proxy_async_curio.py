import curio

from ._errors import ProxyConnectionError, ProxyTimeoutError
from ._proxy_async import (
    AsyncProxy,
    Socks4ProxyNegotiator,
    Socks5ProxyNegotiator,
    HttpProxyNegotiator
)
from ._proxy_factory import ProxyFactory
from ._stream_async_curio import CurioSocketStream
from ._types import ProxyType

DEFAULT_TIMEOUT = 60


class CurioProxyConnection(AsyncProxy):
    def __init__(self, proxy_host, proxy_port):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._dest_host = None
        self._dest_port = None
        self._timeout = None

        self._stream = CurioSocketStream()

    async def connect(self, dest_host, dest_port, timeout=None, _socket=None):
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._timeout = timeout

        try:
            await curio.timeout_after(self._timeout, self._connect, _socket)
        except OSError as e:
            await self._stream.close()
            msg = ('Can not connect to proxy %s:%s [%s]' %
                   (self._proxy_host, self._proxy_port, e.strerror))
            raise ProxyConnectionError(e.errno, msg) from e
        except curio.TaskTimeout as e:
            await self._stream.close()
            raise ProxyTimeoutError('Proxy connection timed out: %s'
                                    % self._timeout) from e
        except Exception:
            await self._stream.close()
            raise

        return self._stream.socket

    async def _connect(self, _socket=None):
        await self._stream.open_connection(
            host=self._proxy_host,
            port=self._proxy_port,
            timeout=self._timeout,
            _socket=_socket
        )
        await self.negotiate()

    async def negotiate(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_host(self):
        return self._proxy_host

    @property
    def proxy_port(self):
        return self._proxy_port


class Socks5Proxy(Socks5ProxyNegotiator, CurioProxyConnection):
    def __init__(self, proxy_host, proxy_port,
                 username=None, password=None, rdns=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
        self._username = username
        self._password = password
        self._rdns = rdns


class Socks4Proxy(Socks4ProxyNegotiator, CurioProxyConnection):
    def __init__(self, proxy_host, proxy_port, user_id=None, rdns=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
        self._user_id = user_id
        self._rdns = rdns


class HttpProxy(HttpProxyNegotiator, CurioProxyConnection):
    def __init__(self, proxy_host, proxy_port, username=None, password=None):
        super().__init__(proxy_host=proxy_host, proxy_port=proxy_port)
        self._username = username
        self._password = password


class Proxy(ProxyFactory):
    types = {
        ProxyType.SOCKS4: Socks4Proxy,
        ProxyType.SOCKS5: Socks5Proxy,
        ProxyType.HTTP: HttpProxy,
    }
