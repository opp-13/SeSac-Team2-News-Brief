# newscollect

카테고리 기반 뉴스 수집 파이프라인 PoC. NAVER 뉴스 검색 API와 Free News API에서 기사를 검색(search) → 필요하면 본문을 조회(detail) → 발행일순으로 정렬해 출력(output)한다.

## 설치

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

pip install -e ".[dev]"        # ruff 포함 설치
```

`.env.example`을 복사해 `.env`를 만들고 값을 채운다.

만약 번역/요약/DB 저장/유사도 dedup까지 하려면 아래 명령어로 의존성을 완성시킵니다.

```bash
# GPU 인스턴스가 아니면 CPU 전용 torch를 먼저 깔 것 (용량 최적화)
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -e ".[deploy]"   # pymysql, googletrans, sentence-transformers, scikit-learn
```


```bash
mysql -h 127.0.0.1 -u root news_ai < seed_mock.sql
```

## CLI 사용법

```bash
python main.py --category <카테고리> [--provider all|naver|freenews] [--display N] [--with-body]
```

| 옵션 | 필수 | 기본값 | 설명 |
|---|---|---|---|
| `--category` | O | - | 검색 카테고리. Free News API의 topic enum 값 중 하나여야 함(예: `technology`, `business`, `sports`, `music` ...). NAVER 검색에도 같은 문자열을 그대로 검색어로 사용한다. 전체 목록은 `providers/base.py`의 `CATEGORIES` 참고 |
| `--provider` | X | `all` | 어떤 provider로 검색할지. `naver`, `freenews`, 또는 `all`(둘 다 검색해서 합침) |
| `--display` | X | `10` | provider별 검색 결과 개수. **freenews는 API가 개수 파라미터를 지원하지 않아** 실제로는 API 응답 개수(현재 10건)에서 더 늘어나지 않는다 |
| `--with-body` | X | 꺼짐(플래그) | 본문까지 가져올지 여부. 끄면 제목/요약/링크/발행일만 출력(검색 API 호출만 발생). 켜면 기사마다 상세 조회가 추가로 발생하므로 느려짐 |

### 예시

```bash
# technology 카테고리, 전체 provider, 제목만
python main.py --category technology

# music 카테고리, naver만, 본문 포함, 20건 시도
python main.py --category music --provider naver --display 20 --with-body

# freenews만, 제목만 5건
python main.py --category technology --provider freenews --display 5
```

## 코드 스타일 (ruff)

```bash
ruff check .          # 린트
ruff check . --fix    # 자동 수정
ruff format .         # 포매팅
```

설정은 `pyproject.toml`의 `[tool.ruff]`에 있다.

## 참고

- `naver_news/article.py`의 본문 조회는 newspaper3k를 통한다. 따라서 본문을 제대로 못가져올 위험성이 있다.
- `main.py`는 검색 → 유사도 dedup → (옵션)본문조회 → 요약 → 번역 → DB 저장 → 출력 순으로 돈다. 각 스테이지는 `processing/`의 별도 모듈이고, `main.py`가 명시적으로 순서대로 호출한다.
- `processing/`은 `sentence_similarity/`의 두 파일(`cosine_similarity.py`, `summarize_and_translate.py`)을 **복사**해온 것 + 우리가 새로 만든 `translate.py`/`db.py`로 구성된다. `sentence_similarity/`의 원본은 안 건드렸고, `processing/` 쪽 사본만 실제 스키마/모델에 맞게 고쳐서 쓴다 (`cosine_similarity.py`는 DB 연결 방식과 태그 조인 쿼리를, `summarize_and_translate.py`는 deprecate된 `GROQ_MODEL` 값을 수정함).
- `translate.py`는 `item.summary`(Groq 요약)를 googletrans로 한국어로 번역해서 `item.summary_ko`를 채운다. `item.language`가 이미 `"ko"`면 건너뛴다 (naver는 항상 ko, freenews는 `--language`로 실제 검색한 언어). `googletrans`는 4.x부터 async 전용이라 내부적으로 `asyncio.run()`으로 감싸져 있지만, `translate_stage()` 자체는 동기 함수라 파이프라인 나머지와 동일하게 쓴다.
- 요약/번역은 실패해도 예외를 던지지 않고 `item.summary`/`item.summary_ko`에 `"(요약 실패: ...)"`/`"(번역 실패: ...)"` 문자열을 넣는다. `db.py`는 이 패턴을 보고 해당 기사를 `articles.status='FAILED'`로 표시하고 summaries/translations 저장을 건너뛴다.
- `articles.url_hash`가 UNIQUE라서 완전히 같은 URL 재수집은 DB가 알아서 upsert로 걸러준다 (재실행해도 안전). 이것과 별개로 `cosine_similarity.py`의 `dedup_stage`는 URL이 달라도 내용이 사실상 같은 기사(예: 여러 언론사가 같은 통신사 기사를 재배포)를 `sentence-transformers` 임베딩 + 코사인 유사도(`SIMILARITY_THRESHOLD=0.8`)로 걸러낸다. 같은 `--category` 태그로 DB에 이미 있는 기사 제목과 이번 배치 제목을 비교하는 방식이라, `sentence-transformers`/`torch`를 로드하므로 매 실행마다 첫 로딩이 느리다.
