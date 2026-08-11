from __future__ import annotations

import ssl
from typing import Union

import trio

from .... import _abc as abc
from ...._errors import IncompleteReadError

DEFAULT_RECEIVE_SIZE = 65536

TrioStreamType = Union[trio.SocketStream, trio.SSLStream]


class TrioSocketStream(abc.AsyncSocketStream):
    def __init__(self, stream: TrioStreamType) -> None:
        self._stream = stream

    async def write(self, data: bytes) -> None:
        await self._stream.send_all(data)

    async def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        return await self._stream.receive_some(max_bytes)  # type:ignore[return-value]

    async def read_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = await self._stream.receive_some(n - len(data))
            if not packet:  # pragma: no cover
                raise IncompleteReadError("Connection closed unexpectedly")
            data.extend(packet)
        return data  # type:ignore[return-value]

    async def start_tls(
        self,
        hostname: str,
        ssl_context: ssl.SSLContext,
    ) -> TrioSocketStream:
        ssl_stream = trio.SSLStream(
            self._stream,
            ssl_context=ssl_context,
            server_hostname=hostname,
            https_compatible=True,
            server_side=False,
        )
        await ssl_stream.do_handshake()
        return TrioSocketStream(ssl_stream)

    async def close(self) -> None:
        await self._stream.aclose()

    @property
    def trio_stream(self) -> TrioStreamType:  # pragma: nocover
        return self._stream
