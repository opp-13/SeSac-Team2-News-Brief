"""Exceptions for the NAVER news search client."""


class NaverNewsAPIError(Exception):
    """Raised when the NAVER news search API returns an error response."""

    def __init__(self, status_code: int, code: str, message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"[{status_code}/{code}] {message}")
