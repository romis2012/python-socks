from .. import _abc as abc
from .._protocols import http


class HttpSyncConnector:
    def __init__(
        self,
        username: str,
        password: str,
        resolver: abc.SyncResolver,
    ):
        self._username = username
        self._password = password
        self._resolver = resolver

    def connect(
        self,
        stream: abc.SyncSocketStream,
        host: str,
        port: int,
    ) -> http.ConnectReply:
        conn = http.Connection()

        request = http.ConnectRequest(
            host=host,
            port=port,
            username=self._username,
            password=self._password,
        )
        data = conn.send(request)
        stream.write_all(data)

        data = stream.read()
        reply: http.ConnectReply = conn.receive(data)
        return reply
