from __future__ import annotations

from .._abc import SyncResolver
from .._types import ProxyType
from .abc import SyncConnector
from .http_sync import HttpSyncConnector
from .socks4_sync import Socks4SyncConnector
from .socks5_sync import Socks5SyncConnector


def create_connector(
    proxy_type: ProxyType,
    username: str | None,
    password: str | None,
    rdns: bool | None,  # noqa: FBT001
    resolver: SyncResolver,
) -> SyncConnector:
    if proxy_type == ProxyType.SOCKS4:
        return Socks4SyncConnector(
            user_id=username,
            rdns=rdns,
            resolver=resolver,
        )

    if proxy_type == ProxyType.SOCKS5:
        return Socks5SyncConnector(
            username=username,
            password=password,
            rdns=rdns,
            resolver=resolver,
        )

    if proxy_type == ProxyType.HTTP:
        return HttpSyncConnector(
            username=username,
            password=password,
            resolver=resolver,
        )

    raise ValueError(f"Invalid proxy type: {proxy_type}")
