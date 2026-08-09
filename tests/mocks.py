from __future__ import annotations

import socket
from collections.abc import Awaitable, Callable
from typing import Any

from python_socks._abc import AsyncResolver, SyncResolver
from tests.config import (
    PROXY_HOST_NAME_IPV4,
    PROXY_HOST_NAME_IPV6,
    TEST_HOST_NAME_IPV4,
    TEST_HOST_NAME_IPV6,
)

AddrInfo = list[
    tuple[
        socket.AddressFamily,  # family (e.g., AF_INET, AF_INET6)
        socket.SocketKind,  # socktype (e.g., SOCK_STREAM, SOCK_DGRAM)
        int,  # proto (protocol number, e.g., 6 for TCP)
        str,  # canonname (canonical name)
        # Union[  # sockaddr
        #     tuple[str, int],  # IPv4 tuple
        #     tuple[str, int, int, int],  # IPv6 tuple
        #     tuple[int, bytes],  # Raw address fallback (CPython built without IPv6)
        # ],
        tuple[Any, ...],
    ]
]


def getaddrinfo_sync_mock() -> Callable[..., AddrInfo]:
    _orig_getaddrinfo = socket.getaddrinfo

    def getaddrinfo(
        host: str,
        port: int,
        family: int | socket.AddressFamily = 0,
        type: int | socket.SocketKind = 0,  # noqa: A002
        proto: int = 0,
        flags: int = 0,
    ) -> AddrInfo:
        if host in (TEST_HOST_NAME_IPV4, PROXY_HOST_NAME_IPV4):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

        if host in (TEST_HOST_NAME_IPV6, PROXY_HOST_NAME_IPV6):
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port, 0, 0))]

        return _orig_getaddrinfo(host, port, family, type, proto, flags)

    return getaddrinfo


def getaddrinfo_async_mock(
    origin_getaddrinfo: Callable[..., Awaitable[AddrInfo]],
) -> Callable[..., Awaitable[AddrInfo]]:
    async def getaddrinfo(
        host: str,
        port: int,
        family: int | socket.AddressFamily = 0,
        type: int | socket.SocketKind = 0,  # noqa: A002
        proto: int = 0,
        flags: int = 0,
    ) -> AddrInfo:
        if host in (TEST_HOST_NAME_IPV4, PROXY_HOST_NAME_IPV4):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

        if host in (TEST_HOST_NAME_IPV6, PROXY_HOST_NAME_IPV6):
            return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port, 0, 0))]

        return await origin_getaddrinfo(
            host,
            port,
            family=family,
            type=type,
            proto=proto,
            flags=flags,
        )

    return getaddrinfo


def _resolve_local(host: str) -> tuple[socket.AddressFamily, str] | None:
    if host in (TEST_HOST_NAME_IPV4, PROXY_HOST_NAME_IPV4):
        return socket.AF_INET, "127.0.0.1"

    if host in (TEST_HOST_NAME_IPV6, PROXY_HOST_NAME_IPV6):
        return socket.AF_INET6, "::1"

    return None


def sync_resolve_factory(
    cls: type[SyncResolver],
) -> Callable[..., tuple[socket.AddressFamily, str]]:
    original_resolve = cls.resolve

    def new_resolve(
        self: SyncResolver,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> tuple[socket.AddressFamily, str]:
        res = _resolve_local(host)

        if res is not None:
            return res

        return original_resolve(self, host=host, port=port, family=family)

    return new_resolve


def async_resolve_factory(
    cls: type[AsyncResolver],
) -> Callable[..., Awaitable[tuple[socket.AddressFamily, str]]]:
    original_resolve = cls.resolve

    async def new_resolve(
        self: Any,
        host: str,
        port: int = 0,
        family: socket.AddressFamily = socket.AF_UNSPEC,
    ) -> tuple[socket.AddressFamily, str]:
        res = _resolve_local(host)

        if res is not None:
            return res

        return await original_resolve(self, host=host, port=port, family=family)

    return new_resolve
