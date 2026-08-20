-- =====================================================================
-- AI 뉴스 요약/번역 서비스 스키마 — V2
-- Stack: React + FastAPI + MySQL 8.0 + Redis(세션 / 캐시)
-- Charset: utf8mb4 / Collation: utf8mb4_0900_ai_ci / Engine: InnoDB
--
-- 배치 실행 기술(스케줄러/큐)은 미정 — 스키마는 특정 실행기에 결합하지 않는다.
-- 같은 기준으로 LLM 클라이언트 라이브러리명도 스키마에 박지 않는다. 프로바이더와
-- 모델은 provider / model_name 컬럼에 실행 시점 값으로 기록한다. (CLAUDE.md §8.2)
--
-- [이 파일의 성격]
-- 조회 성능용 보조 인덱스(KEY)와 전문검색 인덱스(FULLTEXT)를 제외했습니다.
-- 남긴 제약은 전부 업무 규칙에 해당합니다.
--   - PRIMARY KEY : 식별자
--   - FOREIGN KEY : 관계 및 참조 무결성
--   - UNIQUE KEY  : 중복 방지 규칙
-- 인덱스는 실제 쿼리 패턴을 EXPLAIN으로 확인한 뒤 추가합니다.
-- 파일 하단에 추가 후보를 정리해 두었습니다.
--
-- [V1.1 대비 변경 사항]
--   1. 보조 인덱스(KEY), FULLTEXT 인덱스 제거
--   2. articles 파티셔닝 제거 (§8 "파티셔닝 vs FK" 미결 사항을 FK 쪽으로 확정)
--      → 복합 PK가 단일 PK로 단순화
--      → articles를 참조하는 자식 테이블에 실제 FK 설정 가능
--      → uk_articles_url_hash 가 (url_hash, published_at) 복합에서 단일 컬럼으로
--        돌아와 중복 제거 규칙(§8.3)이 비로소 실제로 동작한다.
--        V1.1에서는 published_at 만 다르면 같은 url_hash 가 통과했다.
--   3. 단일 프로바이더(Bedrock) 전제를 제거하고 다중 프로바이더 구조 반영
--      → model_id 단일 컬럼을 provider + model_name 으로 분리
--      → is_token_estimated, is_fallback 컬럼 추가
--   4. articles → summaries / feed_items FK를 RESTRICT로 지정
--      → 요약이 남아 있는 articles는 삭제 자체가 실패한다
--      → 보관 배치가 원문을 지우면서 LLM 결과를 연쇄 삭제하는 사고를 차단
--      → 삭제가 필요하면 순서를 명시해야 한다 (아래 [삭제 순서] 참고)
--   5. retention_policies.strategy 에서 PARTITION_DROP 제거
--      → 파티셔닝을 뺐으므로 실행 불가능한 값이다. 관리자 화면에 고를 수 없는
--        선택지가 뜨거나 배치가 런타임에 실패하는 경로를 없앤다.
--   6. LLM 호출량/비용 추적을 스코프에서 제외 (팀 결정)
--      → ai_invocations / cost_budgets / cost_alerts 테이블 제거
--      → retention_policies.target_entity 에서 INVOCATIONS 제거 (가리킬 테이블이 없다)
--      → 프로바이더를 Groq 하나로 고정하면서 프로바이더별 비용 비교의 실익이 사라졌다.
--        summaries/translations 의 provider·model_name 은 남긴다 — 비용이 아니라
--        "어떤 모델이 만든 결과인가"를 기록하는 값이라 품질 추적에 계속 쓰인다.
--
-- [삭제 순서]
-- articles 행을 실제로 지워야 한다면 다음 순서만 허용됩니다.
--   1) DELETE summaries  → translations, feed_items 가 CASCADE로 함께 정리됨
--   2) DELETE articles   → article_tags 가 CASCADE로 함께 정리됨
-- 즉 "요약을 버린다"는 판단을 먼저 명시적으로 해야 원문을 지울 수 있습니다.
-- 요약을 보존하면서 저장공간만 줄이려면 articles.content 를 NULL 로 만드는
-- soft purge 를 쓰고, 행은 남깁니다.
-- =====================================================================

CREATE DATABASE IF NOT EXISTS news_ai
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE news_ai;


-- ---------------------------------------------------------------------
-- 1. 회원 / 개인화
-- ---------------------------------------------------------------------

CREATE TABLE users (
  id                   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email                VARCHAR(255)    NOT NULL,
  password_hash        VARCHAR(255)    NOT NULL,
  nickname             VARCHAR(50)     NOT NULL,
  role                 ENUM('USER','ADMIN')                  NOT NULL DEFAULT 'USER',
  preferred_language   CHAR(5)         NOT NULL DEFAULT 'ko',
  default_summary_type ENUM('ONE_LINE','THREE_LINE','DETAIL') NOT NULL DEFAULT 'THREE_LINE',
  status               ENUM('ACTIVE','DORMANT','WITHDRAWN')   NOT NULL DEFAULT 'ACTIVE',
  last_login_at        DATETIME        NULL,
  created_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at           DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP
                                       ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_email (email)
) ENGINE=InnoDB COMMENT='회원. 세션 자체는 Redis, 영속 정보만 MySQL';


CREATE TABLE tags (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tag_type   ENUM('CATEGORY','KEYWORD') NOT NULL,
  name       VARCHAR(100) NOT NULL,
  slug       VARCHAR(120) NOT NULL,
  is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tags_slug (slug)
) ENGINE=InnoDB COMMENT='카테고리/키워드 통합 태그 마스터';


CREATE TABLE user_tags (
  id         BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED  NOT NULL,
  tag_id     INT UNSIGNED     NOT NULL,
  priority   TINYINT UNSIGNED NOT NULL DEFAULT 5 COMMENT '큐레이션 가중치 1~10',
  created_at DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_tags (user_id, tag_id),
  CONSTRAINT fk_user_tags_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
  CONSTRAINT fk_user_tags_tag  FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='사용자 관심 태그';


-- ---------------------------------------------------------------------
-- 2. 수집
-- ---------------------------------------------------------------------

CREATE TABLE news_sources (
  id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
  name         VARCHAR(100) NOT NULL,
  provider     VARCHAR(50)  NOT NULL COMMENT 'NEWS_API / RSS 등',
  api_endpoint VARCHAR(500) NULL,
  country      CHAR(2)      NULL,
  language     CHAR(5)      NOT NULL DEFAULT 'ko',
  is_active    BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_sources_name (name)
) ENGINE=InnoDB COMMENT='언론사/뉴스 공급자';


CREATE TABLE batch_jobs (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_type      ENUM('COLLECT','SUMMARIZE','TRANSLATE','FEED','RETENTION') NOT NULL,
  slot          ENUM('0700','1200','1700','MANUAL') NOT NULL DEFAULT 'MANUAL',
  task_ref      VARCHAR(64)  NULL COMMENT '배치 실행기 식별자. 중복 실행 방지용',
  status        ENUM('PENDING','RUNNING','SUCCESS','PARTIAL','FAILED') NOT NULL DEFAULT 'PENDING',
  target_count  INT UNSIGNED NOT NULL DEFAULT 0,
  success_count INT UNSIGNED NOT NULL DEFAULT 0,
  fail_count    INT UNSIGNED NOT NULL DEFAULT 0,
  started_at    DATETIME     NULL,
  finished_at   DATETIME     NULL,
  created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_jobs_task_ref (task_ref)
) ENGINE=InnoDB COMMENT='배치 실행 단위(1일 3회 고정). 실행 기술 무관';


CREATE TABLE collection_filters (
  id          INT UNSIGNED    NOT NULL AUTO_INCREMENT,
  source_id   INT UNSIGNED    NULL COMMENT 'NULL이면 전체 소스 대상',
  filter_type ENUM('KEYWORD','CATEGORY','PRESS') NOT NULL,
  value       VARCHAR(200)    NOT NULL,
  is_include  BOOLEAN         NOT NULL DEFAULT TRUE COMMENT 'TRUE=포함, FALSE=제외',
  is_active   BOOLEAN         NOT NULL DEFAULT TRUE,
  created_by  BIGINT UNSIGNED NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_filters_source FOREIGN KEY (source_id)  REFERENCES news_sources(id) ON DELETE CASCADE,
  CONSTRAINT fk_filters_admin  FOREIGN KEY (created_by) REFERENCES users(id)        ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='수집 대상 필터링 규칙';


CREATE TABLE articles (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id      INT UNSIGNED    NULL,
  collect_job_id BIGINT UNSIGNED NULL,
  url            VARCHAR(1000)   NOT NULL,
  url_hash       CHAR(64)        NOT NULL COMMENT 'SHA-256(정규화 URL). 중복 제거 기준',
  title          VARCHAR(500)    NOT NULL,
  content        LONGTEXT        NULL,
  author         VARCHAR(200)    NULL,
  language       CHAR(5)         NOT NULL DEFAULT 'ko',
  image_url      VARCHAR(1000)   NULL,
  status         ENUM('COLLECTED','SUMMARIZED','TRANSLATED','FAILED') NOT NULL DEFAULT 'COLLECTED',
  published_at   DATETIME        NOT NULL,
  created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_articles_url_hash (url_hash),
  CONSTRAINT fk_articles_source FOREIGN KEY (source_id)      REFERENCES news_sources(id) ON DELETE SET NULL,
  CONSTRAINT fk_articles_job    FOREIGN KEY (collect_job_id) REFERENCES batch_jobs(id)   ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='원문 기사';


CREATE TABLE article_tags (
  article_id BIGINT UNSIGNED NOT NULL,
  tag_id     INT UNSIGNED    NOT NULL,
  relevance  DECIMAL(4,3)    NOT NULL DEFAULT 1.000,
  PRIMARY KEY (article_id, tag_id),
  CONSTRAINT fk_article_tags_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE CASCADE,
  CONSTRAINT fk_article_tags_tag     FOREIGN KEY (tag_id)     REFERENCES tags(id)     ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='기사-태그 매핑. 큐레이션 매칭 기준';


CREATE TABLE job_logs (
  id          BIGINT UNSIGNED  NOT NULL AUTO_INCREMENT,
  job_id      BIGINT UNSIGNED  NOT NULL,
  article_id  BIGINT UNSIGNED  NULL,
  level       ENUM('INFO','WARN','ERROR') NOT NULL DEFAULT 'INFO',
  error_code  VARCHAR(50)      NULL,
  message     TEXT             NULL,
  retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
  created_at  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_logs_job     FOREIGN KEY (job_id)     REFERENCES batch_jobs(id) ON DELETE CASCADE,
  CONSTRAINT fk_logs_article FOREIGN KEY (article_id) REFERENCES articles(id)   ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='수집/처리 오류 및 재시도 로그';


-- ---------------------------------------------------------------------
-- 3. AI 요약 / 번역 (다중 프로바이더)
-- ---------------------------------------------------------------------

CREATE TABLE summaries (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  article_id     BIGINT UNSIGNED NOT NULL,
  summary_type   ENUM('ONE_LINE','THREE_LINE','DETAIL') NOT NULL,
  content        TEXT            NOT NULL,
  language       CHAR(5)         NOT NULL DEFAULT 'ko',
  provider       VARCHAR(50)     NOT NULL COMMENT 'openai / anthropic / google 등',
  model_name     VARCHAR(100)    NOT NULL COMMENT '호출 시점의 실제 모델',
  prompt_version VARCHAR(20)     NOT NULL DEFAULT 'v1',
  review_status  ENUM('PENDING','OK','FLAGGED') NOT NULL DEFAULT 'PENDING',
  created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_summaries (article_id, summary_type) COMMENT '동일 조합 재호출 방지',
  -- RESTRICT: 요약이 남아 있으면 원문 삭제를 막는다.
  -- 원문은 URL로 재수집 가능하지만 요약은 LLM을 다시 호출해야 하므로,
  -- 보관 배치가 원문을 지우면서 비용을 태워 만든 결과를 함께 날리는 것을 차단한다.
  CONSTRAINT fk_summaries_article FOREIGN KEY (article_id) REFERENCES articles(id) ON DELETE RESTRICT
) ENGINE=InnoDB COMMENT='LLM 요약 결과 영구 저장. 조회 시 재호출 없이 재사용';


CREATE TABLE translations (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  summary_id         BIGINT UNSIGNED NOT NULL,
  target_language    CHAR(5)         NOT NULL,
  translated_title   VARCHAR(500)    NULL,
  translated_content TEXT            NOT NULL,
  provider           VARCHAR(50)     NOT NULL,
  model_name         VARCHAR(100)    NOT NULL,
  status             ENUM('DONE','FAILED') NOT NULL DEFAULT 'DONE',
  created_at         DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_translations (summary_id, target_language) COMMENT '동일 언어 재호출 방지',
  CONSTRAINT fk_translations_summary FOREIGN KEY (summary_id) REFERENCES summaries(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='요약문의 다국어 번역 결과';


CREATE TABLE summary_reviews (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  summary_id  BIGINT UNSIGNED NOT NULL,
  reviewer_id BIGINT UNSIGNED NULL,
  verdict     ENUM('OK','HALLUCINATION','OMISSION','OTHER') NOT NULL,
  note        TEXT            NULL,
  created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  CONSTRAINT fk_reviews_summary  FOREIGN KEY (summary_id)  REFERENCES summaries(id) ON DELETE CASCADE,
  CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id)     ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='관리자 환각/누락 검수 이력';


-- ---------------------------------------------------------------------
-- 4. 배포 (개인화 피드)
-- ---------------------------------------------------------------------

CREATE TABLE feed_items (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id        BIGINT UNSIGNED NOT NULL,
  article_id     BIGINT UNSIGNED NOT NULL,
  summary_id     BIGINT UNSIGNED NOT NULL,
  translation_id BIGINT UNSIGNED NULL COMMENT '원문 언어와 동일하면 NULL',
  matched_tag_id INT UNSIGNED    NULL COMMENT '이 기사가 노출된 사유',
  score          DECIMAL(6,3)    NOT NULL DEFAULT 0,
  is_read        BOOLEAN         NOT NULL DEFAULT FALSE,
  is_bookmarked  BOOLEAN         NOT NULL DEFAULT FALSE,
  created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_feed (user_id, article_id),
  CONSTRAINT fk_feed_user    FOREIGN KEY (user_id)        REFERENCES users(id)        ON DELETE CASCADE,
  -- RESTRICT: 원문 삭제로 피드 행이 조용히 사라지지 않게 한다.
  -- 피드는 summaries 로부터 curate 배치가 재생성할 수 있으므로,
  -- 정리는 summaries 삭제(→ CASCADE) 경로로만 일어나야 한다.
  CONSTRAINT fk_feed_article FOREIGN KEY (article_id)     REFERENCES articles(id)     ON DELETE RESTRICT,
  CONSTRAINT fk_feed_summary FOREIGN KEY (summary_id)     REFERENCES summaries(id)    ON DELETE CASCADE,
  CONSTRAINT fk_feed_trans   FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE SET NULL,
  CONSTRAINT fk_feed_tag     FOREIGN KEY (matched_tag_id) REFERENCES tags(id)         ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='배치가 미리 만들어 둔 개인화 피드. 조회 시 LLM 미호출';


-- ---------------------------------------------------------------------
-- 5. 운영 (데이터 보관)
-- ---------------------------------------------------------------------







CREATE TABLE retention_policies (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  target_entity    ENUM('ARTICLES','SUMMARIES','TRANSLATIONS','FEED_ITEMS','LOGS') NOT NULL,
  retention_days   INT UNSIGNED NOT NULL,
  -- V1.1의 PARTITION_DROP은 제거했다. articles 파티셔닝을 뺐으므로 실행할 수 없는 값이고,
  -- ENUM에 남겨 두면 관리자 화면의 선택지로 노출돼 배치가 런타임에 실패한다.
  -- 파티셔닝을 재도입하면 그때 ENUM을 넓히는 마이그레이션을 낸다.
  strategy         ENUM('BATCH_DELETE') NOT NULL DEFAULT 'BATCH_DELETE',
  last_executed_at DATETIME     NULL,
  is_active        BOOLEAN      NOT NULL DEFAULT TRUE,
  PRIMARY KEY (id),
  UNIQUE KEY uk_retention_target (target_entity)
) ENGINE=InnoDB COMMENT='데이터 보관 기간/TTL 정책';


-- =====================================================================
-- Redis 키 설계 (MySQL 테이블 아님, 참고용)
-- ---------------------------------------------------------------------
-- session:{session_id}            HASH   TTL 30m   로그인 세션
-- refresh:{user_id}:{jti}         STRING TTL 14d   리프레시 토큰 화이트리스트
-- dedup:url:{yyyymmdd}            SET    TTL 48h   INSERT 전 URL 해시 선필터
-- feed:{user_id}:{page}           STRING TTL 10m   피드 응답 캐시
-- article:summary:{article_id}    HASH   TTL 1h    상세 조회 캐시
-- lock:job:{job_type}:{slot}      STRING TTL 30m   배치 중복 실행 방지
-- ratelimit:{user_id}:{endpoint}  STRING TTL 1m    API 레이트리밋
-- (배치 브로커 용도는 실행 기술 확정 후 추가)
-- =====================================================================


-- =====================================================================
-- 성능 튜닝 시 추가할 인덱스 (지금은 의도적으로 제외)
-- ---------------------------------------------------------------------
-- 실제 쿼리를 EXPLAIN으로 확인한 뒤 필요한 것만 추가하세요.
-- FK 컬럼에는 MySQL이 자동으로 인덱스를 생성하므로 중복 생성하지 않습니다.
--
-- 피드 목록 조회 (가장 빈번)
--   ALTER TABLE feed_items   ADD KEY idx_feed_list (user_id, created_at DESC, score DESC);
--   ALTER TABLE feed_items   ADD KEY idx_feed_bookmark (user_id, is_bookmarked);
--
-- 기사 목록 / 커서 페이지네이션
--   ALTER TABLE articles     ADD KEY idx_articles_published (published_at DESC, id DESC);
--   ALTER TABLE articles     ADD KEY idx_articles_status (status, published_at);
--
-- 큐레이션 역방향 매칭 (태그로 기사 찾기)
--   ALTER TABLE article_tags ADD KEY idx_article_tags_tag (tag_id, article_id);
--
-- 관리자 화면
--   ALTER TABLE batch_jobs   ADD KEY idx_jobs_type_status (job_type, status, created_at);
--   ALTER TABLE job_logs     ADD KEY idx_logs_job_level (job_id, level);
--   ALTER TABLE summaries    ADD KEY idx_summaries_review (review_status, created_at);
--
-- 제목 검색 (검색 기능 구현 시)
--   ALTER TABLE articles     ADD FULLTEXT KEY ft_articles_title (title) WITH PARSER ngram;
--
-- 활성 레코드 필터
--   ALTER TABLE tags         ADD KEY idx_tags_type_active (tag_type, is_active);
--   ALTER TABLE news_sources ADD KEY idx_sources_active (is_active);
-- =====================================================================


-- =====================================================================
-- 추가 검토 항목
-- ---------------------------------------------------------------------
-- 1. articles 파티셔닝  → FK 쪽으로 확정 (V2)
--    보관 정책을 PARTITION_DROP으로 처리하려면 published_at 기준 파티셔닝이 필요하지만,
--    파티셔닝하면 파티션 키가 모든 UNIQUE/PK에 포함되어야 하고
--    해당 테이블은 FK 대상이 될 수 없습니다.
--    → V2는 FK를 유지하는 쪽으로 확정했습니다.
--      일 수천 건 규모에서는 BATCH_DELETE로 충분하고,
--      참조 무결성을 DB가 보장하는 편이 애플리케이션 부담이 적습니다.
--      url_hash 유니크가 정상 동작하게 되는 것이 부수 효과로 따라옵니다.
--
-- 3. 원문 선택 삭제  → RESTRICT + hard delete 로 확정 (V2)
--    articles → summaries / feed_items FK 를 RESTRICT 로 두었으므로,
--    보관 배치가 articles 를 지우려 하면 요약이 남아 있는 한 실패합니다.
--    ARTICLES 정책은 **hard delete** 로 정했습니다 — "요약을 버린다"는 판단을 명시적으로
--    먼저 내린 뒤 원문을 지웁니다. 구현은 backend/app/modules/feed/services/retention_service.py.
--    strategy 값의 의미가 그대로 "행 삭제"로 유지되므로 retention_policies 표현은 바꾸지
--    않았습니다. (soft purge 안은 채택하지 않았습니다.)
--
-- 4. retention_policies.strategy 의 PARTITION_DROP  → 제거 완료 (V2)
--    파티셔닝을 제거했으므로 실행 불가능한 값이라 ENUM 에서 뺐습니다.
--    파티셔닝을 재도입하면 그때 ENUM 을 넓히는 마이그레이션을 냅니다.
--
-- 5. 헤더의 특정 라이브러리명 표기  → 제거 완료 (V2)
--    루트 CLAUDE.md §8.2 는 "스키마를 특정 실행 기술에 결합하지 않는다"를
--    확정 사항으로 두고 있고, 그 근거로 celery_task_id → task_ref 로 개명했습니다.
--    같은 원칙을 LLM 클라이언트에도 적용해 헤더에서 라이브러리명을 빼고,
--    프로바이더/모델은 provider / model_name 컬럼 값으로만 기록합니다.
--
-- =====================================================================
