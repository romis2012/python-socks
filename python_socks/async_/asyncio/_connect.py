from __future__ import annotations

import asyncio
import socket

from ..._helpers import is_ipv4_address, is_ipv6_address
from ..._types import ResolvedAddress
from ._resolver import Resolver


async def connect_tcp(
    host: str,
    port: int,
    loop: asyncio.AbstractEventLoop,
    local_addr: tuple[str, int] | None = None,
) -> socket.socket:

    family, host = await _resolve_host(host, loop)

    sock = socket.socket(family=family, type=socket.SOCK_STREAM)
    sock.setblocking(False)  # noqa: FBT003
    if local_addr is not None:  # pragma: no cover
        sock.bind(local_addr)

    if is_ipv6_address(host):  # noqa: SIM108
        address = (host, port, 0, 0)  # to fix OSError: [WinError 10022]
    else:
        address = (host, port)  # type: ignore[assignment]

    try:
        await loop.sock_connect(sock=sock, address=address)
    except OSError:
        sock.close()
        raise
    return sock


async def _resolve_host(
    host: str,
    loop: asyncio.AbstractEventLoop,
) -> ResolvedAddress:
    if is_ipv4_address(host):
        return socket.AF_INET, host
    if is_ipv6_address(host):
        return socket.AF_INET6, host

    resolver = Resolver(loop=loop)
    return await resolver.resolve(host=host)
