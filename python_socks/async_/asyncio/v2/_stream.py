from __future__ import annotations

import asyncio
import ssl

from .... import _abc as abc

DEFAULT_RECEIVE_SIZE = 65536


class AsyncioSocketStream(abc.AsyncSocketStream):
    def __init__(
        self,
        loop: asyncio.AbstractEventLoop,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        self._loop = loop
        self._reader = reader
        self._writer = writer

    async def write(self, data: bytes) -> None:
        self._writer.write(data)
        await self._writer.drain()

    async def read(self, max_bytes: int = DEFAULT_RECEIVE_SIZE) -> bytes:
        return await self._reader.read(max_bytes)

    async def read_exactly(self, n: int) -> bytes:
        return await self._reader.readexactly(n)

    async def start_tls(
        self,
        hostname: str,
        ssl_context: ssl.SSLContext,
        ssl_handshake_timeout: float | None = None,
    ) -> AsyncioSocketStream:
        if hasattr(self._writer, "start_tls"):  # Python>=3.11
            await self._writer.start_tls(
                ssl_context,
                server_hostname=hostname,
                ssl_handshake_timeout=ssl_handshake_timeout,
            )
            return self

        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)

        transport: asyncio.Transport = await self._loop.start_tls(
            self._writer.transport,  # type: ignore[assignment]
            protocol,
            ssl_context,
            server_side=False,
            server_hostname=hostname,
            ssl_handshake_timeout=ssl_handshake_timeout,
        )

        # reader.set_transport(transport)

        # Initialize the protocol, so it is made aware of being tied to
        # a TLS connection.
        # See also: https://github.com/encode/httpx/issues/859
        protocol.connection_made(transport)

        writer = asyncio.StreamWriter(
            transport=transport,
            protocol=protocol,
            reader=reader,
            loop=self._loop,
        )

        stream = AsyncioSocketStream(loop=self._loop, reader=reader, writer=writer)
        # When we return a new SocketStream with new StreamReader/StreamWriter instances
        # we need to keep references to the old StreamReader/StreamWriter so that they
        # are not garbage collected and closed while we're still using them.
        stream._inner = self  # type: ignore[attr-defined]
        return stream

    async def close(self) -> None:
        self._writer.close()
        self._writer.transport.abort()

    @property
    def reader(self) -> asyncio.StreamReader:
        return self._reader  # pragma: no cover

    @property
    def writer(self) -> asyncio.StreamWriter:
        return self._writer  # pragma: no cover
