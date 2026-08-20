import pymysql
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from processing.db import _db_config

# 원본(sentence_similarity/cosine_similarity.py) 대비 두 가지 수정:
#   1. DB_CONFIG 하드코딩(localhost/root/password/db) 대신 db.py와 같은
#      DB_HOST/DB_USER/DB_PASSWORD/DB_NAME 환경변수를 씀 -- 이 사본은 실제
#      DB에 붙으므로 자리채움 값으로는 항상 연결이 실패한다.
#   2. 존재하지 않는 articles.tag 컬럼 대신 article_tags/tags를 조인한다.
#      실제 스키마(schema-v2-proposal의 schema_no_index.sql)엔 태그가
#      article_tags 다대다 테이블로 연결돼 있고, tags.name으로 매칭한다
#      (db.py의 _lookup_tag_id와 동일한 기준).

SIMILARITY_THRESHOLD = 0.8

_embed_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


def dedup_stage(items: list, tag: str) -> list:
    if not items:
        return items

    try:
        conn = pymysql.connect(**_db_config())
    except Exception as e:
        print(f"DB 연결 실패, 중복 제거 건너뜀: {e}")
        return items

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT a.title
                FROM articles a
                JOIN article_tags at ON at.article_id = a.id
                JOIN tags t ON t.id = at.tag_id
                WHERE t.name = %s
                """,
                (tag,),
            )
            existing_titles = [row[0] for row in cur.fetchall()]
    except Exception as e:
        print(f"기존 제목 조회 실패, 중복 제거 건너뜀: {e}")
        return items
    finally:
        conn.close()

    if not existing_titles:
        return items

    new_titles = [item.title for item in items]

    existing_emb = _embed_model.encode(existing_titles)
    new_emb = _embed_model.encode(new_titles)

    sim_matrix = cosine_similarity(new_emb, existing_emb)
    max_sim_per_item = sim_matrix.max(axis=1)

    keep = [
        item
        for item, sim in zip(items, max_sim_per_item, strict=True)
        if sim < SIMILARITY_THRESHOLD
    ]

    return keep
