import asyncio
from typing import Optional, Tuple
from ._stream import AsyncioSocketStream


async def connect_tcp(
    host: str,
    port: int,
    local_addr: Optional[Tuple[str, int]] = None,
    loop: asyncio.AbstractEventLoop = None,
) -> AsyncioSocketStream:
    if loop is None:
        loop = asyncio.get_running_loop()

    kwargs = {}
    if local_addr is not None:
        kwargs['local_addr'] = local_addr  # pragma: no cover

    reader, writer = await asyncio.open_connection(
        host=host,
        port=port,
        loop=loop,
        **kwargs,
    )

    return AsyncioSocketStream(
        loop=loop,
        reader=reader,
        writer=writer,
    )
