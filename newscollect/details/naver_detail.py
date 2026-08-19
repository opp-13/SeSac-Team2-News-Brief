"""Detail-fetch stage for naver-provider ArticleItems.

Kept separate from providers/naver_provider.py on purpose: search returns a
lightweight list, detail-fetching is its own (slower, scraping) step that a
pipeline can choose to run or skip.
"""

from naver_news import fetch_article_body


def fetch_detail(detail_ref: str) -> dict:
    """detail_ref is the article's naver link. Returns {"body": ...}."""
    body = fetch_article_body(detail_ref)
    return {"body": body or "(본문을 가져올 수 없음: 네이버 뉴스 링크가 아니거나 파싱 실패)"}
