import trio

from ... import _abc as abc
from ..._errors import IncompleteReadError

DEFAULT_RECEIVE_SIZE = 65536


class TrioSocketStream(abc.AsyncSocketStream):
    def __init__(self, sock: trio.socket.SocketType) -> None:
        self._socket = sock

    async def write(self, data: bytes) -> None:
        total_sent = 0
        while total_sent < len(data):
            remaining = data[total_sent:]
            sent = await self._socket.send(remaining)
            total_sent += sent

    async def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        return await self._socket.recv(max_bytes)

    async def read_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = await self._socket.recv(n - len(data))
            if not packet:  # pragma: no cover
                raise IncompleteReadError("Connection closed unexpectedly")
            data.extend(packet)
        return data  # type:ignore[return-value]

    async def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
            await trio.lowlevel.checkpoint()
