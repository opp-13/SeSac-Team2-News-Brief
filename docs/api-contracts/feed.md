# Feed API 계약

> **상태: DRAFT — C 승인 대기.** 루트 CLAUDE.md §5 규칙4에 따라 C·D 양측 승인 전까지
> 구현에 착수하지 않는다. 프론트(D)는 현재 이 계약 없이 목업 배열을 직접 쓰고 있어
> (`frontend/src/hooks/useFeed.ts`) **아직 api 레이어를 경유하지 않는다** — 계약 확정 후
> `frontend/src/api/feed.ts`를 만들어 전환한다.
>
> 관련 문서: [auth.md](auth.md) (세션·관심 태그), [admin.md](admin.md), [meta.md](meta.md)

## 공통 규약 (루트 CLAUDE.md §6)

- `BASE = /api/v1`, 모든 요청에 `credentials: 'include'`
- 응답 봉투: `{ "success": true, "data": ... }` | `{ "success": false, "error": { "code", "message" } }`
- 페이지네이션은 **커서 기반**: 요청 `cursor`, 응답 `nextCursor` / `hasNext`
- 시각은 **ISO 8601 UTC**. 상대시간("12분 전")은 프론트가 계산한다 (§ 아래 `relativeTime` 참고)

## 🚫 절대 제약 — 조회 경로에 LLM을 호출하지 않는다

루트 CLAUDE.md의 설계 핵심 제약이다. 이 문서의 **모든 엔드포인트는 저장된 결과만 읽는다.**

- 요약이 없는 기사를 만났을 때 **그 자리에서 생성하지 않는다.**
- 요약이 없으면 목록/상세에서 **제외**하거나 명시적 상태값으로 반환한다.
- "캐시 미스 시 온디맨드 생성" 같은 구현은 성능 문제가 아니라 **비용 사고**로 취급한다.

요약·번역 생성은 배치(`summarize.py` / `translate.py`, B 담당)만 수행하고,
`feed_items` 행 생성은 `curate.py`(C 담당)만 수행한다 (루트 CLAUDE.md §8-5).

---

## GET /feed — 뉴스 목록

화면: `/` (전체 작업량의 30%, 최우선 화면). 무한 스크롤 목록.

**같은 엔드포인트가 로그인 여부에 따라 두 가지로 동작한다** (design_plan.md §7 표).

| | 비로그인 (게스트) | 로그인 |
|---|---|---|
| 데이터 출처 | `articles` 최신순 전체 | `feed_items` (배치가 미리 만든 개인화 피드) |
| 필터 칩 | 카테고리 (`tags.tag_type='CATEGORY'`) | 사용자 관심 태그 + 맨 앞 `전체` |
| 행의 태그 칩 | 표시하지 않음 → `tags` 생략/빈 배열 | 매칭된 태그 최대 2개 |
| `isRead` | 항상 없음 (읽음 기록 주체가 없음) | `feed_items.is_read` |

### 관심 태그가 하나도 없는 로그인 사용자 → 게스트와 같은 목록

설정 화면이 **"태그를 선택하지 않으면 전체 최신 뉴스를 보여줍니다"**로 약속하고 있다
(`SettingsPage`). 개인화할 근거가 없는데 `feed_items`만 읽으면 빈 화면이 되므로,
관심 태그가 0개인 로그인 사용자는 **게스트와 동일하게 `articles` 최신순**으로 응답한다.

이때 응답 형태도 게스트와 같다 — 피드 행이 없으므로 `feedItemId`는 `null`이고
`isRead`는 생략된다. 프론트는 로그인 상태여도 이 응답을 그대로 그리면 된다.

`tag` 파라미터는 이 경우에도 동작한다(게스트와 같은 `article_tags` 기준). 다만 로그인 시
필터 칩은 관심 태그이므로, 관심 태그가 0개면 칩도 `전체` 하나뿐이라 실질적으로 쓰이지 않는다.

### 관심 태그를 바꾸면 피드가 그 자리에서 다시 맞춰진다

`PUT /me/tags`가 저장과 동시에 해당 사용자의 `feed_items`를 현재 관심사에 맞춘다.
`feed_items`는 배치만 채우는 테이블인데 배치 실행 기술이 미정이라(루트 CLAUDE.md §8),
트리거가 없으면 가입 직후·태그 변경 직후에 피드가 빈 채로 남기 때문이다.

맞추는 규칙은 세 가지다.

1. **삭제** — 현재 관심 태그가 **하나도** 붙어 있지 않은 기사의 행을 지운다.
   `matched_tag_id`가 빠졌다는 이유로 지우지 않는다. 기사가 `[경제, 반도체]`이고 사유가
   `경제`인데 `경제`만 해제했다면, `반도체`가 아직 관심사이므로 행은 남아야 한다.
2. **사유 갱신** — 살아남은 행의 `matched_tag_id`가 더 이상 관심사가 아니면, 그 기사에
   붙은 태그 중 현재 관심사인 것으로 다시 지정한다. 안 그러면 행의 태그 칩 정렬이
   사용자가 따르지도 않는 태그를 맨 앞에 세운다.
3. **생성** — 새로 걸리는 기사로 행을 만든다 (요약이 있는 기사만).

`feed_items`는 `summaries`로부터 언제든 재생성할 수 있는 파생 테이블이라 삭제가 안전하다.
단, `feed_items.is_read`를 실제로 쓰기 시작하면 1번이 읽음 상태를 잃는 동작이 된다 —
그 시점에 "행을 지우는 대신 숨긴다" 같은 대안을 다시 검토해야 한다. 현재는 백엔드·프론트
어느 쪽도 `is_read`를 저장하지 않으므로 잃는 것이 없다.

### 요청

```
GET /api/v1/feed?tag=AI&cursor=eyJpZCI6MTIzfQ&limit=20
```

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `tag` | 아니오 | 필터할 태그/카테고리 **이름**. 생략 = `전체` (프론트의 `전체` 칩은 파라미터를 보내지 않음) |
| `cursor` | 아니오 | 이전 응답의 `nextCursor`. 첫 페이지는 생략. **불투명 문자열이므로 프론트는 파싱하지 않는다** |
| `limit` | 아니오 | 기본값 20 제안. 상한을 서버가 정하고 여기 명시할 것 |

### 응답 — 200

```json
{
  "success": true,
  "data": {
    "articles": [
      {
        "id": "128402",
        "source": "TechCrunch",
        "category": "IT",
        "headline": "OpenAI, GPT-5 출시 일정 공개…",
        "tags": ["AI", "개발"],
        "url": "https://techcrunch.com/...",
        "publishedAt": "2026-08-19T10:18:00Z",
        "isNew": true,
        "isRead": false
      }
    ],
    "nextCursor": "eyJpZCI6MTI4MzkwfQ",
    "hasNext": true
  }
}
```

### 필드 매핑 (`docs/db/schema.sql` 기준)

| 필드 | 타입 | 출처 | 비고 |
|---|---|---|---|
| `id` | **string** | `articles.id` | ⚠️ `BIGINT UNSIGNED`는 JS 안전 정수 범위(2^53)를 넘을 수 있어 **문자열로 직렬화**할 것 |
| `source` | string | `news_sources.name` | `articles.source_id`가 NULL이면? → 아래 열려있는 질문 |
| `category` | string | `article_tags` ⋈ `tags` 중 `tag_type='CATEGORY'` | 2개 이상 매칭 시 규칙 필요 (아래 참고) |
| `headline` | string | `articles.title` | 프론트에서 2줄 말줄임 |
| `tags` | string[] | `article_tags` ⋈ `tags` 중 `tag_type='KEYWORD'` | 로그인 시에만 의미 있음. 프론트는 최대 2개만 표시 |
| `url` | string | `articles.url` | 원문 링크 (새 탭) |
| `publishedAt` | string | `articles.published_at` | ISO 8601 UTC |
| `isNew` | boolean? | **스키마에 없음** — 정의 필요 (아래) | 앰버 점 + "속보" 표시용 |
| `isRead` | boolean? | `feed_items.is_read` | 로그인 시에만. 게스트는 생략 |

### ⚠️ `relativeTime`을 서버가 만들지 않는다

프론트의 현재 타입(`frontend/src/types/feed.ts`)에는 피그마 프로토타입에서 온
`relativeTime: string`("12분 전")이 남아 있다. 그러나 루트 CLAUDE.md §6은
"시각은 ISO 8601 UTC로 받고, KST 변환은 `utils/date.ts`에서 처리"로 정하고 있다.

→ **서버는 `publishedAt`만 보내고, `relativeTime`은 프론트가 계산한다.**
API 연동 시 프론트의 `Article` 타입에서 `relativeTime`을 제거하고
`utils/date.ts`에 변환 함수를 추가하는 작업이 필요하다 (D 담당, 아직 미착수).

### ⚠️ `summary`를 목록에 포함하지 않는다

design_plan.md §6.1: "**요약문은 목록에 넣지 않습니다.** 행을 누르면 상세 화면으로
이동해 거기서 요약을 봅니다." 목록 응답에서 요약 본문을 빼면 페이로드가 크게 줄고
디자인 의도와도 맞는다.

단, 프론트의 현재 구현은 목록에서 받은 기사 객체를 그대로 모달에 넘긴다. 목록에서
`summary`를 빼면 모달이 `GET /articles/{id}`로 따로 받아와야 한다 —
**어차피 직접 URL 진입(`/articles/1`)을 지원해야 하므로 그 엔드포인트는 필수다**(아래).

> **현재 구현은 목록 응답에 `summary`를 포함한다.** 모달이 목록 객체를 그대로 쓰고 있어
> 빼면 상세가 비기 때문이다. 화면상으로는 디자인 의도대로 **목록 행에는 요약을 그리지 않고**
> 모달에서만 보여준다(`ArticleModal.tsx`). 위 제안(목록에서 제거)은 `GET /articles/{id}`가
> 붙는 시점에 함께 적용한다.

### 요약이 없는 기사 처리

`articles.status`가 `SUMMARIZED`에 도달하지 않은 기사(수집만 됨 / `FAILED`)는
**목록에서 제외**하는 것을 제안한다.

> `status`는 `COLLECTED → SUMMARIZED → TRANSLATED` 진행 단계다. 노출 대상은
> **`SUMMARIZED` 이후 단계 전부**(`SUMMARIZED`, `TRANSLATED`)다. `TRANSLATED`는 더 진행된
> 상태지 덜 진행된 것이 아니다 — `== 'SUMMARIZED'`로만 거르면 번역 배치가 도는 순간
> 기사가 목록에서 통째로 사라진다. 이유: 목록에는 요약이 안 보이지만 행을 누르면
반드시 요약이 필요하고, 그 시점에 생성하는 건 위 절대 제약 위반이다.

- 게스트 모드: `WHERE articles.status = 'SUMMARIZED'` 조건 추가
- 로그인 모드: `feed_items`는 `summary_id NOT NULL`이므로 구조적으로 보장됨

### 응답 — 오류

| 상황 | code | HTTP |
|---|---|---|
| 존재하지 않는 `tag` | `UNKNOWN_TAG` | 400 |
| 잘못된/만료된 `cursor` | `INVALID_CURSOR` | 400 |

빈 결과는 오류가 아니다 — `articles: []`, `hasNext: false`로 200을 반환한다
(프론트가 "비어있음" 상태 화면을 그린다).

---

## GET /articles/{articleId} — 기사 상세

화면: 기사 상세 **모달** (별도 페이지가 아니라 목록 위 오버레이, design_plan.md §6.3).
URL은 `/articles/:id`로 바뀌지만 목록 위에 겹쳐 뜬다.

**이 엔드포인트가 필요한 이유**: design_plan.md §6.3이 "그 주소로 직접 들어오면 목록 위에
모달이 열린 상태로 보입니다. 링크 공유와 뒤로가기가 정상 동작해야 합니다"를 요구한다.
직접 진입 시 해당 기사가 현재 목록 페이지에 없을 수 있으므로 단건 조회가 있어야 한다.

### 요청

```
GET /api/v1/articles/128402?summaryType=THREE_LINE
```

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `summaryType` | 아니오 | `ONE_LINE` \| `THREE_LINE` \| `DETAIL` (`summaries.summary_type`). 생략 시 서버 기본값 |

### 응답 — 200

```json
{
  "success": true,
  "data": {
    "id": "128402",
    "source": "TechCrunch",
    "category": "IT",
    "headline": "OpenAI, GPT-5 출시 일정 공개…",
    "tags": ["AI", "개발"],
    "url": "https://techcrunch.com/...",
    "publishedAt": "2026-08-19T10:18:00Z",
    "summary": {
      "content": "OpenAI가 차세대 언어 모델 GPT-5의 출시 일정을 공식 발표했다. …",
      "summaryType": "THREE_LINE",
      "language": "ko"
    }
  }
}
```

| 필드 | 출처 |
|---|---|
| `summary.content` | 노출 언어 번역이 있으면 `translations.translated_content`, 없으면 `summaries.content` (아래 참고) |
| `summary.summaryType` | `summaries.summary_type` — **요청한 타입과 다를 수 있다**(아래) |
| `summary.language` | 실제 노출 언어. 번역이 쓰였으면 `translations.target_language`, 아니면 `summaries.language` |

### ⚠️ 요약 3종이 항상 있다고 가정하지 않는다

루트 CLAUDE.md §8 미결 사항: "요약 3종 저장 여부 — 배치에서 세 종류를 다 만들면 LLM
호출이 3배가 된다. '상세 1건만 저장 + 짧은 버전은 프런트에서 절단' 안과 비교 검토 필요.
(B·D 협의, 비용 추정 후 결정)"

따라서:
- 프론트는 `summaryType`을 **보낼 수는 있지만**, 요청한 타입이 없을 때 **다른 타입이
  돌아올 수 있다고 가정하고 만든다** (`summary.summaryType`으로 실제 값을 확인).
- 서버는 요청 타입이 없으면 있는 것 중 하나를 반환하고 실제 타입을 명시한다.
  **없다고 해서 그 자리에서 생성하지 않는다.**

### 번역은 별도 필드가 아니라 `content`에 담긴다

**전제가 바뀌었다.** 이 절은 원래 "번역 UI는 담당자 부재로 범위에서 제외됐으니 필드를
넣지 않는다"였는데, 그 뒤 수집 파이프라인이 실제로 번역을 만들기 시작했다
(Google Translate, `translations.provider='google'`).

번역이 이 서비스의 핵심이므로(루트 CLAUDE.md §1 "요약·번역 개인화 피드") **원문/번역을
두 필드로 나누지 않고 `content` 하나에 노출 언어 기준으로 담는다.**

| 상황 | `content` | `language` |
|---|---|---|
| 노출 언어 번역이 있다 | `translations.translated_content` | 그 번역의 `target_language` |
| 없다 | `summaries.content` | `summaries.language` |

**노출 언어를 정하는 규칙:**

| | 노출 언어 |
|---|---|
| 로그인 (개인화 피드) | `feed_items.translation_id`가 가리키는 번역의 언어 |
| 로그인 (관심 태그 0개 → 전체 최신) | `users.preferred_language` |
| 비로그인 (게스트) | 서비스 기본 언어 `ko` |

게스트에게 원문을 그대로 주지 않는다. 선호 언어를 모른다는 이유로 영어 기사의 영어 요약을
노출하면 번역이라는 핵심 기능이 화면에 드러나지 않는다. 한국어 사용자를 위한 서비스이므로
기본 언어는 `ko`다.

`translations.status='FAILED'`인 번역은 본문이 오류 문구라 노출하지 않고 원문으로 떨어진다.

**번역이 없다고 그 자리에서 만들지 않는다** (CLAUDE.md §1). 원문 요약으로 대체할 뿐이다.

> 원문/번역 토글은 아직 없다. 필요해지면 응답에 원문을 함께 내리는 형태로 계약을 넓힌다 —
> 디자인에 없는 요소라 디자인 담당 승인이 먼저다.

### 응답 — 오류

| 상황 | code | HTTP |
|---|---|---|
| 존재하지 않는 기사 | `ARTICLE_NOT_FOUND` | 404 |
| 기사는 있으나 저장된 요약이 없음 | `SUMMARY_NOT_AVAILABLE` | 404 |

`SUMMARY_NOT_AVAILABLE`을 별도 code로 두는 이유: 프론트가 "기사를 불러오지 못했습니다"
대신 "요약 준비 중"을 보여줄 수 있게 하려는 것. **이 응답을 받고 생성 요청을 보내는
경로는 만들지 않는다.**

---

## GET /tags — 태그·카테고리 마스터

화면: `/` 필터 칩, `/settings` 태그 선택, `/signup` 2단계 태그 선택.

**필요한 이유**: 현재 프론트는 태그 목록을 두 곳에 **하드코딩**하고 있다.

| 하드코딩 위치 | 내용 |
|---|---|
| `frontend/src/constants/tags.ts` | 설정·가입에서 고를 수 있는 10개 태그 |
| `frontend/src/pages/feed/NewsFeedPage.tsx` 의 `GUEST_CATEGORIES` | 게스트 필터 칩 7개 |

둘 다 스키마의 `tags` 마스터 테이블과 동기화되지 않아, 태그가 추가/비활성화되면 즉시
어긋난다. 이 엔드포인트로 전환해야 한다.

### 요청

```
GET /api/v1/tags?type=CATEGORY
```

| 파라미터 | 필수 | 설명 |
|---|---|---|
| `type` | 아니오 | `CATEGORY` \| `KEYWORD` (`tags.tag_type`). 생략 = 전체 |

`tags.is_active = TRUE` 인 것만 반환한다.

### 응답 — 200

```json
{
  "success": true,
  "data": [
    { "id": 1, "name": "AI", "slug": "ai", "tagType": "KEYWORD" },
    { "id": 2, "name": "IT", "slug": "it", "tagType": "CATEGORY" }
  ]
}
```

`id`는 `INT UNSIGNED`이므로 숫자로 직렬화해도 안전하다 (`articles.id`와 다름).

---

## 제안하지만 프론트가 아직 호출하지 않는 것

### PATCH /feed/items/{articleId}/read — 읽음 처리

design_plan.md §6.1의 "읽음" 상태(헤드라인을 `#64748B`로)를 위해 필요하다.
현재 프론트는 읽은 기사 id를 **컴포넌트 로컬 state에만** 담고 있어 새로고침하면 사라진다.
스키마에는 `feed_items.is_read`가 이미 있다.

```
PATCH /api/v1/feed/items/128402/read
→ { "success": true, "data": null }
```

로그인 사용자만 해당(게스트는 기록 주체가 없음). 401 → `UNAUTHENTICATED`.

### 북마크는 계약에 넣지 않는다

`feed_items.is_bookmarked` 컬럼이 스키마에 있고 루트 CLAUDE.md §3은 북마크를 D 담당으로
명시하지만, design_plan.md §6.3은 "공유·스크랩은 넣지 않습니다"로 제외했다.
**디자인이 없으므로 구현하지 않는다** (frontend/CLAUDE.md §0.2). 디자인이 나오면 추가한다.

---

## 열려있는 질문 (C 확인 필요)

1. **비로그인 피드 접근 허용 여부** — frontend/CLAUDE.md §0.2에서 "백엔드 확인 대기"로
   남아 있는 항목. 프론트는 두 경우 모두 동작하도록 만들어 뒀지만, 게스트에게 목록을
   열어줄지는 정책 결정이다.
2. **`isNew` 정의** — 스키마에 대응 컬럼이 없다. `published_at`이 N시간 내인지로 계산할지
   (N값 필요), 별도 플래그를 둘지. 서버 계산을 제안한다(프론트가 임의 기준을 정하면
   화면마다 달라짐).
3. **기사당 카테고리가 2개 이상일 때** — `article_tags`는 다대다이므로 `CATEGORY` 태그가
   여럿 붙을 수 있다. `relevance` 최고값 1개를 쓸지, 첫 번째를 쓸지 규칙 필요
   (프론트는 1개만 표시).
4. **`articles.source_id`가 NULL인 경우** — 출처 뱃지에 무엇을 표시할지. 서버가
   `"출처 미상"` 같은 기본값을 줄지, `null`을 주고 프론트가 처리할지.
5. **`limit` 상한** — 서버가 정하고 명시할 것.
~~6. **커서 인코딩 방식**~~ → **확정.** `(published_at, id)` 복합 커서를 base64로 감싼
   불투명 문자열이다. 프론트는 파싱하지 않고 그대로 되돌려 보낸다.

   정렬이 `published_at DESC, id DESC`이므로 `id`만으로는 이어 읽을 수 없다 — 수집
   순서(id)와 발행 순서(published_at)가 다르기 때문이다. 이전에는 `id DESC`로 정렬해
   **가장 오래된 기사가 맨 위**에 올라왔다(시드에서 최신 기사가 먼저 INSERT되므로).

   깨진 커서는 `INVALID_CURSOR`(400)로 거부한다.
7. **피드 캐시** — 스키마 하단 Redis 설계에 `feed:{user_id}:{page}` TTL 10m이 있다.
   페이지 대신 커서를 쓰면 이 키 설계도 함께 조정해야 한다.
