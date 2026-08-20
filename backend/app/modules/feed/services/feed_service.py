"""피드 조회 서비스.

**금지: 이 파일에서 LLM/AI 서비스를 호출하지 않는다** (CLAUDE.md §9, SKILL §4-1).
저장된 summaries/translations만 읽고, 없으면 null 또는 제외로 처리한다.
캐시를 붙이더라도 캐시 미스는 MySQL 조회까지만 이어진다.

컬럼명은 `docs/db/schema.sql`(V2) 기준이다. 언론사 이름은 articles가 직접 갖지 않고
news_sources를 조인해서 얻는다.

**북마크는 기능 범위가 아니다.** design_plan.md §6.3이 "공유·스크랩 넣지 않는다"로 제외했고
frontend/CLAUDE.md §0.2도 구현하지 않기로 정리해 뒀다. 관련 API/모델을 제거했다.
"""

from dataclasses import dataclass, field

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.common.exceptions import NotFoundError
from app.modules.feed.models.feed_item import FeedItem
from app.modules.feed.models.read_only import (
    FEED_READY_STATUSES,
    Article,
    ArticleTag,
    NewsSource,
    Summary,
    Translation,
)
from app.modules.feed.models.tag import TAG_TYPE_CATEGORY, Tag, UserTag

# [PROV-F15] 목록에 노출할 기본 요약 타입. "요약 3종 저장 여부"가 미결이므로 상수로 분리해 둔다.
LIST_SUMMARY_TYPE = "THREE_LINE"



@dataclass
class FeedRow:
    """목록 1행. 게스트는 feed_items 행이 없으므로 feed_item은 None일 수 있다."""

    article: Article
    language: str
    summary_text: str | None
    summary_type: str | None
    #

    press: str | None = None
    feed_item: FeedItem | None = None
    # 프런트가 태그 칩과 게스트 카테고리 필터에 쓰는 값. 이름으로 내려보낸다.
    tag_names: list[str] = field(default_factory=list)
    category: str | None = None


def _resolve_summary_text(
    db: Session, summary_id: int | None, translation_id: int | None
) -> tuple[str | None, str | None, str | None]:
    """저장된 번역 > 저장된 요약 순으로 사용. 없으면 (None, None, None) — 생성하지 않는다.

    반환값은 (본문, 요약 종류, 노출 언어)다. 노출 언어를 feed_items 컬럼으로 따로 두지 않고
    여기서 결정한다 — 번역이 있으면 그 번역의 target_language가 곧 노출 언어다.
    같은 정보를 두 곳에 두면 어긋난다.
    """
    if translation_id is not None:
        translation = db.get(Translation, translation_id)
        if translation is not None:
            summary = db.get(Summary, summary_id) if summary_id is not None else None
            return (
                translation.translated_content,
                summary.summary_type if summary else None,
                translation.target_language,
            )
    if summary_id is not None:
        summary = db.get(Summary, summary_id)
        if summary is not None:
            return summary.content, summary.summary_type, summary.language
    return None, None, None


def _resolve_tag_id(db: Session, tag_name: str | None) -> int | None:
    """태그 이름 → id. 프런트는 이름으로 필터한다(`docs/api-contracts/feed.md`).

    없는 이름이면 404가 아니라 None을 돌려준다 — 필터 칩이 잠깐 어긋났다고
    화면을 오류로 만들 이유는 없고, 호출 측이 "매칭 0건"으로 처리한다.
    """
    if not tag_name:
        return None
    return db.scalar(select(Tag.id).where(Tag.name == tag_name))


def _load_article_tags(db: Session, article_ids: list[int]) -> dict[int, list[Tag]]:
    """기사 id → 태그 목록. 행마다 개별 조회하면 N+1이 되므로 한 번에 읽는다."""
    if not article_ids:
        return {}
    rows = db.execute(
        select(ArticleTag.article_id, Tag)
        .join(Tag, Tag.id == ArticleTag.tag_id)
        .where(ArticleTag.article_id.in_(article_ids))
    ).all()
    out: dict[int, list[Tag]] = {}
    for article_id, tag in rows:
        out.setdefault(article_id, []).append(tag)
    return out


def _load_press_names(db: Session, source_ids: list[int]) -> dict[int, str]:
    """news_sources.id → 이름. articles에 언론사 이름 컬럼이 없어 조인해서 채운다."""
    ids = [i for i in source_ids if i is not None]
    if not ids:
        return {}
    return dict(db.execute(select(NewsSource.id, NewsSource.name).where(NewsSource.id.in_(ids))).all())


def _search_filter(stmt, q: str | None):  # noqa: ANN001, ANN201
    """제목·언론사·요약·태그 이름 부분일치 검색.

    검색 범위를 이 네 곳으로 잡은 이유: 프런트가 서버 검색 이전에 쓰던 클라이언트 필터가
    같은 범위였다. 서버로 옮기면서 범위가 줄면 "전에는 찾아졌는데 지금은 안 나오는" 회귀가
    된다. (예: "반도체"는 태그에만 있고 제목에는 없다.)

    언론사는 articles에 이름이 없어 news_sources 서브쿼리로 찾는다.

    [성능] LIKE '%...%'는 인덱스를 타지 못하고 서브쿼리가 셋이나 붙는다. 스키마 V2가
    보조 인덱스와 FULLTEXT를 본문에서 빼고 하단 주석의 추가 후보로 돌렸으므로
    (docs/db/schema.sql), 검색을 정식 기능으로 유지하려면 articles.title에 FULLTEXT를
    되살리고 MATCH ... AGAINST로 바꿔야 한다.
    지금은 시연 규모(일 수천 건) 기준으로 LIKE를 쓴다.
    """
    if not q:
        return stmt
    needle = f"%{q.strip()}%"
    return stmt.where(
        or_(
            Article.title.like(needle),
            Article.source_id.in_(select(NewsSource.id).where(NewsSource.name.like(needle))),
            Article.id.in_(select(Summary.article_id).where(Summary.content.like(needle))),
            Article.id.in_(
                select(ArticleTag.article_id)
                .join(Tag, Tag.id == ArticleTag.tag_id)
                .where(Tag.name.like(needle))
            ),
        )
    )


def _pick_category(tags: list[Tag]) -> str | None:
    """카테고리 성격의 태그 이름을 하나 고른다.

    스키마는 카테고리/키워드를 별도 컬럼이 아니라 `tags.tag_type` ENUM으로 구분한다.
    """
    for tag in tags:
        if tag.tag_type == TAG_TYPE_CATEGORY:
            return tag.name
    return None


def _order_matched_first(tags: list[Tag], matched_tag_id: int | None) -> list[str]:
    """매칭된 태그를 맨 앞에 둔다 — 이 기사가 노출된 사유가 먼저 보여야 한다."""
    names = [t.name for t in tags if t.id == matched_tag_id]
    names += [t.name for t in tags if t.id != matched_tag_id]
    return names


def list_feed(
    db: Session,
    *,
    user_id: int | None,
    limit: int,
    cursor: int | None = None,
    tag: str | None = None,
    q: str | None = None,
) -> tuple[list[FeedRow], int | None, bool]:
    """로그인 여부로 두 가지로 동작한다 (`docs/api-contracts/feed.md`).

    - 게스트(user_id=None): `articles` 최신순. 커서는 article.id
    - 로그인: `feed_items` (배치가 미리 만든 개인화 피드). 커서는 feed_item.id

    어느 쪽이든 저장된 요약만 읽는다. 요약을 생성하지 않는다 (CLAUDE.md §1).
    """
    tag_id = _resolve_tag_id(db, tag)
    if tag and tag_id is None:
        # 존재하지 않는 태그로 필터하면 결과는 0건이다.
        return [], None, False

    if user_id is None:
        return _list_guest(db, limit=limit, cursor=cursor, tag_id=tag_id, q=q)

    # 관심 태그가 하나도 없으면 개인화할 근거가 없다 → 게스트와 같은 전체 최신 목록.
    #
    # 설정 화면이 "태그를 선택하지 않으면 전체 최신 뉴스를 보여줍니다"로 약속하고 있는데,
    # feed_items만 읽으면 빈 화면이 된다. 계약에 명시돼 있다
    # (docs/api-contracts/feed.md "관심 태그가 하나도 없는 로그인 사용자").
    # 이때 응답의 feedItemId는 null이 되고 isRead는 생략된다 — 게스트와 같은 형태다.
    if not db.scalar(select(UserTag.id).where(UserTag.user_id == user_id).limit(1)):
        return _list_guest(db, limit=limit, cursor=cursor, tag_id=tag_id, q=q)

    return _list_personal(db, user_id=user_id, limit=limit, cursor=cursor, tag_id=tag_id, q=q)


def _list_guest(
    db: Session, *, limit: int, cursor: int | None, tag_id: int | None, q: str | None
) -> tuple[list[FeedRow], int | None, bool]:
    stmt = (
        select(Article)
        # 요약이 끝난 기사만 노출한다(조회 시점 생성 금지 — CLAUDE.md §1).
        .where(Article.status.in_(FEED_READY_STATUSES))
        .order_by(Article.id.desc())
        .limit(limit + 1)
    )
    if cursor is not None:
        stmt = stmt.where(Article.id < cursor)
    if tag_id is not None:
        stmt = stmt.where(
            Article.id.in_(select(ArticleTag.article_id).where(ArticleTag.tag_id == tag_id))
        )
    stmt = _search_filter(stmt, q)

    articles = list(db.scalars(stmt))
    has_next = len(articles) > limit
    articles = articles[:limit]
    article_ids = [a.id for a in articles]

    # 게스트는 선호 언어가 없으므로 번역을 거치지 않고 원문 언어 요약을 그대로 쓴다.
    summaries = {
        s.article_id: s
        for s in db.scalars(
            select(Summary).where(
                Summary.article_id.in_(article_ids or [0]),
                Summary.summary_type == LIST_SUMMARY_TYPE,
            )
        )
    }
    tags_by_article = _load_article_tags(db, article_ids)
    press_by_source = _load_press_names(db, [a.source_id for a in articles])

    result = [
        FeedRow(
            article=article,
            language=article.language,
            summary_text=summaries[article.id].content if article.id in summaries else None,
            summary_type=LIST_SUMMARY_TYPE if article.id in summaries else None,
            press=press_by_source.get(article.source_id) if article.source_id else None,
            feed_item=None,
            # 게스트 행에는 태그 칩을 표시하지 않는다(design_plan §7) — 이름은 비우고
            # 카테고리만 넘겨 필터 칩이 동작하게 한다.
            tag_names=[],
            category=_pick_category(tags_by_article.get(article.id, [])),
        )
        for article in articles
    ]
    next_cursor = result[-1].article.id if result and has_next else None
    return result, next_cursor, has_next


def _list_personal(
    db: Session,
    *,
    user_id: int,
    limit: int,
    cursor: int | None,
    tag_id: int | None,
    q: str | None,
) -> tuple[list[FeedRow], int | None, bool]:
    stmt = (
        select(FeedItem, Article)
        .join(Article, Article.id == FeedItem.article_id)
        .where(FeedItem.user_id == user_id)
        .order_by(FeedItem.id.desc())
        .limit(limit + 1)  # has_next 판별용 1건 초과 조회
    )
    if cursor is not None:
        stmt = stmt.where(FeedItem.id < cursor)
    if tag_id is not None:
        # 기사에 붙은 태그로 거른다 — 게스트 경로(`_list_guest`)와 같은 기준이다.
        #
        # 이전에는 `FeedItem.matched_tag_id == tag_id`로 걸렀는데, 그건 "이 태그 때문에
        # 노출된 행"이라는 뜻이지 "이 태그가 붙은 기사"가 아니다. matched_tag_id에는
        # 큐레이션이 고른 사유 **하나만** 들어가므로(curate는 관심 태그 중 첫 번째를 쓴다),
        # 기사가 [IT, AI, 개발]이어도 사유가 AI로 기록됐으면 'IT' 칩에서 사라졌다.
        # 프런트는 로그인 시 필터 칩을 사용자의 관심 태그로 그리기 때문에(NewsFeedPage),
        # 관심 태그를 새로 고르면 모든 칩이 0건이 되는 증상으로 나타났다.
        # 같은 칩이 로그인 여부에 따라 다른 의미를 갖던 것을 맞춘다.
        stmt = stmt.where(
            FeedItem.article_id.in_(
                select(ArticleTag.article_id).where(ArticleTag.tag_id == tag_id)
            )
        )
    stmt = _search_filter(stmt, q)

    rows = list(db.execute(stmt).all())
    has_next = len(rows) > limit
    rows = rows[:limit]

    tags_by_article = _load_article_tags(db, [r[1].id for r in rows])
    press_by_source = _load_press_names(db, [r[1].source_id for r in rows])

    result: list[FeedRow] = []
    for feed_item, article in rows:
        text, stype, language = _resolve_summary_text(
            db, feed_item.summary_id, feed_item.translation_id
        )
        article_tags = tags_by_article.get(article.id, [])
        result.append(
            FeedRow(
                feed_item=feed_item,
                article=article,
                language=language or article.language,
                summary_text=text,
                summary_type=stype,
                press=press_by_source.get(article.source_id) if article.source_id else None,
                tag_names=_order_matched_first(article_tags, feed_item.matched_tag_id),
                category=_pick_category(article_tags),
            )
        )

    next_cursor = result[-1].feed_item.id if result and result[-1].feed_item and has_next else None
    return result, next_cursor, has_next


def get_feed_detail(
    db: Session, *, user_id: int, feed_item_id: int
) -> tuple[FeedRow, dict[str, str | None]]:
    feed_item = db.get(FeedItem, feed_item_id)
    if feed_item is None or feed_item.user_id != user_id:
        # 남의 피드 행 존재 여부를 노출하지 않기 위해 동일하게 404 처리한다.
        raise NotFoundError("FEED_ITEM_NOT_FOUND")

    article = db.scalar(select(Article).where(Article.id == feed_item.article_id))
    if article is None:
        raise NotFoundError("ARTICLE_NOT_FOUND")

    # 저장된 요약 3종만 조회. 없으면 None (생성하지 않는다).
    summaries = {
        s.summary_type: s
        for s in db.scalars(select(Summary).where(Summary.article_id == article.id))
    }
    # 노출 언어는 feed_item이 가리키는 번역에서 온다. 그 언어의 번역만 골라 쓴다.
    _, _, language = _resolve_summary_text(db, feed_item.summary_id, feed_item.translation_id)
    language = language or article.language
    translations = {
        t.summary_id: t
        for t in db.scalars(
            select(Translation).where(
                Translation.summary_id.in_([s.id for s in summaries.values()] or [0]),
                Translation.target_language == language,
            )
        )
    }

    def pick(summary_type: str) -> str | None:
        s = summaries.get(summary_type)
        if s is None:
            return None
        t = translations.get(s.id)
        return t.translated_content if t is not None else s.content

    press_by_source = _load_press_names(db, [article.source_id])
    row = FeedRow(
        feed_item=feed_item,
        article=article,
        language=language,
        summary_text=pick(LIST_SUMMARY_TYPE),
        summary_type=LIST_SUMMARY_TYPE,
        press=press_by_source.get(article.source_id) if article.source_id else None,
    )
    contents = {
        "ONE_LINE": pick("ONE_LINE"),
        "THREE_LINE": pick("THREE_LINE"),
        "DETAIL": pick("DETAIL"),
    }
    return row, contents
