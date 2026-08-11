from __future__ import annotations

import socket

from .._abc import SyncResolver, SyncSocketStream
from .._helpers import is_ip_address
from .._protocols import socks4
from .abc import SyncConnector


class Socks4SyncConnector(SyncConnector):
    def __init__(
        self,
        user_id: str | None,
        rdns: bool | None,  # noqa: FBT001
        resolver: SyncResolver,
    ) -> None:
        if rdns is None:
            rdns = False

        self._user_id = user_id
        self._rdns = rdns
        self._resolver = resolver

    def connect(
        self,
        stream: SyncSocketStream,
        host: str,
        port: int,
    ) -> socks4.ConnectReply:
        conn = socks4.Connection()

        if not is_ip_address(host) and not self._rdns:
            _, host = self._resolver.resolve(
                host,
                family=socket.AF_INET,
            )

        request = socks4.ConnectRequest(host=host, port=port, user_id=self._user_id)
        data = conn.send(request)
        stream.write(data)

        data = stream.read_exactly(socks4.ConnectReply.SIZE)
        reply: socks4.ConnectReply = conn.receive(data)
        return reply
