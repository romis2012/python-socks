import socket

from .. import _abc as abc
from .._protocols import socks4
from .._helpers import is_ip_address


class Socks4SyncConnector:
    def __init__(
        self,
        user_id: str,
        rdns: bool,
        resolver: abc.SyncResolver,
    ):
        self._user_id = user_id
        self._rdns = rdns
        self._resolver = resolver

    def connect(
        self,
        stream: abc.SyncSocketStream,
        host: str,
        port: int,
    ) -> socks4.ConnectReply:
        conn = socks4.Connection()

        if not is_ip_address(host) and not self._rdns:
            _, dest_host = self._resolver.resolve(
                host,
                family=socket.AF_INET,
            )

        request = socks4.ConnectRequest(host=host, port=port, user_id=self._user_id)
        data = conn.send(request)
        stream.write_all(data)

        data = stream.read_exact(socks4.ConnectReply.SIZE)
        reply: socks4.ConnectReply = conn.receive(data)
        return reply
