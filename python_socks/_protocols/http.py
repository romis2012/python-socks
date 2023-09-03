import sys
from dataclasses import dataclass

from .._basic_auth import BasicAuth
from .._version import __title__, __version__

from .errors import ReplyError

DEFAULT_USER_AGENT = 'Python/{0[0]}.{0[1]} {1}/{2}'.format(
    sys.version_info,
    __title__,
    __version__,
)

CRLF = '\r\n'


class _Buffer:
    def __init__(self, encoding: str = 'utf-8'):
        self._encoding = encoding
        self._buffer = bytearray()

    def append_line(self, line: str = ""):
        if line:
            self._buffer.extend(line.encode(self._encoding))

        self._buffer.extend(CRLF.encode('ascii'))

    def dumps(self) -> bytes:
        return bytes(self._buffer)


@dataclass
class ConnectRequest:
    host: str
    port: int
    username: str
    password: str

    def dumps(self) -> bytes:
        buff = _Buffer()
        buff.append_line(f'CONNECT {self.host}:{self.port} HTTP/1.1')
        buff.append_line(f'Host: {self.host}:{self.port}')
        buff.append_line(f'User-Agent: {DEFAULT_USER_AGENT}')

        if self.username and self.password:
            auth = BasicAuth(self.username, self.password)
            buff.append_line(f'Proxy-Authorization: {auth.encode()}')

        buff.append_line()

        return buff.dumps()


@dataclass
class ConnectReply:
    status_code: int
    message: str

    @classmethod
    def loads(cls, data: bytes) -> 'ConnectReply':
        if not data:
            raise ReplyError('Invalid proxy response')  # pragma: no cover

        line = data.split(CRLF.encode('ascii'), 1)[0]
        line = line.decode('utf-8', 'surrogateescape')

        try:
            version, code, *reason = line.split()
        except ValueError:  # pragma: no cover
            raise ReplyError(f'Invalid status line: {line}')

        try:
            status_code = int(code)
        except ValueError:  # pragma: no cover
            raise ReplyError(f'Invalid status code: {code}')

        status_message = " ".join(reason)

        if status_code != 200:
            msg = f'{status_code} {status_message}'
            raise ReplyError(msg, error_code=status_code)

        return cls(status_code=status_code, message=status_message)


# noinspection PyMethodMayBeStatic
class Connection:
    def send(self, request: ConnectRequest) -> bytes:
        return request.dumps()

    def receive(self, data: bytes) -> ConnectReply:
        return ConnectReply.loads(data)
