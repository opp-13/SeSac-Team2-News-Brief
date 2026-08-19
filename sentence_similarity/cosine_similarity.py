from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import pymysql

SIMILARITY_THRESHOLD = 0.8  

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "password",
    "database": "db",
}
TABLE_NAME = "articles"  

_embed_model = SentenceTransformer("paraphrase-multilingual-mpnet-base-v2")


def dedup_stage(items: list, tag: str) -> list:
    if not items:
        return items

    try:
        conn = pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"DB 연결 실패, 중복 제거 건너뜀: {e}")
        return items

    try:
        with conn.cursor() as cur:
            cur.execute(f"SELECT title FROM {TABLE_NAME} WHERE tag = %s", (tag,))
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
        item for item, sim in zip(items, max_sim_per_item)
        if sim < SIMILARITY_THRESHOLD
    ]

    return keep