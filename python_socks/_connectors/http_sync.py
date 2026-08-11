from __future__ import annotations

from .._abc import SyncResolver, SyncSocketStream
from .._protocols import http
from .abc import SyncConnector


class HttpSyncConnector(SyncConnector):
    def __init__(
        self,
        username: str | None,
        password: str | None,
        resolver: SyncResolver,
    ) -> None:
        self._username = username
        self._password = password
        self._resolver = resolver

    def connect(
        self,
        stream: SyncSocketStream,
        host: str,
        port: int,
    ) -> http.ConnectReply:
        conn = http.Connection()

        request = http.ConnectRequest(
            host=host,
            port=port,
            username=self._username,
            password=self._password,
        )
        data = conn.send(request)
        stream.write(data)

        data = stream.read()
        reply: http.ConnectReply = conn.receive(data)
        return reply
