from typing import Iterable
from ._proxy import SyncProxy


class ProxyChain:
    def __init__(self, proxies: Iterable[SyncProxy]):
        self._proxies = proxies

    def connect(self, dest_host, dest_port, dest_ssl=None,  timeout=None,):
        stream = None
        proxies = list(self._proxies)

        length = len(proxies) - 1
        for i in range(length):
            stream = proxies[i].connect(
                dest_host=proxies[i + 1].proxy_host,
                dest_port=proxies[i + 1].proxy_port,
                timeout=timeout,
                _stream=stream
            )

        stream = proxies[length].connect(
            dest_host=dest_host,
            dest_port=dest_port,
            dest_ssl=dest_ssl,
            timeout=timeout,
            _stream=stream
        )

        return stream
