import asyncio
import sys

from googletrans import Translator

SUMMARY_FAILURE_PREFIX = "(요약 실패:"
TRANSLATION_FAILURE_PREFIX = "(번역 실패:"


async def _translate_all(items: list, target: str) -> None:
    async with Translator() as translator:
        for item in items:
            if not item.summary or item.summary.startswith(SUMMARY_FAILURE_PREFIX):
                continue  # no summary to translate

            if item.language == "ko":
                item.summary_ko = None  # summary is already Korean
                continue

            try:
                result = await translator.translate(item.summary, dest=target)
                item.summary_ko = result.text
            except Exception as e:
                item.summary_ko = f"{TRANSLATION_FAILURE_PREFIX} {e})"
                print(f"[translate] '{item.title[:30]}...' 번역 실패: {e}", file=sys.stderr)


def translate_stage(items: list, target: str = "ko") -> list:
    """Fill item.summary_ko for every item whose summary isn't already Korean."""
    asyncio.run(_translate_all(items, target))
    return items
