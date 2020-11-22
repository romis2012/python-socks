from typing import Type, Union, Dict, Any
from ._types import ProxyType
from ._proxy_sync import SyncProxy
from ._proxy_async import AsyncProxy
from ._helpers import parse_proxy_url


class ProxyFactory:
    types: Dict[ProxyType, Type[Any]]

    @classmethod
    def create(cls, proxy_type: ProxyType, host: str, port: int,
               username: str = None, password: str = None,
               rdns: bool = None, **kwargs) -> Union[SyncProxy, AsyncProxy]:

        proxy_cls = cls.types.get(proxy_type)

        if proxy_type == ProxyType.SOCKS4:
            return proxy_cls(
                proxy_host=host,
                proxy_port=port,
                user_id=username,
                rdns=rdns,
                **kwargs
            )

        if proxy_type == ProxyType.SOCKS5:
            return proxy_cls(
                proxy_host=host,
                proxy_port=port,
                username=username,
                password=password,
                rdns=rdns,
                **kwargs
            )

        if proxy_type == ProxyType.HTTP:
            return proxy_cls(
                proxy_host=host,
                proxy_port=port,
                username=username,
                password=password,
                **kwargs
            )

        raise ValueError('Invalid proxy type: %s'  # pragma: no cover
                         % proxy_type)

    @classmethod
    def from_url(cls, url: str, **kwargs) -> Union[SyncProxy, AsyncProxy]:
        proxy_type, host, port, username, password = parse_proxy_url(url)
        return cls.create(
            proxy_type=proxy_type,
            host=host,
            port=port,
            username=username,
            password=password,
            **kwargs
        )
