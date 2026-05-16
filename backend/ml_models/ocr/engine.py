import easyocr
import torch
import logging
from typing import List
from ml_models.ocr.preprocess import normilize_ocr_text
import time

logger = logging.getLogger(__name__)
reader = None

def ocr_init():
    global reader
    logger.info("Loading EasyOCR...")
    start_time = time.time()

    gpu_available = torch.cuda.is_available()
    try:
        reader = easyocr.Reader(['ru', 'en'], gpu=gpu_available)
        load_time = time.time() - start_time
        if gpu_available:
            logger.info(f"EasyOCR loaded with GPU in {load_time:.2f}s")
        else:
            logger.warning(f"EasyOCR loaded with CPU (GPU not available) in {load_time:.2f}s")
    except Exception as e:
        logger.warning(f"Failed to load with GPU, falling back to CPU: {e}")
        try:
            reader = easyocr.Reader(['ru', 'en'], gpu=False)
            load_time = time.time() - start_time
            logger.info(f"EasyOCR loaded with CPU (fallback) in {load_time:.2f}s")
        except Exception as cpu_error:
            logger.error(f"Failed to load EasyOCR even with CPU: {cpu_error}", exc_info=True)
            raise

def extract_items(image_path: str) -> List[dict]:
    results = reader.readtext(image_path, detail=0)
    items = []
    for line in results:
        name = normilize_ocr_text(line.strip())
        if len(name) >= 3:
            items.append({"raw_text": name})
    return items
