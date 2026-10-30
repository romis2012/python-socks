from __future__ import annotations

import errno
import socket
from types import SimpleNamespace
from typing import Any

import pytest

from python_socks import ProxyConnectionError, ProxyType

trio = pytest.importorskip("trio")
from python_socks.async_.trio import Proxy as TrioProxy
from python_socks.async_.trio import _connect as trio_connect


def socket_namespace(sock: Any) -> SimpleNamespace:
    return SimpleNamespace(
        AF_INET=socket.AF_INET,
        AF_INET6=socket.AF_INET6,
        SOCK_STREAM=socket.SOCK_STREAM,
        socket=lambda **_kwargs: sock,
    )


@pytest.mark.parametrize("during_bind", (True, False))
@pytest.mark.trio
async def test_trio_interrupted_connection_closes_socket(
    monkeypatch: pytest.MonkeyPatch,
    during_bind: bool,
) -> None:
    sock = trio.socket.socket()

    async def blocked(_address: tuple[str, int]) -> None:
        await trio.sleep_forever()

    monkeypatch.setattr(sock, "bind" if during_bind else "connect", blocked)
    monkeypatch.setattr(
        trio_connect,
        "trio",
        SimpleNamespace(socket=socket_namespace(sock)),
    )
    try:
        with trio.CancelScope() as scope:
            scope.cancel()
            await trio_connect.connect_tcp(
                "127.0.0.1",
                1080,
                local_addr=("127.0.0.1", 0) if during_bind else None,
            )
        assert scope.cancelled_caught
        assert sock.fileno() == -1
    finally:
        sock.close()


@pytest.mark.trio
async def test_trio_bind_failure_closes_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    sock = trio.socket.socket()
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        monkeypatch.setattr(
            trio_connect,
            "trio",
            SimpleNamespace(socket=socket_namespace(sock)),
        )
        proxy = TrioProxy(ProxyType.SOCKS5, "127.0.0.1", 1080)
        try:
            with pytest.raises(ProxyConnectionError) as error:
                await proxy.connect(
                    "example.org", 443, local_addr=listener.getsockname()
                )
            assert error.value.errno == errno.EADDRINUSE
            assert sock.fileno() == -1
        finally:
            sock.close()


@pytest.mark.trio
async def test_trio_success_keeps_returned_socket_open() -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        sock = await trio_connect.connect_tcp(*listener.getsockname())
        try:
            assert sock.fileno() != -1
            with listener.accept()[0] as peer:
                await sock.send(b"connected")
                assert peer.recv(9) == b"connected"
        finally:
            sock.close()
