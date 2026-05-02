from sentence_transformers import SentenceTransformer
import numpy as np

model = None

def init():
    global model
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")

def encode(text: str) -> np.ndarray:
    return model.encode(text.lower(), normalize_embeddings=True)
