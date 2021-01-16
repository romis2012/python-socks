import socket

from ._errors import ProxyConnectionError, ProxyTimeoutError
from ._proto_http_sync import HttpProto
from ._proto_socks4_sync import Socks4Proto
from ._proto_socks5_sync import Socks5Proto
from ._stream_sync import SyncSocketStream

DEFAULT_TIMEOUT = 60


class SyncProxy:
    def connect(self, dest_host, dest_port, timeout=None, _socket=None):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_host(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_port(self):
        raise NotImplementedError()  # pragma: no cover


class BaseProxy(SyncProxy):
    def __init__(self, proxy_host, proxy_port):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port

        self._dest_host = None
        self._dest_port = None
        self._timeout = None

        self._stream = SyncSocketStream()

    def connect(self, dest_host, dest_port, timeout=None, _socket=None):
        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._timeout = timeout

        try:
            self._stream.open_connection(
                host=self._proxy_host,
                port=self._proxy_port,
                timeout=timeout,
                _socket=_socket
            )

            self.negotiate()

        except socket.timeout as e:
            self._stream.close()
            raise ProxyTimeoutError('Proxy connection timed out: %s'
                                    % self._timeout) from e
        except OSError as e:
            self._stream.close()
            msg = ('Can not connect to proxy %s:%s [%s]' %
                   (self._proxy_host, self._proxy_port, e.strerror))
            raise ProxyConnectionError(e.errno, msg) from e
        except Exception:
            self._stream.close()
            raise

        return self._stream.socket

    def negotiate(self):
        raise NotImplementedError

    @property
    def proxy_host(self):
        return self._proxy_host

    @property
    def proxy_port(self):
        return self._proxy_port


class Socks5Proxy(BaseProxy):
    def __init__(self, proxy_host, proxy_port,
                 username=None, password=None, rdns=None):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port
        )
        self._username = username
        self._password = password
        self._rdns = rdns

    def negotiate(self):
        proto = Socks5Proto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
            rdns=self._rdns
        )
        proto.negotiate()


class Socks4Proxy(BaseProxy):
    def __init__(self, proxy_host, proxy_port,
                 user_id=None, rdns=None):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port
        )
        self._user_id = user_id
        self._rdns = rdns

    def negotiate(self):
        proto = Socks4Proto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            user_id=self._user_id,
            rdns=self._rdns
        )
        proto.negotiate()


class HttpProxy(BaseProxy):
    def __init__(self, proxy_host, proxy_port, username=None, password=None):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port
        )
        self._username = username
        self._password = password

    def negotiate(self):
        proto = HttpProto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password
        )
        proto.negotiate()
