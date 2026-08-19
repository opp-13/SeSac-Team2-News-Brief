"""Data models for NAVER news search results."""

import html
import re
from dataclasses import dataclass, field

_TAG_RE = re.compile(r"<[^>]+>")


def clean_text(raw: str) -> str:
    """Strip highlight tags (e.g. <b>) and unescape HTML entities."""
    return html.unescape(_TAG_RE.sub("", raw))


@dataclass
class NewsItem:
    title: str
    originallink: str
    link: str
    description: str
    pub_date: str

    @classmethod
    def from_api(cls, data: dict) -> "NewsItem":
        return cls(
            title=clean_text(data.get("title", "")),
            originallink=data.get("originallink", ""),
            link=data.get("link", ""),
            description=clean_text(data.get("description", "")),
            pub_date=data.get("pubDate", ""),
        )


@dataclass
class NewsSearchResult:
    last_build_date: str
    total: int
    start: int
    display: int
    items: list[NewsItem] = field(default_factory=list)

    @classmethod
    def from_api(cls, data: dict) -> "NewsSearchResult":
        return cls(
            last_build_date=data.get("lastBuildDate", ""),
            total=data.get("total", 0),
            start=data.get("start", 0),
            display=data.get("display", 0),
            items=[NewsItem.from_api(item) for item in data.get("items", [])],
        )
