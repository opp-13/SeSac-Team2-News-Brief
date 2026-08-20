"""feed/tag 모듈 API 경로 상수 (임시값).

[PROVISIONAL] 이 파일의 모든 값은 D의 `docs/api-contracts/feed.md`가 확정되기 전까지 쓰는
임시 이름이다. 확정 후에는 **이 파일만 고치면** 라우터/테스트가 모두 따라간다.
경로 문자열을 라우터에 직접 쓰지 말 것.
"""

API_PREFIX = "/api/v1"  # [PROV-A00] auth/api_paths.py와 동일 값

# ── 태그 ──────────────────────────────────────────────────────────────────────
TAGS_PREFIX = f"{API_PREFIX}/tags"        # [PROV-T01] GET — 선택 가능한 전체 태그 목록
ME_TAGS_PREFIX = f"{API_PREFIX}/me/tags"  # [PROV-T02] GET — 내 관심 태그 조회

TAG_LIST = ""            # GET  TAGS_PREFIX
MY_TAG_LIST = ""         # GET  ME_TAGS_PREFIX
MY_TAG_REPLACE = ""      # PUT  ME_TAGS_PREFIX        [PROV-T03] 전체 교체
MY_TAG_DELETE = "/{tag_id}"  # DELETE ME_TAGS_PREFIX/{tag_id}  [PROV-T04]

# ── 피드 ──────────────────────────────────────────────────────────────────────
FEED_PREFIX = f"{API_PREFIX}/feed"              # [PROV-F01]
FEED_LIST = ""                                  # GET  FEED_PREFIX
FEED_DETAIL = "/{feed_item_id}"                 # GET  FEED_PREFIX/{feedItemId}   [PROV-F02]
# 북마크는 기능 범위가 아니다 (design_plan.md §6.3 "공유·스크랩 넣지 않는다",
# frontend/CLAUDE.md §0.2). 경로·라우터·모델을 모두 제거했다.


# ── 쿼리 파라미터 기본값 ──────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20  # [PROV-F05] limit 기본값; 허용 범위 1-50
# feed_router.py가 Query(le=...)에서 이 상수를 참조하는데 정의가 빠져 있어
# 모듈 임포트 자체가 AttributeError로 실패했다. 위 주석의 "허용 범위 1-50"에 맞춘 값이다.
MAX_PAGE_SIZE = 50

# --- 관리자: 데이터 보관 정책 (docs/api-contracts/admin.md) ---
ADMIN_RETENTION_PREFIX = f"{API_PREFIX}/admin/retention"
ADMIN_RETENTION_LIST = ""                       # GET   ADMIN_RETENTION_PREFIX
ADMIN_RETENTION_UPDATE = "/{target_entity}"     # PATCH ADMIN_RETENTION_PREFIX/{targetEntity}
