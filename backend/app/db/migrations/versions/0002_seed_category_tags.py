"""정식 카테고리 태그 시드 (slug = 기계 키, name = 한국어 표시명)

`tags`는 수집기(A)와 피드(C)가 함께 쓰는 **마스터 데이터**다. 어느 한쪽이 임의로 만들면
어휘가 갈려서, 사용자가 고른 관심 태그로는 기사가 한 건도 안 잡히는 상태가 된다.
실제로 그런 상태였다 — A는 Free News API의 topic enum(영문 63개)으로만 태그를 달고,
개발 시드는 한국어 태그를 따로 만들어서 두 어휘가 공존했다.

그래서 어휘를 하나로 고정한다.

  - `slug`: 기계 키. Free News API topic을 소문자·하이픈으로 정규화한 값.
            수집기가 이 값으로 태그를 찾는다 (newscollect/processing/db.py).
  - `name`: 화면 표시명(한국어). 프런트 필터 칩과 설정 화면이 이 값을 쓴다.
            바꿔도 slug가 그대로라 기사 연결이 끊기지 않는다.

`is_active`는 **화면 노출 여부**만 뜻한다. 수집기는 비활성 태그로도 기사를 태깅한다
(`_lookup_tag_id`는 is_active를 보지 않는다) — 데이터는 쌓되 필터 칩에 63개를 다
늘어놓지 않기 위함이다. 뉴스 브리핑에 맞는 12개만 활성으로 둔다.

슬러그 기준으로 UPSERT하므로 여러 번 돌려도 안전하고, 기존 DB의 같은 슬러그 행은
정식 표시명으로 갱신된다.

Revision ID: 0002_seed_tags
Revises: 0001_v2_initial
Create Date: 2026-08-20

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_seed_tags"
down_revision: str | None = "0001_v2_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# 화면 필터 칩에 노출할 카테고리. 나머지는 데이터로만 쌓인다.
ACTIVE_SLUGS = {
    "technology", "economy", "finance", "business", "politics", "world",
    "science", "health", "internet-security", "mobile", "environment", "entertainment",
}

# (slug, 한국어 표시명) — slug는 Free News API topic을 소문자·하이픈으로 정규화한 값이다.
CATEGORIES: list[tuple[str, str]] = [
    ("arts-design", "예술·디자인"), ("baseball", "야구"), ("basketball", "농구"),
    ("beauty", "뷰티"), ("business", "비즈니스"), ("celebrities", "셀럽"),
    ("combat-sports", "격투기"), ("cricket", "크리켓"), ("cycling", "사이클"),
    ("digital-currencies", "가상자산"), ("economy", "경제"), ("education", "교육"),
    ("energy", "에너지"), ("entertainment", "엔터테인먼트"), ("environment", "환경"),
    ("fashion", "패션"), ("finance", "금융"), ("food", "음식"),
    ("football", "미식축구"), ("gadgets", "가젯"), ("gaming", "게임"),
    ("geology", "지질학"), ("golf", "골프"), ("health", "건강"),
    ("higher-education", "고등교육"), ("hockey", "하키"), ("home", "홈·리빙"),
    ("internet-security", "보안"), ("jobs", "일자리"), ("medicine", "의학"),
    ("mental-health", "정신건강"), ("mobile", "모바일"), ("motor-sports", "모터스포츠"),
    ("movies", "영화"), ("music", "음악"), ("neuroscience", "신경과학"),
    ("nutrition", "영양"), ("online-education", "온라인 교육"), ("outdoors", "아웃도어"),
    ("paleontology", "고생물학"), ("personal-finance", "재테크"), ("physics", "물리학"),
    ("politics", "정치"), ("public-health", "공중보건"), ("robotics", "로봇"),
    ("rugby", "럭비"), ("science", "과학"), ("shopping", "쇼핑"),
    ("soccer", "축구"), ("social-sciences", "사회과학"), ("space", "우주"),
    ("sports", "스포츠"), ("sports-betting", "스포츠 베팅"), ("technology", "기술"),
    ("tennis", "테니스"), ("theater", "연극"), ("travel", "여행"),
    ("tv", "TV"), ("vehicles", "자동차"), ("virtual-reality", "VR"),
    ("water-sports", "수상스포츠"), ("wildlife", "야생동물"), ("world", "세계"),
]


def upgrade() -> None:
    # slug 유니크 기준 UPSERT. 기존 DB에 같은 슬러그가 있으면 정식 표시명으로 갱신한다.
    stmt = sa.text(
        """
        INSERT INTO tags (tag_type, name, slug, is_active)
        VALUES ('CATEGORY', :name, :slug, :is_active)
        ON DUPLICATE KEY UPDATE
            name = VALUES(name),
            tag_type = VALUES(tag_type),
            is_active = VALUES(is_active)
        """
    )
    conn = op.get_bind()
    for slug, name in CATEGORIES:
        conn.execute(stmt, {"slug": slug, "name": name, "is_active": slug in ACTIVE_SLUGS})


def downgrade() -> None:
    # 이 리비전이 넣은 슬러그만 지운다. article_tags / user_tags는 FK CASCADE로 정리된다.
    conn = op.get_bind()
    conn.execute(
        sa.text("DELETE FROM tags WHERE slug IN :slugs").bindparams(
            sa.bindparam("slugs", value=[s for s, _ in CATEGORIES], expanding=True)
        )
    )
