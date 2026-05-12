from sentence_transformers import SentenceTransformer
import numpy as np
import time
import sys

model = None

def init():
    global model
    print("Loading FAISS...", flush=True)
    start_time = time.time()
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    load_time = time.time() - start_time
    print(f"   ✅ FAISS loaded in {load_time:.2f}s", flush=True)
    sys.stdout.flush()

def encode(text: str) -> np.ndarray:
    return model.encode(text.lower(), normalize_embeddings=True)
