import curio
import curio.io
import curio.socket

from ._resolver import Resolver
from ..._helpers import is_ipv4_address, is_ipv6_address


async def connect_tcp(
    host: str,
    port: int,
) -> curio.io.Socket:

    family, host = await _resolve_host(host=host)

    sock = curio.socket.socket(family=family, type=curio.socket.SOCK_STREAM)

    await sock.connect((host, port))
    return sock


async def _resolve_host(host):
    if is_ipv4_address(host):
        return curio.socket.AF_INET, host
    if is_ipv6_address(host):
        return curio.socket.AF_INET6, host

    resolver = Resolver()
    return await resolver.resolve(host=host)
