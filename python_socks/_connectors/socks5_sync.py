import socket

from .._abc import SyncSocketStream, SyncResolver
from .abc import SyncConnector

from .._protocols import socks5
from .._helpers import is_ip_address


class Socks5SyncConnector(SyncConnector):
    def __init__(
        self,
        username: str,
        password: str,
        rdns: bool,
        resolver: SyncResolver,
    ):
        if rdns is None:
            rdns = True

        self._username = username
        self._password = password
        self._rdns = rdns
        self._resolver = resolver

    def connect(
        self,
        stream: SyncSocketStream,
        host: str,
        port: int,
    ) -> socks5.ConnectReply:
        conn = socks5.Connection()

        # Auth methods
        request = socks5.AuthMethodsRequest(username=self._username, password=self._password)
        data = conn.send(request)
        stream.write_all(data)

        data = stream.read_exact(socks5.AuthMethodReply.SIZE)
        reply: socks5.AuthMethodReply = conn.receive(data)

        # Authenticate
        if reply.method == socks5.AuthMethod.USERNAME_PASSWORD:
            request = socks5.AuthRequest(username=self._username, password=self._password)
            data = conn.send(request)
            stream.write_all(data)

            data = stream.read_exact(socks5.AuthReply.SIZE)
            _: socks5.AuthReply = conn.receive(data)

        # Connect
        if not is_ip_address(host) and not self._rdns:
            _, dest_host = self._resolver.resolve(host, family=socket.AF_UNSPEC)

        request = socks5.ConnectRequest(host=host, port=port)
        data = conn.send(request)
        stream.write_all(data)

        data = stream.read()
        reply: socks5.ConnectReply = conn.receive(data)
        return reply
