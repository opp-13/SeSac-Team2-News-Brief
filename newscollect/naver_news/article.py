"""Best-effort extractor for full NAVER news article bodies.

The NAVER news search API only returns a summary (`description`), not the
full article text. This module downloads the `link` page and lets newspaper3k
(download + parse) pull the article body out of it. It only works for links
hosted on `n.news.naver.com` / `news.naver.com` -- for `originallink` pages
(the publisher's own site), markup varies per outlet and is not supported
here.
"""

from urllib.parse import urlparse

from newspaper import Article, ArticleException, Config

_SUPPORTED_HOSTS = {"n.news.naver.com", "news.naver.com"}
_USER_AGENT = "Mozilla/5.0 (compatible; poc-news/1.0)"


def is_naver_news_link(url: str) -> bool:
    return urlparse(url).netloc in _SUPPORTED_HOSTS


def fetch_article_body(url: str, timeout: int = 10) -> str | None:
    """Fetch and return the article body text, or None if unavailable/unsupported."""

    config = Config()
    config.browser_user_agent = _USER_AGENT
    config.request_timeout = timeout

    article = Article(url, language="ko", config=config)
    try:
        article.download()
        article.parse()
    except ArticleException:
        return None

    return article.text or None
