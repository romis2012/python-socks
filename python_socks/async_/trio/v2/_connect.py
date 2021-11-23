from typing import Optional, Tuple

import trio


async def connect_tcp(
    host: str,
    port: int,
    local_addr: Optional[Tuple[str, int]] = None,
) -> trio.SocketStream:
    return await trio.open_tcp_stream(
        host=host,
        port=port,
        local_address=local_addr,
    )
