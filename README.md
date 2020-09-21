## python-socks

[![Build Status](https://travis-ci.org/romis2012/python-socks.svg?branch=master)](https://travis-ci.org/romis2012/python-socks)
[![Coverage Status](https://coveralls.io/repos/github/romis2012/python-socks/badge.svg?branch=master&_=x)](https://coveralls.io/github/romis2012/python-socks?branch=master)
[![PyPI version](https://badge.fury.io/py/python-socks.svg)](https://badge.fury.io/py/python-socks)

The `python-socks` package provides a core proxy client functionality for Python.
Supports SOCKS4(a), SOCKS5, HTTP (tunneling) proxy and provides sync and async (asyncio, trio) APIs.
You probably don't need to use `python-socks` directly. 
It is used internally by 
[aiohttp-socks](https://github.com/romis2012/aiohttp-socks) and [httpx-socks](https://github.com/romis2012/httpx-socks) packages.  

## Requirements
- Python >= 3.6
- async-timeout >= 3.0.1 (optional)
- trio >= 0.16.0 (optional)

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

## Simple usage
We are making secure HTTP GET request via SOCKS5 proxy
 
#### Sync
```python
import ssl
from python_socks.sync import Proxy

proxy = Proxy.from_url('socks5://user:password@127.0.0.1:1080')

# `connect` returns standard Python socket in blocking mode
sock = proxy.connect(dest_host='check-host.net', dest_port=443)

sock = ssl.create_default_context().wrap_socket(
    sock=sock,
    server_hostname='check-host.net'
)

request = (
    b'GET /ip HTTP/1.1\r\n'
    b'Host: check-host.net\r\n'
    b'Connection: close\r\n\r\n'
)
sock.sendall(request)
response = sock.recv(4096)
print(response)
```

#### Async (asyncio)
```python
import ssl
import asyncio
from python_socks.async_.asyncio import Proxy

proxy = Proxy.from_url('socks5://user:password@127.0.0.1:1080')

# `connect` returns standard Python socket in non-blocking mode 
# so we can pass it to asyncio.open_connection(...)
sock = await proxy.connect(dest_host='check-host.net', dest_port=443)

reader, writer = await asyncio.open_connection(
    host=None,
    port=None,
    sock=sock,
    ssl=ssl.create_default_context(),
    server_hostname='check-host.net',
)

request = (
    b'GET /ip HTTP/1.1\r\n'
    b'Host: check-host.net\r\n'
    b'Connection: close\r\n\r\n'
)

writer.write(request)
response = await reader.read(-1)
print(response)
```

#### Async (trio)
```python
import ssl
import trio
from python_socks.async_.trio import Proxy

proxy = Proxy.from_url('socks5://user:password@127.0.0.1:1080')

# `connect` returns trio socket 
# so we can pass it to trio.SocketStream
sock = await proxy.connect(dest_host='check-host.net', dest_port=443)

stream = trio.SocketStream(sock)

stream = trio.SSLStream(
    stream, ssl.create_default_context(),
    server_hostname='check-host.net'
)
await stream.do_handshake()

request = (
    b'GET /ip HTTP/1.1\r\n'
    b'Host: check-host.net\r\n'
    b'Connection: close\r\n\r\n'
)

await stream.send_all(request)
response = await stream.receive_some(4096)
print(response)
```

## More complex example

####A urllib3 PoolManager that routes connections via the proxy

```python
from urllib3 import PoolManager, HTTPConnectionPool, HTTPSConnectionPool
from urllib3.connection import HTTPConnection, HTTPSConnection
from python_socks.sync import Proxy


class ProxyHTTPConnection(HTTPConnection):
    def __init__(self, *args, **kwargs):
        socks_options = kwargs.pop('_socks_options')
        self._proxy_url = socks_options['proxy_url']
        super().__init__(*args, **kwargs)

    def _new_conn(self):
        proxy = Proxy.from_url(self._proxy_url)
        return proxy.connect(
            dest_host=self.host,
            dest_port=self.port,
            timeout=self.timeout
        )


class ProxyHTTPSConnection(ProxyHTTPConnection, HTTPSConnection):
    pass


class ProxyHTTPConnectionPool(HTTPConnectionPool):
    ConnectionCls = ProxyHTTPConnection


class ProxyHTTPSConnectionPool(HTTPSConnectionPool):
    ConnectionCls = ProxyHTTPSConnection


class ProxyPoolManager(PoolManager):
    def __init__(self, proxy_url, timeout=5, num_pools=10, headers=None,
                 **connection_pool_kw):

        connection_pool_kw['_socks_options'] = {'proxy_url': proxy_url}
        connection_pool_kw['timeout'] = timeout

        super().__init__(num_pools, headers, **connection_pool_kw)

        self.pool_classes_by_scheme = {
            'http': ProxyHTTPConnectionPool,
            'https': ProxyHTTPSConnectionPool,
        }


### and how to use it
manager = ProxyPoolManager('socks5://user:password@127.0.0.1:1080')
response = manager.request('GET', 'https://check-host.net/ip')
print(response.data)
```
