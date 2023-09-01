import socket

from .. import _abc as abc
from .._protocols import socks5
from .._helpers import is_ip_address


class Socks5AsyncConnector:
    def __init__(
        self,
        username: str,
        password: str,
        rdns: bool,
        resolver: abc.AsyncResolver,
    ):
        self.username = username
        self.password = password
        self.rdns = rdns
        self.resolver = resolver

    async def connect(
        self,
        stream: abc.AsyncSocketStream,
        host: str,
        port: int,
    ) -> socks5.ConnectReply:
        conn = socks5.Connection()

        # Auth methods
        request = socks5.AuthMethodsRequest(
            username=self.username,
            password=self.password,
        )
        data = conn.send(request)
        await stream.write_all(data)

        data = await stream.read_exact(socks5.AuthMethodReply.SIZE)
        reply: socks5.AuthMethodReply = conn.receive(data)

        # Authenticate
        if reply.method == socks5.AuthMethod.USERNAME_PASSWORD:
            request = socks5.AuthRequest(
                username=self.username,
                password=self.password,
            )
            data = conn.send(request)
            await stream.write_all(data)

            data = await stream.read_exact(socks5.AuthReply.SIZE)
            _: socks5.AuthReply = conn.receive(data)

        # Connect
        if not is_ip_address(host) and not self.rdns:
            _, dest_host = await self.resolver.resolve(
                host,
                family=socket.AF_UNSPEC,
            )

        request = socks5.ConnectRequest(host=host, port=port)
        data = conn.send(request)
        await stream.write_all(data)

        data = await stream.read()
        reply: socks5.ConnectReply = conn.receive(data)
        return reply
