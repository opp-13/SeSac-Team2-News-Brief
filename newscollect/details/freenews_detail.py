"""Detail-fetch stage for freenews-provider ArticleItems.

Kept separate from providers/freenews_provider.py on purpose: /news (search)
is lightweight, /details (this module) is a second call per article that a
pipeline can choose to run or skip. All HTTP calls live in
freenews/client.py -- this module only maps the raw detail dict.
"""

from freenews import FreeNewsClient


def fetch_detail(detail_ref: str) -> dict:
    """detail_ref is the article's uuid. Returns {"body": ..., "url": ...}."""
    data = FreeNewsClient().get_details(detail_ref)

    return {
        "body": data.get("body") or data.get("incipit") or "",
        "url": data.get("original_url") or "",
    }
