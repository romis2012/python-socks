from __future__ import annotations

from typing import Union

import anyio
import anyio.abc
from anyio.streams.tls import TLSStream

from ... import _abc as abc
from ..._errors import IncompleteReadError

DEFAULT_RECEIVE_SIZE = 65536

AnyioStreamType = Union[anyio.abc.SocketStream, TLSStream]


class AnyioSocketStream(abc.AsyncSocketStream):
    def __init__(self, stream: AnyioStreamType) -> None:
        self._stream = stream

    async def write(self, data: bytes) -> None:
        await self._stream.send(item=data)

    async def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        try:
            return await self._stream.receive(max_bytes=max_bytes)
        except anyio.EndOfStream:  # pragma: no cover
            return b""

    async def read_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = await self.read(n - len(data))
            if not packet:  # pragma: no cover
                raise IncompleteReadError("Connection closed unexpectedly")
            data.extend(packet)
        return data  # type:ignore[return-value]

    async def close(self) -> None:
        await self._stream.aclose()

    @property
    def anyio_stream(self) -> AnyioStreamType:  # pragma: no cover
        return self._stream
