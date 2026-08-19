from . import freenews_detail, naver_detail

_FETCHERS = {
    "naver": naver_detail.fetch_detail,
    "freenews": freenews_detail.fetch_detail,
}


def fetch_detail(provider: str, detail_ref: str) -> dict:
    return _FETCHERS[provider](detail_ref)


__all__ = ["fetch_detail"]
