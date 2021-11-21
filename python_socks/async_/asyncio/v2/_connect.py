from typing import Optional, Tuple
import socket
import asyncio

from .._resolver import Resolver
from ...._helpers import is_ipv4_address, is_ipv6_address


async def connect_tcp(
    host: str,
    port: int,
    loop: asyncio.AbstractEventLoop,
    local_addr: Optional[Tuple[str, int]] = None,
) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:

    family, host = await _resolve_host(host, loop)

    kwargs = {}
    if local_addr is not None:
        kwargs['local_addr'] = local_addr   # pragma: no cover

    reader, writer = await asyncio.open_connection(
        host=host,
        port=port,
        family=family,
        **kwargs,
    )

    return reader, writer


async def _resolve_host(host, loop):
    if is_ipv4_address(host):
        return socket.AF_INET, host
    if is_ipv6_address(host):
        return socket.AF_INET6, host

    resolver = Resolver(loop=loop)
    return await resolver.resolve(host=host)
