from __future__ import annotations

import trio

from ..._helpers import is_ipv4_address, is_ipv6_address
from ..._types import ResolvedAddress
from ._resolver import Resolver


async def connect_tcp(
    host: str,
    port: int,
    local_addr: tuple[str, int] | None = None,
) -> trio.socket.SocketType:

    family, host = await _resolve_host(host)

    sock = trio.socket.socket(family=family, type=trio.socket.SOCK_STREAM)
    if local_addr is not None:  # pragma: no cover
        await sock.bind(local_addr)

    try:
        await sock.connect((host, port))
    except OSError:
        sock.close()
        raise
    return sock


async def _resolve_host(host: str) -> ResolvedAddress:
    if is_ipv4_address(host):
        return trio.socket.AF_INET, host
    if is_ipv6_address(host):
        return trio.socket.AF_INET6, host

    resolver = Resolver()
    return await resolver.resolve(host=host)
