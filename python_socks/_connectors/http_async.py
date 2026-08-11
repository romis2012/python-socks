from __future__ import annotations

from .._abc import AsyncResolver, AsyncSocketStream
from .._protocols import http
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

        data = await stream.read()
        reply: http.ConnectReply = conn.receive(data)
        return reply
