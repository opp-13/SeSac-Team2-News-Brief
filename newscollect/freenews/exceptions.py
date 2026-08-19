"""Exceptions for the Free News API client."""


class FreeNewsAPIError(Exception):
    """Raised when the Free News API returns an error response."""

    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"[{status_code}] {message}")
