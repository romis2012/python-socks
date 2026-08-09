from __future__ import annotations

import ssl
import warnings
from collections.abc import Iterable

from ._proxy import AnyioProxy
from ._stream import AnyioSocketStream


class ProxyChain:
    def __init__(self, proxies: Iterable[AnyioProxy]) -> None:
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
        _stream = None
        proxies = list(self._proxies)

        length = len(proxies) - 1
        for i in range(length):
            _stream = await proxies[i].connect(
                dest_host=proxies[i + 1].proxy_host,
                dest_port=proxies[i + 1].proxy_port,
                timeout=timeout,
                _stream=_stream,
            )

        _stream = await proxies[length].connect(
            dest_host=dest_host,
            dest_port=dest_port,
            dest_ssl=dest_ssl,
            timeout=timeout,
            _stream=_stream,
        )

        return _stream
