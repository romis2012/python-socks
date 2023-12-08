import socket

from .._abc import AsyncSocketStream, AsyncResolver
from .abc import AsyncConnector

from .._protocols import socks5
from .._helpers import is_ip_address


class Socks5AsyncConnector(AsyncConnector):
    def __init__(
        self,
        username: str,
        password: str,
        rdns: bool,
        resolver: AsyncResolver,
    ):
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
        await stream.write_all(data)

        data = await stream.read_exact(socks5.AuthMethodReply.SIZE)
        reply: socks5.AuthMethodReply = conn.receive(data)

        # Authenticate
        if reply.method == socks5.AuthMethod.USERNAME_PASSWORD:
            request = socks5.AuthRequest(
                username=self._username,
                password=self._password,
            )
            data = conn.send(request)
            await stream.write_all(data)

            data = await stream.read_exact(socks5.AuthReply.SIZE)
            _: socks5.AuthReply = conn.receive(data)

        # Connect
        if not is_ip_address(host) and not self._rdns:
            _, host = await self._resolver.resolve(
                host,
                family=socket.AF_UNSPEC,
            )

        request = socks5.ConnectRequest(host=host, port=port)
        data = conn.send(request)
        await stream.write_all(data)

        data = await stream.read()
        reply: socks5.ConnectReply = conn.receive(data)
        return reply
