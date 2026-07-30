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
    """API request failed or returned unexpected data."""
