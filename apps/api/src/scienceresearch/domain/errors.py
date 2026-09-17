from __future__ import annotations


class AppError(Exception):
    """Stable application error contract shared by every transport."""

    def __init__(self, code: str, message: str, status: int = 422) -> None:
        super().__init__(message)
        self.code, self.message, self.status = code, message, status
