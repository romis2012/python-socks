from __future__ import annotations

import io
from unittest.mock import AsyncMock, Mock

import pytest

from python_socks._abc import AsyncSocketStream, SyncSocketStream
from python_socks._connectors.http_async import HttpAsyncConnector
from python_socks._connectors.http_sync import HttpSyncConnector
from python_socks._errors import IncompleteReadError
from python_socks._protocols.errors import ReplyError

HEADER = b"HTTP/1.1 200 Connection established\r\nX-Proxy: test\r\n\r\n"
PAYLOAD = b"\x00\xfftunnel\r\n\r\ndata"
LIMIT_HEADER = b"HTTP/1.1 200 OK\r\nX: " + b"x" * (65536 - 24) + b"\r\n\r\n"
REPLIES = (
    pytest.param(HEADER, 65536, b"", None, id="complete"),
    pytest.param(HEADER + PAYLOAD, 9, PAYLOAD, None, id="split-status"),
    pytest.param(HEADER + PAYLOAD, 40, PAYLOAD, None, id="split-headers"),
    pytest.param(HEADER + PAYLOAD, 65536, PAYLOAD, None, id="coalesced-payload"),
    pytest.param(HEADER[:-2], 65536, b"", IncompleteReadError, id="incomplete-headers"),
    pytest.param(HEADER[:-4] + b"x" * 65536, 65536, b"", ReplyError, id="oversized"),
    pytest.param(LIMIT_HEADER + PAYLOAD, 65536, PAYLOAD, None, id="limit-boundary"),
)


def read_exactly(buffer: io.BytesIO, size: int) -> bytes:
    data = buffer.read(size)
    if len(data) != size:
        raise IncompleteReadError("Connection closed unexpectedly")
    return data


@pytest.mark.parametrize(("reply", "read_size", "payload", "error"), REPLIES)
def test_sync_http_reply_framing(
    reply: bytes, read_size: int, payload: bytes, error: type[Exception] | None
) -> None:
    buffer = io.BytesIO(reply)
    stream = Mock(spec=SyncSocketStream)
    stream.read.side_effect = lambda: buffer.read(read_size)
    stream.read_exactly.side_effect = lambda size: read_exactly(buffer, size)
    connector = HttpSyncConnector(username=None, password=None, resolver=Mock())

    if error:
        with pytest.raises(error):
            connector.connect(stream, "example.com", 443)
    else:
        response = connector.connect(stream, "example.com", 443)
        assert response.status_code == 200
        assert buffer.read() == payload


@pytest.mark.parametrize(("reply", "read_size", "payload", "error"), REPLIES)
@pytest.mark.asyncio
async def test_async_http_reply_framing(
    reply: bytes, read_size: int, payload: bytes, error: type[Exception] | None
) -> None:
    buffer = io.BytesIO(reply)
    stream = Mock(spec=AsyncSocketStream)
    stream.write = AsyncMock()
    stream.read = AsyncMock(side_effect=lambda: buffer.read(read_size))
    stream.read_exactly = AsyncMock(side_effect=lambda size: read_exactly(buffer, size))
    connector = HttpAsyncConnector(username=None, password=None, resolver=Mock())

    if error:
        with pytest.raises(error):
            await connector.connect(stream, "example.com", 443)
    else:
        response = await connector.connect(stream, "example.com", 443)
        assert response.status_code == 200
        assert buffer.read() == payload
