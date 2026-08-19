from .base import CATEGORIES, ArticleItem, NewsProvider

PROVIDER_NAMES = ["naver", "freenews"]


def get_provider(name: str) -> NewsProvider:
    if name == "naver":
        from .naver_provider import NaverProvider

        return NaverProvider()
    if name == "freenews":
        from .freenews_provider import FreeNewsProvider

        return FreeNewsProvider()
    raise ValueError(f"알 수 없는 provider: {name}")


__all__ = ["CATEGORIES", "PROVIDER_NAMES", "ArticleItem", "NewsProvider", "get_provider"]
