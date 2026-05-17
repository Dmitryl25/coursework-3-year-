import os
import sys
sys.path.insert(0, "/app")

import psycopg2
import faiss
import json
from ml_models.matcher.vectorizer import encode, init as init_vectorizer

init_vectorizer()
from ml_models.matcher.vectorizer import model

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/food_diary")

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("SELECT id, name FROM foods ORDER BY id")
rows = cur.fetchall()
cur.close()
conn.close()

ids = [r[0] for r in rows]
names = [r[1].lower() for r in rows]
print(f"Продуктов в БД: {len(names)}")

vectors = model.encode(names,
                       normalize_embeddings=True,
                       show_progress_bar=True)

index = faiss.IndexFlatIP(vectors.shape[1])
index.add(vectors)

BASE = os.path.dirname(__file__)
faiss.write_index(index, os.path.join(BASE, "food.index"))
with open(os.path.join(BASE, "food_ids.json"), "w") as f:
    json.dump(ids, f)
with open(os.path.join(BASE, "food_names.json"), "w") as f:
    json.dump(names, f)

print(f"Готово — {index.ntotal} векторов, id из БД")
