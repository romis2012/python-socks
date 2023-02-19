from typing import Sequence
from ._proxy import TrioProxy


class ProxyChain:
    def __init__(self, proxies: Sequence[TrioProxy]):
        self._proxies = proxies

    async def connect(
        self,
        dest_host,
        dest_port,
        dest_ssl=None,
        timeout=None,
    ):
        forward = None
        for proxy in self._proxies:
            proxy._forward = forward
            forward = proxy

        return await forward.connect(
            dest_host=dest_host,
            dest_port=dest_port,
            dest_ssl=dest_ssl,
            timeout=timeout,
        )
