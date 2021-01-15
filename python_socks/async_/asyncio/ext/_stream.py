import asyncio
import socket

from ...._resolver_async_aio import Resolver
from ...._helpers import is_ipv4_address, is_ipv6_address

DEFAULT_RECEIVE_SIZE = 65536


class AsyncioAwareStream:
    _loop: asyncio.AbstractEventLoop = None
    _reader: asyncio.StreamReader = None
    _writer: asyncio.StreamWriter = None

    def __init__(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop
        self._resolver = Resolver(loop=loop)

    async def open_connection(self, host, port):
        family, host = await self._resolve(host=host)

        self._reader, self._writer = await asyncio.open_connection(
            host=host,
            port=port,
        )

    async def close(self):
        if self._writer is not None:
            self._writer.close()

    async def write_all(self, data):
        self._writer.write(data)

    async def read(self, max_bytes=DEFAULT_RECEIVE_SIZE):
        return await self._reader.read(max_bytes)

    async def read_exact(self, n):
        return await self._reader.readexactly(n)

    async def start_tls(self, hostname, ssl_context):
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        transport = await self._loop.start_tls(
            self._writer.transport,
            protocol,
            ssl_context,
            server_side=False,
            server_hostname=hostname
        )

        reader.set_transport(transport)
        writer = asyncio.StreamWriter(
            transport=transport,
            protocol=protocol,
            reader=reader,
            loop=self._loop
        )

        self._reader = reader
        self._writer = writer

    @property
    def reader(self):
        return self._reader

    @property
    def writer(self):
        return self._writer

    @property
    def resolver(self):
        return self._resolver

    async def _resolve(self, host):
        if is_ipv4_address(host):
            return socket.AF_INET, host
        if is_ipv6_address(host):
            return socket.AF_INET6, host
        return await self._resolver.resolve(host=host)
