import pandas as pd
from ml_models.matcher.vectorizer import model, encode
import faiss, json

df = pd.read_csv("../../data/products.csv")
names = df["name"].str.lower().tolist()
ids = df["id"].tolist()

vectors = model.encode(names, normalize_embeddings=True)

index = faiss.IndexFlatIP(384)
index.add(vectors)
faiss.write_index(index, "food.index")

with open("food_ids.json", "w") as f:
    json.dump(ids, f)
