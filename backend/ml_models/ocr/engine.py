import easyocr
from typing import List
from ml_models.ocr.preprocess import normilize_ocr_text
import time
import sys

reader = None

def ocr_init():
    global reader
    print("Loading EasyOCR...", flush=True)
    start_time = time.time()
    reader = easyocr.Reader(['ru', 'en'], gpu=True)
    load_time = time.time() - start_time
    print(f"   ✅ EasyOCR loaded in {load_time:.2f}s", flush=True)
    sys.stdout.flush()

def extract_items(image_path: str) -> List[dict]:
    results = reader.readtext(image_path, detail=0)
    items = []
    for line in results:
        name = normilize_ocr_text(line.strip())
        if len(name) >= 3:
            items.append({"raw_text": name})
    return items
