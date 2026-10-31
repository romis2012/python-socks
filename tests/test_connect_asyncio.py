from __future__ import annotations

import asyncio
import errno
import socket
from types import SimpleNamespace
from typing import Any

import pytest

from python_socks import ProxyConnectionError, ProxyTimeoutError, ProxyType
from python_socks.async_.asyncio import Proxy as AsyncioProxy
from python_socks.async_.asyncio import _connect as asyncio_connect


def socket_namespace(sock: Any) -> SimpleNamespace:
    return SimpleNamespace(
        AF_INET=socket.AF_INET,
        AF_INET6=socket.AF_INET6,
        SOCK_STREAM=socket.SOCK_STREAM,
        socket=lambda **_kwargs: sock,
    )


@pytest.mark.parametrize("cancel", (True, False))
@pytest.mark.asyncio
async def test_asyncio_interrupted_connection_closes_socket(
    monkeypatch: pytest.MonkeyPatch,
    cancel: bool,
) -> None:
    loop = asyncio.get_running_loop()
    started = asyncio.Event()
    sockets: list[socket.socket] = []

    async def connect(sock: socket.socket, address: tuple[str, int]) -> None:
        del address
        sockets.append(sock)
        started.set()
        await asyncio.Future()

    monkeypatch.setattr(loop, "sock_connect", connect)
    proxy = AsyncioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
    task = asyncio.create_task(
        proxy.connect("example.org", 443, timeout=60 if cancel else 0.01),
    )
    await started.wait()
    if cancel:
        task.cancel()
    try:
        with pytest.raises(asyncio.CancelledError if cancel else ProxyTimeoutError):
            await task
        assert len(sockets) == 1
        assert sockets[0].fileno() == -1
    finally:
        for sock in sockets:
            sock.close()


@pytest.mark.asyncio
async def test_asyncio_bind_failure_closes_socket(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with socket.socket() as listener, socket.socket() as sock:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        monkeypatch.setattr(asyncio_connect, "socket", socket_namespace(sock))
        proxy = AsyncioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
        with pytest.raises(ProxyConnectionError) as error:
            await proxy.connect("example.org", 443, local_addr=listener.getsockname())
        assert error.value.errno == errno.EADDRINUSE
        assert sock.fileno() == -1


@pytest.mark.asyncio
async def test_asyncio_success_keeps_returned_socket_open() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        host, port = listener.getsockname()
        sock = await asyncio_connect.connect_tcp(
            host,
            port,
            loop=asyncio.get_running_loop(),
        )
        try:
            assert sock.fileno() != -1
            with listener.accept()[0] as peer:
                await asyncio.get_running_loop().sock_sendall(sock, b"connected")
                assert peer.recv(9) == b"connected"
        finally:
            sock.close()
