from typing import Any

from .._abc import AsyncSocketStream, SyncSocketStream


class SyncConnector:
    def connect(
        self,
        stream: SyncSocketStream,
        host: str,
        port: int,
    ) -> Any:
        raise NotImplementedError


class AsyncConnector:
    async def connect(
        self,
        stream: AsyncSocketStream,
        host: str,
        port: int,
    ) -> Any:
        raise NotImplementedError
