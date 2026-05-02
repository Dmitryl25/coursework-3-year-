import faiss
import json
import os

from ml_models.matcher.vectorizer import encode, init as init_vectorizer

BASE = os.path.join(os.path.dirname(__file__), "../../ml_models/matcher")
index = None
ids = None

def faiss_init():
    global index, ids
    init_vectorizer()
    index = faiss.read_index(os.path.join(BASE, "food.index"))
    with open(os.path.join(BASE, "food_ids.json")) as f:
        ids = json.load(f)

def match(text: str, threshold: float = 0.8):
    vector = encode(text).reshape(1, -1)
    D, I = index.search(vector, k=1)
    score = float(D[0][0])
    idx = int(I[0][0])
    if score < threshold:
        return None
    return {
        "matched_food_id": ids[idx],
        "confidence": min(score, 1.0)
    }
