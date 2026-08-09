from __future__ import annotations

import asyncio
from typing import Any

from ._stream import AsyncioSocketStream


async def connect_tcp(
    host: str,
    port: int,
    loop: asyncio.AbstractEventLoop,
    local_addr: tuple[str, int] | None = None,
) -> AsyncioSocketStream:
    kwargs: dict[str, Any] = {}
    if local_addr is not None:
        kwargs["local_addr"] = local_addr  # pragma: no cover

    reader, writer = await asyncio.open_connection(
        host=host,
        port=port,
        **kwargs,
    )

    return AsyncioSocketStream(
        loop=loop,
        reader=reader,
        writer=writer,
    )
