from ...._helpers import parse_proxy_url
from ...._types import ProxyType
from ._proxy import Socks5Proxy, Socks4Proxy, HttpProxy, BaseProxy


class Proxy:
    @classmethod
    def create(cls, proxy_type: ProxyType, host: str, port: int,
               username: str = None, password: str = None,
               rdns: bool = None,
               **kwargs) -> BaseProxy:

        if proxy_type == ProxyType.SOCKS4:
            return Socks4Proxy(
                proxy_host=host,
                proxy_port=port,
                user_id=username,
                rdns=rdns,
                **kwargs
            )

        if proxy_type == ProxyType.SOCKS5:
            return Socks5Proxy(
                proxy_host=host,
                proxy_port=port,
                username=username,
                password=password,
                rdns=rdns,
                **kwargs
            )

        if proxy_type == ProxyType.HTTP:
            return HttpProxy(
                proxy_host=host,
                proxy_port=port,
                username=username,
                password=password,
                **kwargs
            )

        raise ValueError('Invalid proxy type: %s'  # pragma: no cover
                         % proxy_type)

    @classmethod
    def from_url(cls, url: str, **kwargs) -> BaseProxy:
        proxy_type, host, port, username, password = parse_proxy_url(url)
        return cls.create(
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            **kwargs
        )
