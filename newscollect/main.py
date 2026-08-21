"""Category-based news search pipeline: search -> detail -> combined output.

Each stage is a separate module (providers/*, details/*) called explicitly
here, so the pipeline shape stays visible instead of hiding inside a class.
"""

import argparse
import sys

from dotenv import load_dotenv

import details
from providers import CATEGORIES, PROVIDER_NAMES, get_provider

load_dotenv()

# DB(`tags.slug`)는 "internet-security", Free News API topic은 "internet security"다.
# 배치는 슬러그로 부르고 사람은 topic으로 부르므로 둘 다 받는다.
#
# 단순히 하이픈을 공백으로 바꾸면 안 된다 -- "arts-design"은 하이픈이 원래 이름의
# 일부라 그대로 두어야 하고, "internet-security"는 공백으로 되돌려야 한다. 슬러그를
# 만들 때와 같은 규칙으로 역인덱스를 만들어 두면 이 구분이 자동으로 맞는다.
_CATEGORY_BY_SLUG = {c.lower().replace(" ", "-"): c for c in CATEGORIES}


def _normalize_category(value: str) -> str:
    return _CATEGORY_BY_SLUG.get(value.strip().lower(), value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="카테고리 기반 뉴스 검색 파이프라인 (NAVER + Free News API)"
    )
    parser.add_argument(
        "--category",
        type=_normalize_category,  # choices 검사 전에 슬러그를 topic으로 바꾼다
        choices=CATEGORIES,
        required=True,
        help="검색 카테고리 (topic 또는 tags.slug — 'internet security' / 'internet-security' 모두 가능)",
    )
    parser.add_argument(
        "--provider",
        choices=["all", *PROVIDER_NAMES],
        default="all",
        help="검색할 provider (기본값 all: 전부 합쳐서 출력)",
    )
    parser.add_argument(
        "--display", type=int, default=10, help="provider별 검색 결과 개수 (기본값 10)"
    )
    parser.add_argument(
        "--language",
        choices=["ko", "en"],
        default="en",
        help="freenews 검색 언어 (기본값 en). naver는 언어 개념이 없어 무시됨",
    )
    parser.add_argument("--with-body", action="store_true", help="본문(body)도 함께 가져옵니다")
    return parser.parse_args()


def search_stage(category: str, display: int, providers: list, language: str = "en") -> list:
    """Run the given providers and return one combined, unsorted list of items."""
    items = []
    for name in providers:
        try:
            items.extend(
                get_provider(name).search_by_category(category, display=display, language=language)
            )
        except Exception as e:
            print(f"[{name}] 검색 오류: {e}", file=sys.stderr)
    return items


def detail_stage(items: list) -> list:
    """Fetch full body (and, for freenews, the original URL) for each item in place."""
    for item in items:
        try:
            detail = details.fetch_detail(item.provider, item.detail_ref)
            item.body = detail.get("body")
            if detail.get("url"):
                item.url = detail["url"]
        except Exception as e:
            item.body = f"(본문 조회 실패: {e})"
    return items


def summarize_stage(items: list, summarize_and_translate) -> list:
    """Summarize each item in its own actual language (item.language).

    Doesn't call summarize_and_translate.summarize_stage() directly -- that
    picks a language per item.provider (freenews == always "eng"), which is
    wrong now that freenews can be searched in Korean too via --language.
    """
    for item in items:
        lang = "kor" if item.language == "ko" else "eng"
        summarize_and_translate.summarize_item(item, lang)
    return items


def output_stage(items: list) -> None:
    """Print every item, merged and sorted by published_at, regardless of provider."""
    items = sorted(items, key=lambda i: i.published_at, reverse=True)
    for idx, item in enumerate(items, start=1):
        print(f"[{idx}] ({item.provider}/{item.source}) {item.title}")
        if item.description:
            print(f"    {item.description}")
        if item.body:
            print(f"    본문: {item.body[:300]}")
        if item.url:
            print(f"    링크: {item.url}")
        print(f"    발행: {item.published_at}\n")


def main() -> int:
    args = parse_args()
    providers = PROVIDER_NAMES if args.provider == "all" else [args.provider]

    items = search_stage(args.category, args.display, providers, language=args.language)

    # Import lib for data processing [Lazy Load]
    from processing import summarize_and_translate
    from processing.cosine_similarity import dedup_stage
    from processing.db import persist_stage
    from processing.translate import translate_stage

    items = dedup_stage(items, tag=args.category)

    if args.with_body:
        items = detail_stage(items)

    summarize_stage(items, summarize_and_translate)
    translate_stage(items)
    items = persist_stage(items, category=args.category)

    ## 디버깅용
    output_stage(items)

    return 0


if __name__ == "__main__":
    sys.exit(main())
