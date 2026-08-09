from __future__ import annotations

import warnings
from collections.abc import Iterable
from typing import Any


class ProxyChain:
    def __init__(self, proxies: Iterable[Any]) -> None:
        warnings.warn(
            "This implementation of ProxyChain is deprecated "
            "and will be removed in the future",
            DeprecationWarning,
            stacklevel=2,
        )
        self._proxies = proxies

    async def connect(
        self, dest_host: str, dest_port: int, timeout: float | None = None
    ) -> Any:
        curr_socket = None
        proxies = list(self._proxies)

        length = len(proxies) - 1
        for i in range(length):
            curr_socket = await proxies[i].connect(
                dest_host=proxies[i + 1].proxy_host,
                dest_port=proxies[i + 1].proxy_port,
                timeout=timeout,
                _socket=curr_socket,
            )

        curr_socket = await proxies[length].connect(
            dest_host=dest_host,
            dest_port=dest_port,
            timeout=timeout,
            _socket=curr_socket,
        )

        return curr_socket
