from __future__ import annotations

import ssl
from collections.abc import Iterable

from ._proxy import SyncProxy
from ._stream import SyncSocketStream


class ProxyChain:
    def __init__(self, proxies: Iterable[SyncProxy]) -> None:
        self._proxies = proxies

    def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        timeout: float | None = None,
    ) -> SyncSocketStream:
        forward = None
        for proxy in self._proxies:
            proxy._forward = forward  # noqa: SLF001
            forward = proxy

        assert forward is not None

        return forward.connect(
            dest_host=dest_host,
            dest_port=dest_port,
            dest_ssl=dest_ssl,
            timeout=timeout,
        )
