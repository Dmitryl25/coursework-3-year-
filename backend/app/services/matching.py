import faiss
import json
import os

from ml_models.matcher.vectorizer import encode, init as init_vectorizer

BASE = os.path.join(os.path.dirname(__file__), "../../ml_models/matcher")
index = None
ids = None
names = None

def faiss_init():
    global index, ids, names
    init_vectorizer()
    index = faiss.read_index(os.path.join(BASE, "food.index"))
    with open(os.path.join(BASE, "food_ids.json")) as f:
        ids = json.load(f)
    with open(os.path.join(BASE, "food_names.json")) as f:
        names = json.load(f)

def match(text: str, threshold: float = 0.7):
    vector = encode(text).reshape(1, -1)
    D, I = index.search(vector, k=5)
    query = text.lower()

    best_idx, best_score = int(I[0][0]), float(D[0][0])
    if best_score < threshold:
        return None

    for idx, score in zip(I[0], D[0]):
        idx, score = int(idx), float(score)
        if best_score - score > 0.05:
            break
        if query in names[idx] or names[idx] in query:
            best_idx, best_score = idx, score
            break

    return {
        "matched_food_id": ids[best_idx],
        "confidence": min(best_score, 1.0)
    }
