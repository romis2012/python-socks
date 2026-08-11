from __future__ import annotations

from typing import Any


class IncompleteReadError(Exception):
    pass


class ProxyException(Exception):  # noqa: N818
    pass


class ProxyTimeoutError(ProxyException, TimeoutError):
    pass


class ProxyConnectionError(ProxyException, OSError):
    pass


class ProxyError(ProxyException):
    def __init__(
        self,
        message: Any,
        error_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
