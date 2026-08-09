from __future__ import annotations

import socket

from ._stream import SyncSocketStream


def connect_tcp(
    host: str,
    port: int,
    timeout: float | None = None,
    local_addr: tuple[str, int] | None = None,
) -> SyncSocketStream:
    address = (host, port)
    sock = socket.create_connection(
        address,
        timeout,
        source_address=local_addr,
    )

    return SyncSocketStream(sock)
