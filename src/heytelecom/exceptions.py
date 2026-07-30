"""Custom exception hierarchy for the heytelecom library."""

from __future__ import annotations

__all__ = [
    "APIError",
    "AuthenticationError",
    "HeyTelecomError",
]


class HeyTelecomError(Exception):
    """Base exception for all heytelecom errors."""


class AuthenticationError(HeyTelecomError):
    """Authentication or login failed."""


class APIError(HeyTelecomError):
    """API request failed or returned unexpected data.

    Attributes:
        status_code: HTTP status code when available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
