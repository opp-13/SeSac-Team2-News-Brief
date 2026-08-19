"""Category-based news search pipeline: search -> detail -> combined output.

Each stage is a separate module (providers/*, details/*) called explicitly
here, so the pipeline shape stays visible instead of hiding inside a class.
"""

import argparse
import sys

import details
from providers import CATEGORIES, PROVIDER_NAMES, get_provider


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="카테고리 기반 뉴스 검색 파이프라인 (NAVER + Free News API)")
    parser.add_argument("--category", choices=CATEGORIES, required=True, help="검색 카테고리")
    parser.add_argument(
        "--provider",
        choices=["all", *PROVIDER_NAMES],
        default="all",
        help="검색할 provider (기본값 all: 전부 합쳐서 출력)",
    )
    parser.add_argument("--display", type=int, default=10, help="provider별 검색 결과 개수 (기본값 10)")
    parser.add_argument("--with-body", action="store_true", help="본문(body)도 함께 가져옵니다")
    return parser.parse_args()


def search_stage(category: str, display: int, providers: list) -> list:
    """Run the given providers and return one combined, unsorted list of items."""
    items = []
    for name in providers:
        try:
            items.extend(get_provider(name).search_by_category(category, display=display))
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

    items = search_stage(args.category, args.display, providers)

    ## TODO: 유사도 기반 중복 기사 제거 모듈을 여기(search_stage -> detail_stage 사이)에 추가.

    if args.with_body:
        items = detail_stage(items)

    ## 디버깅용
    output_stage(items)

    ## TODO: AI 요약 및 번역 모듈 또는 호출 API 추가


    return 0


if __name__ == "__main__":
    sys.exit(main())
