import socket

import anyio

from ... import _abc as abc
from ..._types import ResolvedAddress


class Resolver(abc.AsyncResolver):
    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> ResolvedAddress:
        infos = await anyio.getaddrinfo(
            host=host,
            port=port,
            family=family,
            type=socket.SOCK_STREAM,
        )

        if not infos:  # pragma: no cover
            raise OSError(f"Can`t resolve address {host}:{port} [{family}]")

        infos = sorted(infos, key=lambda info: info[0])

        family, _, _, _, address = infos[0]
        return family, address[0]
