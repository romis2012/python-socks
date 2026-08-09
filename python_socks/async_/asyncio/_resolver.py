import asyncio
import socket

from ... import _abc as abc
from ..._types import ResolvedAddress


class Resolver(abc.AsyncResolver):
    def __init__(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> ResolvedAddress:
        infos = await self._loop.getaddrinfo(
            host=host,
            port=port,
            family=family,
            type=socket.SOCK_STREAM,
        )

        if not infos:  # pragma: no cover
            raise OSError(f"Can`t resolve address {host}:{port} [{family}]")

        # use IPv4 address first
        infos = sorted(infos, key=lambda info: info[0])

        family, _, _, _, address = infos[0]
        return family, address[0]  # type:ignore[return-value]
