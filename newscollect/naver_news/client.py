"""HTTP client for the NAVER API HUB news search endpoint."""

from typing import Literal, Optional

import requests

from .config import NaverAPIConfig
from .exceptions import NaverNewsAPIError
from .models import NewsSearchResult

SortOption = Literal["sim", "date"]

_NEWS_SEARCH_PATH = "/search/v1/news"


class NaverNewsClient:
    def __init__(self, config: Optional[NaverAPIConfig] = None):
        self._config = config or NaverAPIConfig.from_env()

    def search(
        self,
        query: str,
        display: int = 5,
        start: int = 1,
        sort: SortOption = "sim",
    ) -> NewsSearchResult:
        if not 1 <= display <= 100:
            raise ValueError("display 값은 1~100 사이여야 합니다.")
        if not 1 <= start <= 1000:
            raise ValueError("start 값은 1~1000 사이여야 합니다.")
        if sort not in ("sim", "date"):
            raise ValueError("sort 값은 'sim' 또는 'date' 여야 합니다.")

        response = requests.get(
            f"{self._config.base_url}{_NEWS_SEARCH_PATH}",
            params={
                "query": query,
                "display": display,
                "start": start,
                "sort": sort,
                "format": "json",
            },
            headers={
                "X-NCP-APIGW-API-KEY-ID": self._config.client_id,
                "X-NCP-APIGW-API-KEY": self._config.client_secret,
            },
            timeout=10,
        )

        if not response.ok:
            self._raise_for_error(response)

        return NewsSearchResult.from_api(response.json())

    @staticmethod
    def _raise_for_error(response: requests.Response) -> None:
        try:
            body = response.json()
        except ValueError:
            body = {}

        error = body.get("error", {})
        raise NaverNewsAPIError(
            status_code=response.status_code,
            code=error.get("errorCode", "UNKNOWN"),
            message=error.get("message", response.text),
        )
