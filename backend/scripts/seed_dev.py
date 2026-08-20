"""로컬 개발용 시드 데이터.

    cd backend
    .venv/bin/python scripts/seed_dev.py

**개발 편의용이다.** 운영 스키마의 기준은 `docs/db/schema.sql`이고 변경은 Alembic +
C 창구를 거친다 (CLAUDE.md §5 규칙 5). 이 스크립트는 **데이터만 넣는다 — 테이블을 만들지
않는다.** 스키마는 `alembic upgrade head`로 먼저 올려 둔다 (CLAUDE.md §2.1).

이전에는 여기서 `Base.metadata.create_all()`을 불렀는데, 모델이 스키마 전체를 덮지 않아서
빈 DB에 돌리면 **일부 테이블만, 그것도 모델 기준으로** 만들어졌다. Alembic이 올린 스키마와
갈라지는 경로라 없앴다.

넣는 것:
- 카테고리/키워드 태그 (프런트 필터 칩·설정 화면이 서버 태그를 쓴다)
- 요약이 붙은 기사 8건 (요약 없는 기사는 게스트 목록에 안 나온다)
- 기사-태그 매핑
- 계정 2개: 일반(user@example.com) / 관리자(admin@example.com), 비밀번호 password123
- 관리자에게는 관심 태그와 개인화 피드 행까지 만들어, 로그인 후 화면이 비어 보이지 않게 한다

비밀번호는 하드코딩된 시크릿이 아니라 로컬 시드용 고정값이다. 운영 DB에 절대 돌리지 않는다.
"""

import hashlib
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import inspect  # noqa: E402

from app.common.models.batch_job import BatchJob, JobLog  # noqa: E402,F401
from app.db.session import SessionLocal, engine  # noqa: E402
from app.modules.auth.models.user import User  # noqa: E402
from app.modules.auth.services.password import hash_password  # noqa: E402
from app.modules.feed.models.feed_item import FeedItem  # noqa: E402
from app.modules.feed.models.read_only import (  # noqa: E402
    Article,
    ArticleTag,
    NewsSource,
    Summary,
    Translation,  # noqa: F401
)
from app.modules.feed.models.tag import (  # noqa: E402
    TAG_TYPE_CATEGORY,
    TAG_TYPE_KEYWORD,
    Tag,
    UserTag,
)

SEED_PASSWORD = "password123"  # 로컬 전용

# 시드용 고정값. 실제 값은 배치가 호출 시점에 채운다(환경변수로 주입 — CLAUDE.md §8-10).
# 화면에서 프로바이더 구분이 보이도록 관리자 목업과 같은 식별자를 쓴다.
SEED_PROVIDER = "anthropic"
SEED_MODEL_NAME = "claude-sonnet-5"
SEED_SOURCE_PROVIDER = "RSS"

# (이름, slug, tag_type) — CATEGORY인 것만 게스트 필터 칩에 노출된다.
TAGS: list[tuple[str, str, str]] = [
    ("IT", "it", TAG_TYPE_CATEGORY),
    ("경제", "economy", TAG_TYPE_CATEGORY),
    ("정치", "politics", TAG_TYPE_CATEGORY),
    ("글로벌", "global", TAG_TYPE_CATEGORY),
    ("스타트업", "startup", TAG_TYPE_CATEGORY),
    ("보안", "security", TAG_TYPE_CATEGORY),
    ("AI", "ai", TAG_TYPE_KEYWORD),
    ("개발", "dev", TAG_TYPE_KEYWORD),
    ("반도체", "semiconductor", TAG_TYPE_KEYWORD),
    ("규제", "regulation", TAG_TYPE_KEYWORD),
    ("모바일", "mobile", TAG_TYPE_KEYWORD),
]

# 언론사 — articles.source_id가 이 테이블을 가리킨다(스키마에 press 컬럼은 없다).
PRESSES = ["TechCrunch", "한국경제", "Reuters", "블로터", "Wired", "조선비즈", "The Verge", "이데일리"]

# (제목, 언론사, 태그 이름들, 3줄 요약)
ARTICLES: list[tuple[str, str, list[str], str]] = [
    (
        "OpenAI, GPT-5 출시 일정 공개… 추론 성능 GPT-4o 대비 3배",
        "TechCrunch",
        ["IT", "AI", "개발"],
        "OpenAI가 차세대 언어 모델 GPT-5의 출시 일정을 공식 발표했다. 회사에 따르면 추론 성능이 "
        "기존 GPT-4o 대비 약 3배 향상됐고, 복잡한 수학 문제와 코드 생성에서 특히 개선이 크다. "
        "API 접근은 9월부터 순차 확대된다.",
    ),
    (
        "삼성전자, 3분기 HBM4 양산 돌입… 엔비디아 납품 경쟁 본격화",
        "한국경제",
        ["경제", "반도체", "글로벌"],
        "삼성전자가 3분기부터 HBM4 양산에 돌입한다고 밝혔다. AI 가속기 시장에서 독주해온 "
        "SK하이닉스와의 엔비디아 납품 경쟁이 한층 치열해질 전망이다. 삼성은 열 문제를 해결했다며 "
        "연내 공급 계약 체결에 자신감을 보였다.",
    ),
    (
        "EU, AI 법안 시행 첫 해 위반 기업에 총 2.3억 유로 과징금",
        "Reuters",
        ["글로벌", "AI", "규제"],
        "EU 집행위원회가 AI법 시행 첫 해에 총 2억 3천만 유로의 과징금을 부과했다고 발표했다. "
        "위반 사례 대부분은 고위험 AI 시스템의 투명성 의무 미준수와 편향성 평가 보고서 미제출에 "
        "집중됐다. 미국 기업 3곳이 전체 과징금의 68%를 차지했다.",
    ),
    (
        "카카오, AI 에이전트 플랫폼 카나나 정식 출시… 월 9,900원",
        "블로터",
        ["IT", "AI", "스타트업"],
        "카카오가 AI 에이전트 서비스 카나나를 정식 출시하며 월 9,900원 구독 요금제를 발표했다. "
        "카카오톡·멜론·카카오맵 등 자사 서비스와 연동해 일정 관리, 쇼핑, 음악 추천을 하나의 "
        "대화형 인터페이스로 처리하는 것이 특징이다.",
    ),
    (
        "Anthropic, 클로드 멀티모달 업데이트… 실시간 영상 분석 강화",
        "Wired",
        ["IT", "AI", "개발"],
        "Anthropic이 Claude 시리즈에 실시간 영상 스트림 분석과 강화된 도구 호출 기능을 추가하는 "
        "업데이트를 배포했다. 컴퓨터 사용 API가 정식 GA로 전환되며 엔터프라이즈 고객의 RPA 수요를 "
        "겨냥한 요금 체계도 개편됐다.",
    ),
    (
        "한국은행, 기준금리 2.75% 동결… 내수 회복 지연·가계부채 우려",
        "조선비즈",
        ["경제"],
        "한국은행 금융통화위원회가 이달 기준금리를 연 2.75%로 동결했다. 내수 회복이 기대에 미치지 "
        "못하는 동시에 가계부채 잔액이 다시 증가세로 전환됐다며 양측 리스크를 모두 고려한 결정이라고 "
        "설명했다. 시장은 연내 추가 인하 가능성을 40% 수준으로 본다.",
    ),
    (
        "Apple, iOS 베타에 온디바이스 LLM 추론 탑재 확인",
        "The Verge",
        ["IT", "AI", "모바일"],
        "Apple의 개발자 베타 빌드 분석을 통해 온디바이스 LLM 추론 엔진이 포함된 사실이 확인됐다. "
        "최신 칩 이상 탑재 기기에서만 동작하며, Siri의 복잡한 요청 처리와 메일·메시지 초안 생성에 "
        "활용될 전망이다. Apple은 공식 언급을 피하고 있다.",
    ),
    (
        "국회 AI 기본법 소위, 고위험 AI 정의 놓고 산업계·시민단체 충돌",
        "이데일리",
        ["정치", "AI", "규제"],
        "국회 AI 기본법 소위원회에서 고위험 AI의 범위를 두고 산업계와 시민단체 간 이견이 첨예하게 "
        "대립했다. 산업계는 현행 초안이 글로벌 경쟁력을 약화시킨다고 주장한 반면, 시민단체는 채용·"
        "금융·의료 AI에 대한 규제가 여전히 불충분하다는 입장을 고수했다.",
    ),
]


def main() -> None:
    if not inspect(engine).has_table("articles"):
        print("스키마가 없습니다. 먼저 마이그레이션을 올리세요:\n  .venv/bin/alembic upgrade head")
        raise SystemExit(1)

    db = SessionLocal()
    try:
        if db.query(Article).count() > 0:
            print("이미 시드가 있습니다. 다시 넣으려면 DB를 비우고 실행하세요.")
            return

        now = datetime.now(timezone.utc)

        tags = {name: Tag(name=name, slug=slug, tag_type=tag_type) for name, slug, tag_type in TAGS}
        db.add_all(tags.values())
        sources = {name: NewsSource(name=name, provider=SEED_SOURCE_PROVIDER) for name in PRESSES}
        db.add_all(sources.values())
        db.flush()

        for offset, (title, press, tag_names, summary_text) in enumerate(ARTICLES):
            url = f"https://news.example.com/{offset + 1}"
            article = Article(
                title=title,
                url=url,
                # 실제 수집기(A)와 같은 규칙으로 채운다 — 정규화 URL의 SHA-256.
                # NOT NULL이고 단독 UNIQUE라 비워 둘 수 없다.
                url_hash=hashlib.sha256(url.encode()).hexdigest(),
                source_id=sources[press].id,
                status="SUMMARIZED",
                language="ko",
                # 최신순 정렬이 보이도록 시간을 벌려 둔다.
                published_at=now - timedelta(hours=offset * 3),
            )
            db.add(article)
            db.flush()
            db.add(
                Summary(
                    article_id=article.id,
                    summary_type="THREE_LINE",
                    content=summary_text,
                    language="ko",
                    provider=SEED_PROVIDER,
                    model_name=SEED_MODEL_NAME,
                    created_at=now,
                )
            )
            for name in tag_names:
                db.add(ArticleTag(article_id=article.id, tag_id=tags[name].id))

        password_hash = hash_password(SEED_PASSWORD)
        user = User(
            email="user@example.com",
            password_hash=password_hash,
            nickname="일반사용자",
            role="USER",
            preferred_language="ko",
            status="ACTIVE",
        )
        admin = User(
            email="admin@example.com",
            password_hash=password_hash,
            nickname="관리자",
            role="ADMIN",
            preferred_language="ko",
            status="ACTIVE",
        )
        db.add_all([user, admin])
        db.flush()

        # 두 계정 모두 관심 태그 + 개인화 피드를 갖게 한다. 로그인 직후 화면이 비어 보이면
        # "붙었는지" 확인이 안 된다.
        for account, interest in ((user, ["AI", "개발"]), (admin, ["AI", "경제", "반도체"])):
            for name in interest:
                db.add(UserTag(user_id=account.id, tag_id=tags[name].id))

            for article in db.query(Article).all():
                article_tag_ids = {
                    at.tag_id for at in db.query(ArticleTag).filter_by(article_id=article.id).all()
                }
                matched = next(
                    (tags[n].id for n in interest if tags[n].id in article_tag_ids), None
                )
                if matched is None:
                    continue
                summary = db.query(Summary).filter_by(article_id=article.id).first()
                if summary is None:
                    # feed_items.summary_id는 NOT NULL이다. 요약 없는 기사는 애초에
                    # 피드 행을 만들지 않는다(curation_service와 같은 규칙).
                    continue
                db.add(
                    FeedItem(
                        user_id=account.id,
                        article_id=article.id,
                        summary_id=summary.id,
                        matched_tag_id=matched,
                        created_at=now,
                    )
                )

        db.commit()

        print(f"태그 {len(tags)}개, 언론사 {len(sources)}개, 기사 {len(ARTICLES)}건, 요약 {len(ARTICLES)}건")
        print(f"피드 행 {db.query(FeedItem).count()}건")
        print("\n계정 (비밀번호: password123)")
        print("  user@example.com    일반")
        print("  admin@example.com   관리자 — 관리자 화면 접근용")
    finally:
        db.close()


if __name__ == "__main__":
    main()
