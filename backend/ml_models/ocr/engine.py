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

def _resize_if_needed(image_path: str, max_side: int = 1280) -> str:
    from PIL import Image
    img = Image.open(image_path)
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.LANCZOS)
        img.save(image_path)
        logger.info(f"Resized image to {img.size}")
    return image_path

def extract_items(image_path: str) -> List[dict]:
    _resize_if_needed(image_path)
    results = reader.readtext(image_path, detail=1)
    lines: list[tuple[float, list[tuple[float, str]]]] = []
    for (bbox, text, _) in results:
        y_center = (bbox[0][1] + bbox[2][1]) / 2
        x_left = bbox[0][0]
        merged = False
        for line_y, line_blocks in lines:
            if abs(y_center - line_y) < 20:
                line_blocks.append((x_left, text))
                merged = True
                break
        if not merged:
            lines.append((y_center, [(x_left, text)]))

    items = []
    for _, blocks in sorted(lines, key=lambda l: l[0]):
        joined = " ".join(t for _, t in sorted(blocks, key=lambda b: b[0]))
        name = normilize_ocr_text(joined.strip())
        if len(name) >= 3:
            items.append({"raw_text": name})
    return items
