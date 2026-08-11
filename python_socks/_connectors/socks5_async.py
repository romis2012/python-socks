from __future__ import annotations

import socket

from .._abc import AsyncResolver, AsyncSocketStream
from .._helpers import is_ip_address
from .._protocols import socks5
from .abc import AsyncConnector


class Socks5AsyncConnector(AsyncConnector):
    def __init__(
        self,
        username: str | None,
        password: str | None,
        rdns: bool | None,  # noqa: FBT001
        resolver: AsyncResolver,
    ) -> None:
        if rdns is None:
            rdns = True

        self._username = username
        self._password = password
        self._rdns = rdns
        self._resolver = resolver

    async def connect(
        self,
        stream: AsyncSocketStream,
        host: str,
        port: int,
    ) -> socks5.ConnectReply:
        conn = socks5.Connection()

        # Auth methods
        request = socks5.AuthMethodsRequest(
            username=self._username,
            password=self._password,
        )
        data = conn.send(request)
        await stream.write(data)

        data = await stream.read_exactly(socks5.AuthMethodReply.SIZE)
        reply: socks5.AuthMethodReply = conn.receive(data)  # type:ignore[assignment]

        # Authenticate
        if reply.method == socks5.AuthMethod.USERNAME_PASSWORD:
            assert self._username is not None
            assert self._password is not None

            request = socks5.AuthRequest(  # type:ignore[assignment]
                username=self._username,
                password=self._password,
            )
            data = conn.send(request)
            await stream.write(data)

            data = await stream.read_exactly(socks5.AuthReply.SIZE)
            _: socks5.AuthReply = conn.receive(data)  # type:ignore[assignment]

        # Connect
        if not is_ip_address(host) and not self._rdns:
            _family, host = await self._resolver.resolve(
                host,
                family=socket.AF_UNSPEC,
            )

        request = socks5.ConnectRequest(host=host, port=port)
        data = conn.send(request)
        await stream.write(data)

        data = await self._read_reply(stream)
        reply: socks5.ConnectReply = conn.receive(data)  # type:ignore[assignment]
        return reply  # type:ignore[return-value]

    # noinspection PyMethodMayBeStatic
    async def _read_reply(self, stream: AsyncSocketStream) -> bytes:
        data = await stream.read_exactly(3)
        if data[0] != socks5.SOCKS_VER:
            return data
        if data[1] != socks5.ReplyCode.SUCCEEDED:
            return data
        if data[2] != socks5.RSV:
            return data

        data += await stream.read_exactly(1)
        addr_type = data[3]

        if addr_type == socks5.AddressType.IPV4:
            data += await stream.read_exactly(6)
        elif addr_type == socks5.AddressType.IPV6:
            data += await stream.read_exactly(18)
        elif addr_type == socks5.AddressType.DOMAIN:
            data += await stream.read_exactly(1)
            host_len = data[-1]
            data += await stream.read_exactly(host_len + 2)

        return data
