-- =====================================================================
-- AI 뉴스 요약/번역 서비스 스키마
-- Stack: React + FastAPI + MySQL 8.0 + Redis(세션 / 캐시)
-- 배치 실행 기술(스케줄러/큐)은 미정 — 스키마는 특정 실행기에 결합하지 않는다.
-- Charset: utf8mb4 / Collation: utf8mb4_0900_ai_ci / Engine: InnoDB
-- =====================================================================

CREATE DATABASE IF NOT EXISTS news_ai
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_0900_ai_ci;
USE news_ai;

-- ---------------------------------------------------------------------
-- 1. 회원 / 개인화
-- ---------------------------------------------------------------------

CREATE TABLE users (
  id                    BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  email                 VARCHAR(255)    NOT NULL,
  password_hash         VARCHAR(255)    NOT NULL,
  nickname              VARCHAR(50)     NOT NULL,
  role                  ENUM('USER','ADMIN') NOT NULL DEFAULT 'USER',
  preferred_language    CHAR(5)         NOT NULL DEFAULT 'ko',
  default_summary_type  ENUM('ONE_LINE','THREE_LINE','DETAIL') NOT NULL DEFAULT 'THREE_LINE',
  status                ENUM('ACTIVE','DORMANT','WITHDRAWN') NOT NULL DEFAULT 'ACTIVE',
  last_login_at         DATETIME        NULL,
  created_at            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at            DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_users_email (email),
  KEY idx_users_status (status)
) ENGINE=InnoDB COMMENT='회원. 세션 자체는 Redis, 영속 정보만 MySQL';

CREATE TABLE tags (
  id         INT UNSIGNED NOT NULL AUTO_INCREMENT,
  tag_type   ENUM('CATEGORY','KEYWORD') NOT NULL,
  name       VARCHAR(100) NOT NULL,
  slug       VARCHAR(120) NOT NULL,
  is_active  BOOLEAN      NOT NULL DEFAULT TRUE,
  created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_tags_slug (slug),
  KEY idx_tags_type_active (tag_type, is_active)
) ENGINE=InnoDB COMMENT='카테고리/키워드 통합 태그 마스터';

CREATE TABLE user_tags (
  id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id    BIGINT UNSIGNED NOT NULL,
  tag_id     INT UNSIGNED    NOT NULL,
  priority   TINYINT UNSIGNED NOT NULL DEFAULT 5 COMMENT '큐레이션 가중치 1~10',
  created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_user_tags (user_id, tag_id),
  KEY idx_user_tags_tag (tag_id),
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
  UNIQUE KEY uk_sources_name (name),
  KEY idx_sources_active (is_active)
) ENGINE=InnoDB COMMENT='언론사/뉴스 공급자';

CREATE TABLE batch_jobs (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_type       ENUM('COLLECT','SUMMARIZE','TRANSLATE','FEED','RETENTION') NOT NULL,
  slot           ENUM('0700','1200','1700','MANUAL') NOT NULL DEFAULT 'MANUAL',
  task_ref       VARCHAR(64)  NULL COMMENT '배치 실행기 식별자(기술 미정, 중복 실행 방지용)',
  status         ENUM('PENDING','RUNNING','SUCCESS','PARTIAL','FAILED') NOT NULL DEFAULT 'PENDING',
  target_count   INT UNSIGNED NOT NULL DEFAULT 0,
  success_count  INT UNSIGNED NOT NULL DEFAULT 0,
  fail_count     INT UNSIGNED NOT NULL DEFAULT 0,
  started_at     DATETIME     NULL,
  finished_at    DATETIME     NULL,
  created_at     DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_jobs_task_ref (task_ref),
  KEY idx_jobs_type_status (job_type, status, created_at)
) ENGINE=InnoDB COMMENT='배치 실행 단위(1일 3회 고정). 실행 기술 무관';

CREATE TABLE collection_filters (
  id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
  source_id   INT UNSIGNED NULL COMMENT 'NULL이면 전체 소스 대상',
  filter_type ENUM('KEYWORD','CATEGORY','PRESS') NOT NULL,
  value       VARCHAR(200) NOT NULL,
  is_include  BOOLEAN      NOT NULL DEFAULT TRUE COMMENT 'TRUE=포함, FALSE=제외',
  is_active   BOOLEAN      NOT NULL DEFAULT TRUE,
  created_by  BIGINT UNSIGNED NULL,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_filters_active (is_active, filter_type),
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
  PRIMARY KEY (id, published_at),
  UNIQUE KEY uk_articles_url_hash (url_hash, published_at),
  KEY idx_articles_published (published_at DESC),
  KEY idx_articles_status (status, published_at),
  KEY idx_articles_source (source_id, published_at),
  FULLTEXT KEY ft_articles_title (title) WITH PARSER ngram
) ENGINE=InnoDB COMMENT='원문 기사. published_at 기준 월 단위 파티셔닝'
PARTITION BY RANGE COLUMNS (published_at) (
  PARTITION p2026_07 VALUES LESS THAN ('2026-08-01'),
  PARTITION p2026_08 VALUES LESS THAN ('2026-09-01'),
  PARTITION p2026_09 VALUES LESS THAN ('2026-10-01'),
  PARTITION p_max    VALUES LESS THAN (MAXVALUE)
);
-- 주의: 파티셔닝 테이블은 파티션 키가 모든 UNIQUE/PK에 포함되어야 하므로
--       외부 FK 대상이 될 수 없습니다. articles를 참조하는 자식 테이블은
--       애플리케이션 레벨 무결성으로 관리합니다(아래 테이블들의 FK 주석 참고).

CREATE TABLE article_tags (
  article_id BIGINT UNSIGNED NOT NULL,
  tag_id     INT UNSIGNED    NOT NULL,
  relevance  DECIMAL(4,3)    NOT NULL DEFAULT 1.000,
  PRIMARY KEY (article_id, tag_id),
  KEY idx_article_tags_tag (tag_id, article_id),
  CONSTRAINT fk_article_tags_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='기사-태그 매핑. 큐레이션 매칭의 핵심 인덱스';

CREATE TABLE job_logs (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id      BIGINT UNSIGNED NOT NULL,
  article_id  BIGINT UNSIGNED NULL,
  level       ENUM('INFO','WARN','ERROR') NOT NULL DEFAULT 'INFO',
  error_code  VARCHAR(50)  NULL,
  message     TEXT         NULL,
  retry_count TINYINT UNSIGNED NOT NULL DEFAULT 0,
  created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_logs_job (job_id, level),
  KEY idx_logs_created (created_at),
  CONSTRAINT fk_logs_job FOREIGN KEY (job_id) REFERENCES batch_jobs(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='수집/처리 오류 및 재시도 로그';

-- ---------------------------------------------------------------------
-- 3. AI 요약 / 번역
-- ---------------------------------------------------------------------

CREATE TABLE summaries (
  id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  article_id     BIGINT UNSIGNED NOT NULL,
  summary_type   ENUM('ONE_LINE','THREE_LINE','DETAIL') NOT NULL,
  content        TEXT            NOT NULL,
  language       CHAR(5)         NOT NULL DEFAULT 'ko',
  model_id       VARCHAR(100)    NOT NULL COMMENT 'bedrock model id',
  prompt_version VARCHAR(20)     NOT NULL DEFAULT 'v1',
  review_status  ENUM('PENDING','OK','FLAGGED') NOT NULL DEFAULT 'PENDING',
  created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_summaries (article_id, summary_type) COMMENT '동일 조합 재호출 방지',
  KEY idx_summaries_review (review_status, created_at)
) ENGINE=InnoDB COMMENT='Bedrock 요약 결과 영구 저장';

CREATE TABLE translations (
  id                 BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  summary_id         BIGINT UNSIGNED NOT NULL,
  target_language    CHAR(5)         NOT NULL,
  translated_title   VARCHAR(500)    NULL,
  translated_content TEXT            NOT NULL,
  model_id           VARCHAR(100)    NOT NULL,
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
  KEY idx_reviews_summary (summary_id),
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
  matched_tag_id INT UNSIGNED    NULL,
  score          DECIMAL(6,3)    NOT NULL DEFAULT 0,
  is_read        BOOLEAN         NOT NULL DEFAULT FALSE,
  is_bookmarked  BOOLEAN         NOT NULL DEFAULT FALSE,
  created_at     DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_feed (user_id, article_id),
  KEY idx_feed_list (user_id, created_at DESC, score DESC),
  KEY idx_feed_bookmark (user_id, is_bookmarked),
  CONSTRAINT fk_feed_user    FOREIGN KEY (user_id)        REFERENCES users(id)        ON DELETE CASCADE,
  CONSTRAINT fk_feed_summary FOREIGN KEY (summary_id)     REFERENCES summaries(id)    ON DELETE CASCADE,
  CONSTRAINT fk_feed_trans   FOREIGN KEY (translation_id) REFERENCES translations(id) ON DELETE SET NULL,
  CONSTRAINT fk_feed_tag     FOREIGN KEY (matched_tag_id) REFERENCES tags(id)         ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='배치가 미리 만들어 둔 개인화 피드. 조회 시 Bedrock 미호출';

-- ---------------------------------------------------------------------
-- 5. 운영 (비용 / 보관)
-- ---------------------------------------------------------------------

CREATE TABLE ai_invocations (
  id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  job_id        BIGINT UNSIGNED NULL,
  article_id    BIGINT UNSIGNED NULL,
  task_type     ENUM('SUMMARIZE','TRANSLATE') NOT NULL,
  model_id      VARCHAR(100)  NOT NULL,
  input_tokens  INT UNSIGNED  NOT NULL DEFAULT 0,
  output_tokens INT UNSIGNED  NOT NULL DEFAULT 0,
  cost_usd      DECIMAL(10,6) NOT NULL DEFAULT 0,
  latency_ms    INT UNSIGNED  NULL,
  status        ENUM('SUCCESS','FAILED') NOT NULL DEFAULT 'SUCCESS',
  created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_inv_created (created_at),
  KEY idx_inv_job (job_id),
  CONSTRAINT fk_inv_job FOREIGN KEY (job_id) REFERENCES batch_jobs(id) ON DELETE SET NULL
) ENGINE=InnoDB COMMENT='Bedrock 호출 단위 비용/사용량 추적';

CREATE TABLE cost_budgets (
  id              INT UNSIGNED  NOT NULL AUTO_INCREMENT,
  period_type     ENUM('DAILY','MONTHLY') NOT NULL,
  threshold_usd   DECIMAL(10,2) NULL,
  threshold_calls INT UNSIGNED  NULL,
  notify_channel  VARCHAR(100)  NOT NULL COMMENT 'slack webhook / email 등',
  is_active       BOOLEAN       NOT NULL DEFAULT TRUE,
  created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id)
) ENGINE=InnoDB COMMENT='비용/호출 임계치 설정';

CREATE TABLE cost_alerts (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  budget_id    INT UNSIGNED    NOT NULL,
  actual_cost  DECIMAL(10,2)   NOT NULL DEFAULT 0,
  actual_calls INT UNSIGNED    NOT NULL DEFAULT 0,
  is_notified  BOOLEAN         NOT NULL DEFAULT FALSE,
  triggered_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_alerts_budget (budget_id, triggered_at),
  CONSTRAINT fk_alerts_budget FOREIGN KEY (budget_id) REFERENCES cost_budgets(id) ON DELETE CASCADE
) ENGINE=InnoDB COMMENT='임계치 초과 알림 이력';

CREATE TABLE retention_policies (
  id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
  target_entity    ENUM('ARTICLES','SUMMARIES','TRANSLATIONS','FEED_ITEMS','LOGS') NOT NULL,
  retention_days   INT UNSIGNED NOT NULL,
  strategy         ENUM('PARTITION_DROP','BATCH_DELETE') NOT NULL DEFAULT 'BATCH_DELETE',
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
