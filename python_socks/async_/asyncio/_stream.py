import asyncio
import socket

from ... import _abc as abc
from ..._errors import IncompleteReadError

DEFAULT_RECEIVE_SIZE = 65536


class AsyncioSocketStream(abc.AsyncSocketStream):
    def __init__(self, sock: socket.socket, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop
        self._socket = sock

    async def write(self, data: bytes) -> None:
        await self._loop.sock_sendall(self._socket, data)

    async def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        return await self._loop.sock_recv(self._socket, max_bytes)

    async def read_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = await self._loop.sock_recv(self._socket, n - len(data))
            if not packet:  # pragma: no cover
                raise IncompleteReadError("Connection closed unexpectedly")
            data.extend(packet)
        return data  # type:ignore[return-value]

    async def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
