from __future__ import annotations

import socket


def connect_tcp(
    host: str,
    port: int,
    timeout: float | None = None,
    local_addr: tuple[str, int] | None = None,
) -> socket.socket:
    address = (host, port)
    return socket.create_connection(
        address,
        timeout,
        source_address=local_addr,
    )
