"""Free News API search adapted to the common NewsProvider interface.

All HTTP calls live in freenews/client.py -- this module only maps the raw
article dicts from FreeNewsClient.search_news() into ArticleItems.
"""

from freenews import FreeNewsClient

from .base import ArticleItem, NewsProvider


class FreeNewsProvider(NewsProvider):
    def __init__(self):
        self._client = FreeNewsClient()

    def search_by_category(self, category: str, display: int = 10) -> list[ArticleItem]:
        articles = self._client.search_news(topic=category)[:display]

        return [
            ArticleItem(
                title=article["title"],
                url="",
                description="",
                published_at=article["published_at"],
                source=article.get("publisher") or "freenews",
                provider="freenews",
                detail_ref=article["uuid"],
            )
            for article in articles
        ]
