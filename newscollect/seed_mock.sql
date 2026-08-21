-- [이 파일은 더 이상 실행할 필요가 없다]
--
-- tags: 정식 어휘는 backend의 Alembic 리비전 0002_seed_tags가 소유한다
--   (slug = 기계 키, name = 한국어 표시명). `alembic upgrade head`를 돌렸다면
--   아래 INSERT는 INSERT IGNORE라 전부 건너뛴다.
--
-- news_sources: db.py의 _upsert_source_id()가 기사의 **언론사**(item.source)로
--   행을 직접 만든다. 언론사는 수집하면서 계속 늘어나므로 미리 시드할 수 없다.
--   아래 'naver'/'freenews' 행은 **수집 경로이지 언론사가 아니다** -- 예전에
--   기사가 이 두 행에 매달려서 피드 배지에 신문사 대신 'freenews'가 떴다.
--   지금 실행해도 새 기사는 이 행을 쓰지 않지만, 굳이 만들 이유도 없다.

USE news_ai;

-- [사용 안 함] 남겨 두는 것은 기존 기사(source_id가 이 행을 가리킨다)의 참조를
-- 끊지 않기 위해서다. 새 기사는 실제 언론사 행을 쓴다.
INSERT IGNORE INTO news_sources (name, provider, language) VALUES
  ('naver',    'NEWS_API', 'ko'),
  ('freenews', 'NEWS_API', 'en');

-- db.py의 _lookup_tag_id()가 --category 값을 name으로 그대로 매칭한다 (slug 아님).
-- slug는 실제 값 체계가 아직 안 정해져서 db.py가 참조하지 않는다 -- 여기서는
-- NOT NULL UNIQUE 제약을 만족시키기 위한 자리채움(placeholder)일 뿐이다.
-- providers/base.py의 CATEGORIES 63개 전부를 시드한다.
INSERT IGNORE INTO tags (tag_type, name, slug) VALUES
  ('CATEGORY', 'arts-design', 'arts-design'),
  ('CATEGORY', 'baseball', 'baseball'),
  ('CATEGORY', 'basketball', 'basketball'),
  ('CATEGORY', 'beauty', 'beauty'),
  ('CATEGORY', 'business', 'business'),
  ('CATEGORY', 'celebrities', 'celebrities'),
  ('CATEGORY', 'combat sports', 'combat-sports'),
  ('CATEGORY', 'cricket', 'cricket'),
  ('CATEGORY', 'cycling', 'cycling'),
  ('CATEGORY', 'digital currencies', 'digital-currencies'),
  ('CATEGORY', 'economy', 'economy'),
  ('CATEGORY', 'education', 'education'),
  ('CATEGORY', 'energy', 'energy'),
  ('CATEGORY', 'entertainment', 'entertainment'),
  ('CATEGORY', 'environment', 'environment'),
  ('CATEGORY', 'fashion', 'fashion'),
  ('CATEGORY', 'finance', 'finance'),
  ('CATEGORY', 'food', 'food'),
  ('CATEGORY', 'football', 'football'),
  ('CATEGORY', 'gadgets', 'gadgets'),
  ('CATEGORY', 'gaming', 'gaming'),
  ('CATEGORY', 'geology', 'geology'),
  ('CATEGORY', 'golf', 'golf'),
  ('CATEGORY', 'health', 'health'),
  ('CATEGORY', 'higher education', 'higher-education'),
  ('CATEGORY', 'hockey', 'hockey'),
  ('CATEGORY', 'home', 'home'),
  ('CATEGORY', 'internet security', 'internet-security'),
  ('CATEGORY', 'jobs', 'jobs'),
  ('CATEGORY', 'medicine', 'medicine'),
  ('CATEGORY', 'mental health', 'mental-health'),
  ('CATEGORY', 'mobile', 'mobile'),
  ('CATEGORY', 'motor sports', 'motor-sports'),
  ('CATEGORY', 'movies', 'movies'),
  ('CATEGORY', 'music', 'music'),
  ('CATEGORY', 'neuroscience', 'neuroscience'),
  ('CATEGORY', 'nutrition', 'nutrition'),
  ('CATEGORY', 'online education', 'online-education'),
  ('CATEGORY', 'outdoors', 'outdoors'),
  ('CATEGORY', 'paleontology', 'paleontology'),
  ('CATEGORY', 'personal finance', 'personal-finance'),
  ('CATEGORY', 'physics', 'physics'),
  ('CATEGORY', 'politics', 'politics'),
  ('CATEGORY', 'public health', 'public-health'),
  ('CATEGORY', 'robotics', 'robotics'),
  ('CATEGORY', 'rugby', 'rugby'),
  ('CATEGORY', 'science', 'science'),
  ('CATEGORY', 'shopping', 'shopping'),
  ('CATEGORY', 'soccer', 'soccer'),
  ('CATEGORY', 'social sciences', 'social-sciences'),
  ('CATEGORY', 'space', 'space'),
  ('CATEGORY', 'sports', 'sports'),
  ('CATEGORY', 'sports betting', 'sports-betting'),
  ('CATEGORY', 'technology', 'technology'),
  ('CATEGORY', 'tennis', 'tennis'),
  ('CATEGORY', 'theater', 'theater'),
  ('CATEGORY', 'travel', 'travel'),
  ('CATEGORY', 'tv', 'tv'),
  ('CATEGORY', 'vehicles', 'vehicles'),
  ('CATEGORY', 'virtual reality', 'virtual-reality'),
  ('CATEGORY', 'water sports', 'water-sports'),
  ('CATEGORY', 'wildlife', 'wildlife'),
  ('CATEGORY', 'world', 'world');
