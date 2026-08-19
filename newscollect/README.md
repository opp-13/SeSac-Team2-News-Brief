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

```
NCP_CLIENT_ID=...
NCP_CLIENT_SECRET=...
FREENEWS_API_KEY=...
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
- `main.py` TODO 구현 필요 (구현 될 부분에 맞추어 코드 구조 수정할 가능성 있음)
    - 유사도 기반 중복 기사 제거
    - AI 요약/번역
