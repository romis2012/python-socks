import socket

import anyio
import anyio.abc

from ._resolver import Resolver
from ..._helpers import is_ipv4_address, is_ipv6_address


async def connect_tcp(
    host: str,
    port: int,
    local_host: str = None,
) -> anyio.abc.SocketStream:

    family, host = await _resolve_host(host)

    return await anyio.connect_tcp(
        remote_host=host,
        remote_port=port,
        local_host=local_host,
    )


async def _resolve_host(host):
    if is_ipv4_address(host):
        return socket.AF_INET, host
    if is_ipv6_address(host):
        return socket.AF_INET6, host

    resolver = Resolver()
    return await resolver.resolve(host=host)
