"""Console output formatting for news search results."""

from .models import NewsSearchResult


def format_result(result: NewsSearchResult) -> str:
    lines = [f"총 {result.total:,}건 중 {result.start}번째부터 {len(result.items)}건 표시\n"]

    for idx, item in enumerate(result.items, start=result.start):
        lines.append(f"[{idx}] {item.title}")
        lines.append(f"    {item.description}")
        lines.append(f"    링크: {item.link}")
        lines.append(f"    발행: {item.pub_date}\n")

    return "\n".join(lines)


def print_result(result: NewsSearchResult) -> None:
    print(format_result(result))
