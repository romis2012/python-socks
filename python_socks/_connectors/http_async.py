from __future__ import annotations

from .._abc import AsyncResolver, AsyncSocketStream
from .._protocols import http
from .._protocols.errors import ReplyError
from .abc import AsyncConnector


class HttpAsyncConnector(AsyncConnector):
    def __init__(
        self,
        username: str | None,
        password: str | None,
        resolver: AsyncResolver,
    ) -> None:
        self._username = username
        self._password = password
        self._resolver = resolver

    async def connect(
        self,
        stream: AsyncSocketStream,
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
        await stream.write(data)

        # Stop exactly at the end of the headers: following bytes belong to the tunnel.
        response = bytearray()
        while not response.endswith(b"\r\n\r\n"):
            if len(response) >= http.MAX_REPLY_SIZE:
                raise ReplyError("HTTP proxy response headers are too long")
            chunk = await stream.read(1)
            if not chunk:
                raise ReplyError("Invalid proxy response")
            response += chunk
        reply: http.ConnectReply = conn.receive(bytes(response))
        return reply
