from ._proto_socks5_async import Socks5Proto
from ._proto_http_async import HttpProto
from ._proto_socks4_async import Socks4Proto
from ._stream_async import AsyncSocketStream


class AsyncProxy:
    async def connect(self, dest_host, dest_port,
                      timeout=None, _socket=None):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_host(self):
        raise NotImplementedError()  # pragma: no cover

    @property
    def proxy_port(self):
        raise NotImplementedError()  # pragma: no cover


class Socks5ProxyNegotiator:
    _stream: AsyncSocketStream
    _dest_host: str
    _dest_port: int
    _username: str
    _password: str
    _rdns: str

    async def negotiate(self):
        proto = Socks5Proto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
            rdns=self._rdns
        )
        await proto.negotiate()


class Socks4ProxyNegotiator:
    _stream: AsyncSocketStream
    _dest_host: str
    _dest_port: int
    _user_id: str
    _rdns: str

    async def negotiate(self):
        proto = Socks4Proto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            user_id=self._user_id,
            rdns=self._rdns
        )
        await proto.negotiate()


class HttpProxyNegotiator:
    _stream: AsyncSocketStream
    _dest_host: str
    _dest_port: int
    _username: str
    _password: str

    async def negotiate(self):
        proto = HttpProto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password
        )
        await proto.negotiate()
