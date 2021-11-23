import asyncio
from typing import Optional, Tuple


async def connect_tcp(
    host: str,
    port: int,
    local_addr: Optional[Tuple[str, int]] = None,
) -> Tuple[asyncio.StreamReader, asyncio.StreamWriter]:

    kwargs = {}
    if local_addr is not None:
        kwargs['local_addr'] = local_addr   # pragma: no cover

    reader, writer = await asyncio.open_connection(
        host=host,
        port=port,
        **kwargs,
    )

    return reader, writer
