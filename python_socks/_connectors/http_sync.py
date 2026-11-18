from __future__ import annotations

from .._abc import SyncResolver, SyncSocketStream
from .._protocols import http
from .._protocols.errors import ReplyError
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

        # Stop exactly at the end of the headers: following bytes belong to the tunnel.
        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            if len(response) >= http.MAX_REPLY_SIZE:
                raise ReplyError("HTTP proxy response headers are too long")
            chunk = stream.read(1)
            if not chunk:
                raise ReplyError("Invalid proxy response")
            response += chunk
        reply: http.ConnectReply = conn.receive(bytes(response))
        return reply
