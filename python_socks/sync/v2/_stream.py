from __future__ import annotations

import socket
import ssl
from typing import Union

from ... import _abc as abc
from ..._errors import IncompleteReadError
from ._ssl_transport import SSLTransport

DEFAULT_RECEIVE_SIZE = 65536

SocketType = Union[socket.socket, ssl.SSLSocket, SSLTransport]


class SyncSocketStream(abc.SyncSocketStream):
    def __init__(self, sock: SocketType) -> None:
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

    def start_tls(
        self,
        hostname: str,
        ssl_context: ssl.SSLContext,
    ) -> SyncSocketStream:
        ssl_socket: ssl.SSLSocket | SSLTransport

        if isinstance(self._socket, (ssl.SSLSocket, SSLTransport)):
            ssl_socket = SSLTransport(
                self._socket,
                ssl_context=ssl_context,
                server_hostname=hostname,
            )
        else:  # plain socket?
            ssl_socket = ssl_context.wrap_socket(
                self._socket,
                server_hostname=hostname,
            )

        return SyncSocketStream(ssl_socket)

    def close(self) -> None:
        self._socket.close()

    @property
    def socket(self) -> SocketType:  # pragma: nocover
        return self._socket
