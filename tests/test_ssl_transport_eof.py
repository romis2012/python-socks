from __future__ import annotations

import ssl

import pytest
import trustme

from python_socks.sync.v2._ssl_transport import SSLTransport
from python_socks.sync.v2._stream import SyncSocketStream


class MemoryPeer:
    def __init__(
        self, context: ssl.SSLContext, *, payload: bytes = b"", clean: bool = False
    ) -> None:
        self.incoming = ssl.MemoryBIO()
        self.outgoing = ssl.MemoryBIO()
        self.sslobj = context.wrap_bio(self.incoming, self.outgoing, server_side=True)
        self.payload = payload
        self.clean = clean
        self.ready = False

    def sendall(self, data: bytes) -> None:
        if data:
            self.incoming.write(data)
        if self.ready:
            return
        try:
            self.sslobj.do_handshake()
        except ssl.SSLWantReadError:
            return
        self.ready = True
        if self.payload:
            self.sslobj.write(self.payload)
        if self.clean:
            try:
                self.sslobj.unwrap()
            except ssl.SSLWantReadError:
                pass

    def recv(self, size: int) -> bytes:
        return self.outgoing.read(size)

    def close(self) -> None:
        pass


@pytest.fixture
def contexts() -> tuple[ssl.SSLContext, ssl.SSLContext]:
    ca = trustme.CA()
    certificate = ca.issue_cert("localhost")
    server = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    certificate.configure_cert(server)
    client = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ca.configure_trust(client)
    return server, client


def make_transport(
    contexts: tuple[ssl.SSLContext, ssl.SSLContext],
    *,
    payload: bytes = b"",
    clean: bool = False,
    suppress: bool = True,
) -> SSLTransport:
    server, client = contexts
    peer = MemoryPeer(server, payload=payload, clean=clean)
    return SSLTransport(
        peer, client, server_hostname="localhost", suppress_ragged_eofs=suppress
    )


@pytest.mark.parametrize("clean", [False, True])
@pytest.mark.parametrize("method", ["read", "recv", "stream_read", "recv_into"])
def test_eof_result_types(
    contexts: tuple[ssl.SSLContext, ssl.SSLContext], clean: bool, method: str
) -> None:
    transport = make_transport(contexts, clean=clean)
    if method == "recv_into":
        assert transport.recv_into(bytearray(8)) == 0
    elif method == "stream_read":
        assert SyncSocketStream(transport).read(8) == b""
    else:
        assert getattr(transport, method)(8) == b""


@pytest.mark.parametrize("clean", [False, True])
@pytest.mark.parametrize("buffered", [False, True])
def test_payload_before_eof(
    contexts: tuple[ssl.SSLContext, ssl.SSLContext], clean: bool, buffered: bool
) -> None:
    transport = make_transport(contexts, payload=b"hello", clean=clean)
    if buffered:
        buffer = bytearray(8)
        assert transport.recv_into(buffer) == 5
        assert buffer[:5] == b"hello"
        assert transport.recv_into(buffer) == 0
    else:
        assert transport.recv(8) == b"hello"
        assert transport.recv(8) == b""


def test_strict_ragged_eof(
    contexts: tuple[ssl.SSLContext, ssl.SSLContext],
) -> None:
    transport = make_transport(contexts, suppress=False)
    with pytest.raises(ssl.SSLEOFError):
        transport.recv(8)
