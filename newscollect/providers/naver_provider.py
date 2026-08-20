"""NAVER news search adapted to the common NewsProvider interface.

NAVER's news search API has no category concept, so the category string
(e.g. "technology") is used directly as the free-text search query.
"""

from naver_news import NaverNewsClient

from .base import ArticleItem, NewsProvider


class NaverProvider(NewsProvider):
    def __init__(self):
        self._client = NaverNewsClient()

    def search_by_category(
        self, category: str, display: int = 10, language: str = "ko"
    ) -> list[ArticleItem]:
        # 참고로 language는 무시됨
        result = self._client.search(query=category, display=display, sort="date")
        return [
            ArticleItem(
                title=item.title,
                url=item.link,
                description=item.description,
                published_at=item.pub_date,
                source="naver",
                provider="naver",
                detail_ref=item.link,
            )
            for item in result.items
        ]
