import easyocr
from typing import List
from ml_models.ocr.preprocess import normilize_ocr_text

reader = None

def ocr_init():
    global reader
    reader = easyocr.Reader(['ru', 'en'], gpu=True)

def extract_items(image_path: str) -> List[dict]:
    results = reader.readtext(image_path, detail=0)
    items = []
    for line in results:
        name = normilize_ocr_text(line.strip())
        if len(name) >= 3:
            items.append({"raw_text": name})
    return items
