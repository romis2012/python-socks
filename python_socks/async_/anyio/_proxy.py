from typing import Optional

import anyio

from ..._errors import ProxyConnectionError, ProxyTimeoutError
from ..._proto.http_async import HttpProto
from ..._proto.socks4_async import Socks4Proto
from ..._proto.socks5_async import Socks5Proto

from ._resolver import Resolver
from ._stream import AnyioSocketStream
from ._connect import connect_tcp

DEFAULT_TIMEOUT = 60


class AnyioProxy:
    _stream: Optional[AnyioSocketStream]

    def __init__(
        self,
        proxy_host,
        proxy_port,
        proxy_ssl=None,
    ):
        self._proxy_host = proxy_host
        self._proxy_port = proxy_port
        self._proxy_ssl = proxy_ssl

        self._dest_host = None
        self._dest_port = None
        self._dest_ssl = None
        self._timeout = None

        self._stream = None
        self._resolver = Resolver()

    async def connect(
        self,
        dest_host,
        dest_port,
        dest_ssl=None,
        timeout=None,
        _stream: AnyioSocketStream = None,
    ) -> AnyioSocketStream:

        if timeout is None:
            timeout = DEFAULT_TIMEOUT

        self._dest_host = dest_host
        self._dest_port = dest_port
        self._dest_ssl = dest_ssl
        self._timeout = timeout

        try:
            with anyio.fail_after(self._timeout):
                if _stream is None:
                    self._stream = AnyioSocketStream(
                        await connect_tcp(
                            host=self._proxy_host,
                            port=self._proxy_port,
                        )
                    )
                else:
                    self._stream = _stream

                if self._proxy_ssl is not None:
                    self._stream = await self._stream.start_tls(
                        hostname=self._proxy_host,
                        ssl_context=self._proxy_ssl,
                    )

                await self._negotiate()

                if self._dest_ssl is not None:
                    self._stream = await self._stream.start_tls(
                        hostname=self._dest_host,
                        ssl_context=self._dest_ssl,
                    )

                # return self._stream.anyio_stream
                return self._stream

        except TimeoutError as e:
            await self._close()
            raise ProxyTimeoutError('Proxy connection timed out: {}'.format(self._timeout)) from e
        except (OSError, anyio.BrokenResourceError) as e:
            await self._close()
            msg = 'Could not connect to proxy {}:{} [{}]'.format(
                self._proxy_host,
                self._proxy_port,
                e.strerror,
            )
            raise ProxyConnectionError(e.errno, msg) from e
        except Exception:
            await self._close()
            raise

    async def _negotiate(self):
        raise NotImplementedError()

    async def _close(self):
        if self._stream is not None:
            await self._stream.close()

    @property
    def proxy_host(self):
        return self._proxy_host

    @property
    def proxy_port(self):
        return self._proxy_port


class Socks5Proxy(AnyioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        rdns=None,
        proxy_ssl=None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
        )
        self._username = username
        self._password = password
        self._rdns = rdns

    async def _negotiate(self):
        proto = Socks5Proto(
            stream=self._stream,
            resolver=self._resolver,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
            rdns=self._rdns,
        )
        await proto.negotiate()


class Socks4Proxy(AnyioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        user_id=None,
        rdns=None,
        proxy_ssl=None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
        )
        self._user_id = user_id
        self._rdns = rdns

    async def _negotiate(self):
        proto = Socks4Proto(
            stream=self._stream,
            resolver=self._resolver,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            user_id=self._user_id,
            rdns=self._rdns,
        )
        await proto.negotiate()


class HttpProxy(AnyioProxy):
    def __init__(
        self,
        proxy_host,
        proxy_port,
        username=None,
        password=None,
        proxy_ssl=None,
    ):
        super().__init__(
            proxy_host=proxy_host,
            proxy_port=proxy_port,
            proxy_ssl=proxy_ssl,
        )
        self._username = username
        self._password = password

    async def _negotiate(self):
        proto = HttpProto(
            stream=self._stream,
            dest_host=self._dest_host,
            dest_port=self._dest_port,
            username=self._username,
            password=self._password,
        )
        await proto.negotiate()
