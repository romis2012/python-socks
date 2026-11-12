from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import anyio
import pytest

from python_socks import ProxyError, ProxyType
from python_socks._errors import IncompleteReadError
from python_socks._protocols.errors import ReplyError
from python_socks.async_.anyio import Proxy as AnyioProxy
from python_socks.async_.asyncio.v2 import Proxy as AsyncioProxy
from python_socks.async_.asyncio.v2._stream import AsyncioSocketStream

TRUNCATED_REPLIES = [
    pytest.param(b"", id="auth-method"),
    pytest.param(b"\x05\x02\x01", id="password-auth"),
    pytest.param(b"\x05\x00\x05\x00", id="connect-header"),
    pytest.param(b"\x05\x00\x05\x00\x00\x01\x7f", id="connect-address"),
]
PAYLOAD = b"tunnel payload"
SUCCESS = b"\x05\x00\x05\x00\x00\x01\x7f\x00\x00\x01\x00\x50"
CONTROL_REPLIES = [
    pytest.param(SUCCESS + PAYLOAD, False, id="success"),
    pytest.param(b"\x04\x00", True, id="invalid-auth-version"),
    pytest.param(b"\x05\x00\x05\x05\x00", True, id="connection-refused"),
]


def make_anyio_stream(reply: bytes) -> Mock:
    data = bytearray(reply)

    async def receive(max_bytes: int) -> bytes:
        if not data:
            raise anyio.EndOfStream
        packet = bytes(data[:max_bytes])
        del data[:max_bytes]
        return packet

    stream = Mock(spec=anyio.abc.SocketStream)
    stream.receive = AsyncMock(side_effect=receive)
    stream.send = AsyncMock()
    stream.aclose = AsyncMock()
    return stream


def make_asyncio_stream(
    reply: bytes, *, eof: bool = True
) -> tuple[AsyncioSocketStream, Mock]:
    reader = asyncio.StreamReader()
    reader.feed_data(reply)
    if eof:
        reader.feed_eof()
    writer = Mock(spec=asyncio.StreamWriter)
    writer.drain = AsyncMock()
    writer.wait_closed = AsyncMock()
    writer.transport = Mock(spec=asyncio.Transport)
    stream = AsyncioSocketStream(asyncio.get_running_loop(), reader, writer)
    return stream, writer


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
@pytest.mark.parametrize("reply", TRUNCATED_REPLIES)
def test_anyio_truncated_reply(backend: str, reply: bytes) -> None:
    async def run() -> None:
        stream = make_anyio_stream(reply)
        proxy = AnyioProxy(
            ProxyType.SOCKS5,
            "127.0.0.1",
            1080,
            username="user",
            password="password",  # noqa: S106
        )
        with patch(
            "python_socks.async_.anyio._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            try:
                with pytest.raises(ProxyError) as exc_info:
                    await proxy.connect("127.0.0.1", 80)
                assert isinstance(exc_info.value.__cause__, IncompleteReadError)
                assert exc_info.value.error_code is None
                stream.aclose.assert_awaited_once()
            finally:
                if not stream.aclose.await_count:
                    await stream.aclose()

    anyio.run(run, backend=backend)


@pytest.mark.parametrize("reply", TRUNCATED_REPLIES)
def test_asyncio_v2_truncated_reply(reply: bytes) -> None:
    async def run() -> None:
        stream, writer = make_asyncio_stream(reply)
        proxy = AsyncioProxy(
            ProxyType.SOCKS5,
            "127.0.0.1",
            1080,
            username="user",
            password="password",  # noqa: S106
        )
        with patch(
            "python_socks.async_.asyncio.v2._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            try:
                with pytest.raises(ProxyError) as exc_info:
                    await proxy.connect("127.0.0.1", 80)
                assert isinstance(exc_info.value.__cause__, asyncio.IncompleteReadError)
                assert exc_info.value.error_code is None
                writer.close.assert_called_once()
                writer.wait_closed.assert_awaited_once()
                writer.transport.abort.assert_called_once()
            finally:
                if not writer.close.call_count:
                    await stream.close()

    asyncio.run(run())


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
@pytest.mark.parametrize(("reply", "error"), CONTROL_REPLIES)
def test_anyio_reply_controls(backend: str, reply: bytes, error: bool) -> None:
    async def run() -> None:
        stream = make_anyio_stream(reply)
        proxy = AnyioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
        with patch(
            "python_socks.async_.anyio._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            try:
                if error:
                    with pytest.raises(ProxyError) as exc_info:
                        await proxy.connect("127.0.0.1", 80)
                    assert isinstance(exc_info.value.__cause__, ReplyError)
                    stream.aclose.assert_awaited_once()
                else:
                    assert await proxy.connect("127.0.0.1", 80) is stream
                    stream.aclose.assert_not_awaited()
                    assert await stream.receive(1024) == PAYLOAD
            finally:
                if not stream.aclose.await_count:
                    await stream.aclose()

    anyio.run(run, backend=backend)


@pytest.mark.parametrize(("reply", "error"), CONTROL_REPLIES)
def test_asyncio_v2_reply_controls(reply: bytes, error: bool) -> None:
    async def run() -> None:
        stream, writer = make_asyncio_stream(reply)
        proxy = AsyncioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
        with patch(
            "python_socks.async_.asyncio.v2._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            try:
                if error:
                    with pytest.raises(ProxyError) as exc_info:
                        await proxy.connect("127.0.0.1", 80)
                    assert isinstance(exc_info.value.__cause__, ReplyError)
                    writer.close.assert_called_once()
                    writer.wait_closed.assert_awaited_once()
                    writer.transport.abort.assert_called_once()
                else:
                    assert await proxy.connect("127.0.0.1", 80) is stream
                    writer.close.assert_not_called()
                    assert await stream.read() == PAYLOAD
            finally:
                if not writer.close.call_count:
                    await stream.close()

    asyncio.run(run())


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_anyio_cancellation_closes_stream(backend: str) -> None:
    async def run() -> None:
        stream = make_anyio_stream(b"")
        reading = anyio.Event()
        cancelled: list[bool] = []

        async def receive(max_bytes: int) -> bytes:
            assert max_bytes > 0
            reading.set()
            await anyio.sleep_forever()
            raise AssertionError("Cancelled receive must not return")

        stream.receive = AsyncMock(side_effect=receive)
        proxy = AnyioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)

        async def connect() -> None:
            try:
                await proxy.connect("127.0.0.1", 80)
            except anyio.get_cancelled_exc_class():
                cancelled.append(True)
                raise
            else:
                raise AssertionError("Cancellation must propagate")

        with patch(
            "python_socks.async_.anyio._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            async with anyio.create_task_group() as group:
                group.start_soon(connect)
                await reading.wait()
                group.cancel_scope.cancel()
        assert cancelled == [True]
        stream.aclose.assert_awaited_once()

    anyio.run(run, backend=backend)


def test_asyncio_v2_cancellation_closes_stream() -> None:
    async def run() -> None:
        stream, writer = make_asyncio_stream(b"", eof=False)
        reading = asyncio.Event()
        readexactly = stream.reader.readexactly

        async def read(n: int) -> bytes:
            reading.set()
            return await readexactly(n)

        proxy = AsyncioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
        with (
            patch(
                "python_socks.async_.asyncio.v2._proxy.connect_tcp",
                new=AsyncMock(return_value=stream),
            ),
            patch.object(stream.reader, "readexactly", new=read),
        ):
            task = asyncio.create_task(proxy.connect("127.0.0.1", 80))
            try:
                await asyncio.wait_for(reading.wait(), timeout=1)
                task.cancel("test cancellation")
                with pytest.raises(asyncio.CancelledError) as exc_info:
                    await task
                assert exc_info.value.args == ("test cancellation",)
            finally:
                if not task.done():
                    task.cancel()
                    with pytest.raises(asyncio.CancelledError):
                        await task
        writer.close.assert_called_once()
        writer.wait_closed.assert_awaited_once()
        writer.transport.abort.assert_called_once()

    asyncio.run(run())


@pytest.mark.parametrize("backend", ["asyncio", "trio"])
def test_anyio_eof_cleanup_is_shielded(backend: str) -> None:
    async def run() -> None:
        stream = make_anyio_stream(b"")
        closing = anyio.Event()
        release_close = anyio.Event()
        finished = anyio.Event()
        scopes: list[anyio.CancelScope] = []
        errors: list[BaseException] = []
        closed = False

        async def aclose() -> None:
            nonlocal closed
            closing.set()
            await release_close.wait()
            closed = True

        stream.aclose = AsyncMock(side_effect=aclose)
        proxy = AnyioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)

        async def connect() -> None:
            with anyio.CancelScope() as scope:
                scopes.append(scope)
                try:
                    await proxy.connect("127.0.0.1", 80)
                except (ProxyError, anyio.get_cancelled_exc_class()) as error:
                    errors.append(error)
                finally:
                    finished.set()

        with patch(
            "python_socks.async_.anyio._proxy.connect_tcp",
            new=AsyncMock(return_value=stream),
        ):
            try:
                async with anyio.create_task_group() as group:
                    group.start_soon(connect)
                    try:
                        with anyio.fail_after(2):
                            await closing.wait()
                            scopes[0].cancel()
                            release_close.set()
                            await finished.wait()
                    finally:
                        release_close.set()
                assert closed
                assert len(errors) == 1
                assert isinstance(errors[0], ProxyError)
                assert isinstance(errors[0].__cause__, IncompleteReadError)
                stream.aclose.assert_awaited_once()
            finally:
                if not closed:
                    await stream.aclose()

    anyio.run(run, backend=backend)
