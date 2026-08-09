from __future__ import annotations

import ssl
import warnings
from collections.abc import Sequence

from ._proxy import AnyioProxy
from ._stream import AnyioSocketStream


class ProxyChain:
    def __init__(self, proxies: Sequence[AnyioProxy]) -> None:
        warnings.warn(
            "This implementation of ProxyChain is deprecated "
            "and will be removed in the future",
            DeprecationWarning,
            stacklevel=2,
        )
        self._proxies = proxies

    async def connect(
        self,
        dest_host: str,
        dest_port: int,
        dest_ssl: ssl.SSLContext | None = None,
        timeout: float | None = None,
    ) -> AnyioSocketStream:
        forward = None
        for proxy in self._proxies:
            proxy._forward = forward  # noqa: SLF001
            forward = proxy

        assert forward is not None

        return await forward.connect(
            dest_host=dest_host,
            dest_port=dest_port,
            dest_ssl=dest_ssl,
            timeout=timeout,
        )
