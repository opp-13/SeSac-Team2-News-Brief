"""Best-effort scraper for full NAVER news article bodies.

The NAVER news search API only returns a summary (`description`), not the
full article text. This module fetches the `link` page and parses the body
out of NAVER's own article markup. It only works for links hosted on
`n.news.naver.com` / `news.naver.com` -- for `originallink` pages (the
publisher's own site), markup varies per outlet and is not supported here.
"""

from typing import Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

_SUPPORTED_HOSTS = {"n.news.naver.com", "news.naver.com"}
_BODY_SELECTORS = ["#dic_area", "#articleBodyContents"]
_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; poc-news/1.0)"}


def is_naver_news_link(url: str) -> bool:
    return urlparse(url).netloc in _SUPPORTED_HOSTS


def fetch_article_body(url: str, timeout: int = 10) -> Optional[str]:
    """Fetch and return the article body text, or None if unavailable/unsupported."""
    if not is_naver_news_link(url):
        return None

    response = requests.get(url, headers=_HEADERS, timeout=timeout)
    if not response.ok:
        return None

    soup = BeautifulSoup(response.text, "html.parser")

    body = None
    for selector in _BODY_SELECTORS:
        body = soup.select_one(selector)
        if body:
            break

    if body is None:
        return None

    text = body.get_text(separator="\n", strip=True)
    return text or None
