from __future__ import annotations

from typing import Any

import anyio
import anyio.abc


async def connect_tcp(
    host: str,
    port: int,
    **kwargs: Any,
) -> anyio.abc.SocketStream:
    return await anyio.connect_tcp(
        remote_host=host,
        remote_port=port,
        **kwargs,
    )
