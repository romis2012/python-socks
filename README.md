## python-socks

[![CI](https://github.com/romis2012/python-socks/actions/workflows/ci.yml/badge.svg)](https://github.com/romis2012/python-socks/actions/workflows/ci.yml)
[![Coverage Status](https://codecov.io/gh/romis2012/python-socks/branch/master/graph/badge.svg)](https://codecov.io/gh/romis2012/python-socks)
[![PyPI version](https://badge.fury.io/py/python-socks.svg)](https://pypi.python.org/pypi/python-socks)
[![versions](https://img.shields.io/pypi/pyversions/python-socks.svg)](https://github.com/romis2012/python-socks)
<!--
[![Downloads](https://pepy.tech/badge/python-socks/month)](https://pepy.tech/project/python-socks)
-->

The `python-socks` package provides a core proxy client functionality for Python.
Supports `SOCKS4(a)`, `SOCKS5(h)`, `HTTP CONNECT` proxy and provides sync and async (asyncio, trio, anyio) APIs.
You probably don't need to use `python-socks` directly. 
It is used internally by 
[aiohttp-socks](https://github.com/romis2012/aiohttp-socks) and [httpx-socks](https://github.com/romis2012/httpx-socks) packages.  

## Requirements
- Python >= 3.9
- async-timeout >= 5.0 (optional)
- trio >= 0.30 (optional)
- anyio >= 4.12 (optional)

## Installation

only sync proxy support:
```
pip install python-socks
```

to include optional asyncio support:
```
pip install python-socks[asyncio]
```

to include optional trio support:
```
pip install python-socks[trio]
```

to include optional anyio support:
```
pip install python-socks[anyio]
```

## Simple usage
We are making secure HTTP GET request via SOCKS5 proxy
 
#### Sync
```python
import ssl
from python_socks.sync import Proxy


def fetch():
    proxy = Proxy.from_url("socks5://user:password@127.0.0.1:1080")

    # `connect` returns standard Python socket in blocking mode
    sock = proxy.connect(
        dest_host="check-host.net",
        dest_port=443,
    )

    sock = ssl.create_default_context().wrap_socket(
        sock=sock,
        server_hostname="check-host.net",
    )

    # fmt: off
    request = (
        b"GET /ip HTTP/1.1\r\n"
        b"Host: check-host.net\r\n"
        b"Connection: close\r\n\r\n"
    )
    # fmt: on

    sock.sendall(request)
    response = sock.recv(4096)
    print(response)


fetch()
```

#### Async (asyncio)
```python
import asyncio
import ssl
from python_socks.async_.asyncio import Proxy


async def fetch():
    proxy = Proxy.from_url("socks5://user:password@127.0.0.1:1080")

    # `connect` returns standard Python socket in non-blocking mode
    # so we can pass it to asyncio.open_connection(...)
    sock = await proxy.connect(
        dest_host="check-host.net",
        dest_port=443,
    )

    reader, writer = await asyncio.open_connection(
        sock=sock,
        ssl=ssl.create_default_context(),
        server_hostname="check-host.net",
    )

    # fmt: off
    request = (
        b"GET /ip HTTP/1.1\r\n"
        b"Host: check-host.net\r\n"
        b"Connection: close\r\n\r\n"
    )
    # fmt: on

    writer.write(request)
    response = await reader.read(-1)
    print(response)

    writer.close()
    await writer.wait_closed()


asyncio.run(fetch())
```

#### Async (trio)
```python
import ssl
import trio
from python_socks.async_.trio import Proxy


async def fetch():
    proxy = Proxy.from_url("socks5://user:password@127.0.0.1:1080")

    # `connect` returns trio.socket.SocketType
    # so we can pass it to trio.SocketStream
    sock = await proxy.connect(
        dest_host="check-host.net",
        dest_port=443,
    )
    stream = trio.SocketStream(sock)
    stream = trio.SSLStream(
        stream,
        ssl_context=ssl.create_default_context(),
        server_hostname="check-host.net",
    )
    await stream.do_handshake()

    # fmt: off
    request = (
        b"GET /ip HTTP/1.1\r\n"
        b"Host: check-host.net\r\n"
        b"Connection: close\r\n\r\n"
    )
    # fmt: on

    await stream.send_all(request)
    response = await stream.receive_some(4096)
    print(response)

    await stream.aclose()


trio.run(fetch)
```

#### Async (anyio)
```python
import ssl
import anyio
from anyio.streams.tls import TLSStream
from python_socks.async_.anyio import Proxy


async def fetch():
    proxy = Proxy.from_url("socks5://user:password@127.0.0.1:1080")

    # `connect` returns anyio.abc.SocketStream
    # we can use it directly
    stream = await proxy.connect(
        dest_host="check-host.net",
        dest_port=443,
    )
    stream = await TLSStream.wrap(
        stream,
        ssl_context=ssl.create_default_context(),
        hostname="check-host.net",
    )

    # fmt: off
    request = (
        b"GET /ip HTTP/1.1\r\n"
        b"Host: check-host.net\r\n"
        b"Connection: close\r\n\r\n"
    )
    # fmt: on

    await stream.send(request)
    response = await stream.receive(4096)
    print(response)

    await stream.aclose()


anyio.run(fetch)
```

## More complex example

#### A urllib3 PoolManager that routes connections via the proxy

```python
from urllib3 import PoolManager, HTTPConnectionPool, HTTPSConnectionPool
from urllib3.connection import HTTPConnection, HTTPSConnection
from python_socks.sync import Proxy


class ProxyHTTPConnection(HTTPConnection):
    def __init__(self, *args, **kwargs):
        socks_options = kwargs.pop("_socks_options")
        self._proxy_url = socks_options["proxy_url"]
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        proxy = Proxy.from_url(self._proxy_url)
        return proxy.connect(
            dest_host=self.host,
            dest_port=self.port,
            timeout=self.timeout,
        )


class ProxyHTTPSConnection(ProxyHTTPConnection, HTTPSConnection):
    pass


class ProxyHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = ProxyHTTPConnection


class ProxyHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = ProxyHTTPSConnection


class ProxyPoolManager(PoolManager):
    def __init__(
        self,
        proxy_url,
        timeout=5,
        num_pools=10,
        headers=None,
        **connection_pool_kw,
    ):

        connection_pool_kw["_socks_options"] = {"proxy_url": proxy_url}
        connection_pool_kw["timeout"] = timeout

        super().__init__(num_pools, headers, **connection_pool_kw)

        self.pool_classes_by_scheme = {
            "http": ProxyHTTPConnectionPool,
            "https": ProxyHTTPSConnectionPool,
        }


### and how to use it
manager = ProxyPoolManager("socks5://user:password@127.0.0.1:1080")
response = manager.request("GET", "https://check-host.net/ip")
print(response.data)
```

## Proxy Chaining (sync example — same for asyncio, trio, anyio)

```python
import ssl
from python_socks.sync import Proxy


def fetch():
    proxy1 = Proxy.from_url("socks5://user:password@127.0.0.1:1080")
    proxy2 = Proxy.from_url("socks4://127.0.0.1:1081", forward=proxy1)
    proxy3 = Proxy.from_url("http://user:password@127.0.0.1:1082", forward=proxy2)

    sock = proxy3.connect(
        dest_host="check-host.net",
        dest_port=443,
    )

    sock = ssl.create_default_context().wrap_socket(
        sock=sock,
        server_hostname="check-host.net",
    )

    # fmt: off
    request = (
        b"GET /ip HTTP/1.1\r\n"
        b"Host: check-host.net\r\n"
        b"Connection: close\r\n\r\n"
    )
    # fmt: on

    sock.sendall(request)
    response = sock.recv(4096)
    print(response)


fetch()
```