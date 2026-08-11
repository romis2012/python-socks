import socket

from .. import _abc as abc
from .._errors import IncompleteReadError

DEFAULT_RECEIVE_SIZE = 65536


class SyncSocketStream(abc.SyncSocketStream):
    _socket: socket.socket

    def __init__(self, sock: socket.socket) -> None:
        self._socket = sock

    def write(self, data: bytes) -> None:
        self._socket.sendall(data)

    def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        return self._socket.recv(max_bytes)

    def read_exactly(self, n: int) -> bytes:
        data = bytearray()
        while len(data) < n:
            packet = self._socket.recv(n - len(data))
            if not packet:  # pragma: no cover
                raise IncompleteReadError("Connection closed unexpectedly")
            data.extend(packet)
        return data  # type:ignore[return-value]

    def close(self) -> None:
        if self._socket is not None:
            self._socket.close()
