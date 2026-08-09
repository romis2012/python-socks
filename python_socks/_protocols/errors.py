from __future__ import annotations

from typing import Any


class ReplyError(Exception):
    def __init__(
        self,
        message: Any,
        error_code: int | None = None,
    ) -> None:
        super().__init__(message)
        self.error_code = error_code
