from __future__ import annotations

from typing import Any

import anyio

from ._stream import AnyioSocketStream


async def connect_tcp(
    host: str,
    port: int,
    **kwargs: Any,
) -> AnyioSocketStream:
    s = await anyio.connect_tcp(
        remote_host=host,
        remote_port=port,
        **kwargs,
    )
    return AnyioSocketStream(s)
