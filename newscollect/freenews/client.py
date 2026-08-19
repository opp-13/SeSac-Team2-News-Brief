"""HTTP client for the Free News API. Every actual request lives here --
providers/freenews_provider.py and details/freenews_detail.py only call
these methods and map the results, they never call `requests` themselves.
"""


import requests

from .config import FreeNewsConfig
from .exceptions import FreeNewsAPIError


class FreeNewsClient:
    def __init__(self, config: FreeNewsConfig | None = None):
        self._config = config or FreeNewsConfig.from_env()

    def _get(self, path: str, params: dict) -> dict:
        response = requests.get(
            f"{self._config.base_url}{path}",
            params=params,
            headers={"x-api-key": self._config.api_key},
            timeout=10,
        )

        if not response.ok:
            try:
                message = response.json().get("error", response.text)
            except ValueError:
                message = response.text
            raise FreeNewsAPIError(status_code=response.status_code, message=message)

        return response.json()

    def search_news(self, topic: str, language: str = "en", order_by: str = "recent") -> list[dict]:
        """Return the raw article dicts from GET /news (lightweight: uuid/title/published_at/publisher)."""
        return self._get(
            "/news",
            {"topic": topic, "language": language},
        ).get("data", [])

    def get_details(self, uuid: str) -> dict:
        """Return the raw article dict from GET /details (full body/original_url/etc)."""
        return self._get("/details", {"uuid": uuid}).get("data", {})
