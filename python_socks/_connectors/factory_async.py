from __future__ import annotations

from .._abc import AsyncResolver
from .._types import ProxyType
from .abc import AsyncConnector
from .http_async import HttpAsyncConnector
from .socks4_async import Socks4AsyncConnector
from .socks5_async import Socks5AsyncConnector


def create_connector(
    proxy_type: ProxyType,
    username: str | None,
    password: str | None,
    rdns: bool | None,  # noqa: FBT001
    resolver: AsyncResolver,
) -> AsyncConnector:
    if proxy_type == ProxyType.SOCKS4:
        return Socks4AsyncConnector(
            user_id=username,
            rdns=rdns,
            resolver=resolver,
        )

    if proxy_type == ProxyType.SOCKS5:
        return Socks5AsyncConnector(
            username=username,
            password=password,
            rdns=rdns,
            resolver=resolver,
        )

    if proxy_type == ProxyType.HTTP:
        return HttpAsyncConnector(
            username=username,
            password=password,
            resolver=resolver,
        )

    raise ValueError(f"Invalid proxy type: {proxy_type}")
