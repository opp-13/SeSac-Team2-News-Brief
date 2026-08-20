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
FEED_BOOKMARK = "/{feed_item_id}/bookmark"      # POST/DELETE                     [PROV-F03]

BOOKMARK_PREFIX = f"{API_PREFIX}/me/bookmarks"  # [PROV-F04] 미구현

# ── 쿼리 파라미터 기본값 ──────────────────────────────────────────────────────
DEFAULT_PAGE_SIZE = 20  # [PROV-F05] limit 기본값; 허용 범위 1-50
