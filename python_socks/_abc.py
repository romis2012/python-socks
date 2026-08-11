from __future__ import annotations

import socket

from ._types import ResolvedAddress


class SyncResolver:
    def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> ResolvedAddress:
        raise NotImplementedError


class AsyncResolver:
    async def resolve(
        self,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> ResolvedAddress:
        raise NotImplementedError


class SyncSocketStream:
    def write(self, data: bytes) -> None:
        raise NotImplementedError

    def read(self, max_bytes: int = ...) -> bytes:
        raise NotImplementedError

    def read_exactly(self, n: int) -> bytes:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class AsyncSocketStream:
    async def write(self, data: bytes) -> None:
        raise NotImplementedError

    async def read(self, max_bytes: int = ...) -> bytes:
        raise NotImplementedError

    async def read_exactly(self, n: int) -> bytes:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError
