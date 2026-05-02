import easyocr
from typing import List
from ml_models.ocr.preprocess import normilize_ocr_text
import re

reader = None

def ocr_init():
    global reader
    reader = easyocr.Reader(['ru', 'en'], gpu=True)

def extract_items(image_path: str) -> List[dict]:
    results = reader.readtext(image_path, detail=0)
    text = " ".join(results)
    items = []
    pattern = r'([а-яёА-ЯЁa-zA-Z][а-яёА-ЯЁa-zA-Z\s]{1,30})\s+(\d+(?:[.,]\d+)?)\s*(?:г|гр|g|gr|мл|ml)?'

    for match in re.finditer(pattern, text, re.IGNORECASE):
        name = normilize_ocr_text(match.group(1).strip())
        weight = float(match.group(2).replace(',', '.'))
        items.append({"raw_text": name, "weight_g": weight})
    return items
