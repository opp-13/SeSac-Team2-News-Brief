"""Common interfaces shared by every news search provider."""

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Free News API's topic enum (GET /topics). NAVER has no native category
# concept, so the category string is used as its search query instead.
CATEGORIES = [
    "arts-design",
    "baseball",
    "basketball",
    "beauty",
    "business",
    "celebrities",
    "combat sports",
    "cricket",
    "cycling",
    "digital currencies",
    "economy",
    "education",
    "energy",
    "entertainment",
    "environment",
    "fashion",
    "finance",
    "food",
    "football",
    "gadgets",
    "gaming",
    "geology",
    "golf",
    "health",
    "higher education",
    "hockey",
    "home",
    "internet security",
    "jobs",
    "medicine",
    "mental health",
    "mobile",
    "motor sports",
    "movies",
    "music",
    "neuroscience",
    "nutrition",
    "online education",
    "outdoors",
    "paleontology",
    "personal finance",
    "physics",
    "politics",
    "public health",
    "robotics",
    "rugby",
    "science",
    "shopping",
    "soccer",
    "social sciences",
    "space",
    "sports",
    "sports betting",
    "technology",
    "tennis",
    "theater",
    "travel",
    "tv",
    "vehicles",
    "virtual reality",
    "water sports",
    "wildlife",
    "world",
]


@dataclass
class ArticleItem:
    title: str
    url: str
    description: str
    published_at: str
    source: str
    provider: str
    """Which provider produced this item ("naver" | "freenews") -- picks the detail fetcher."""
    detail_ref: str
    """Opaque reference the detail stage needs: a naver article link, or a freenews uuid."""
    language: str
    """Actual language of title/body ("ko" | "en") -- naver is always "ko"; for freenews
    this is whatever --language was actually searched with, not a provider-based guess."""
    body: str | None = None


class NewsProvider(ABC):
    @abstractmethod
    def search_by_category(self, category: str, display: int = 10, language: str = "en") -> list:
        """Return up to `display` ArticleItems for the given category.

        `language` is a hint ("ko" | "en"); providers that have no language
        concept (e.g. NAVER) ignore it.
        """
