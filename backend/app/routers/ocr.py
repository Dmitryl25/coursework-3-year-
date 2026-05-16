from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import logging
import os
import uuid

logger = logging.getLogger(__name__)

from ml_models.classifier.engine import classify_image
from ml_models.ocr.engine import extract_items
from app.core.dependencies import get_current_user
from app.db.crud import (
    create_ocr_log,
    update_ocr_status,
    get_pending_ocr_logs,
    get_user_ocr_logs,
    get_food_by_id,
    get_ocr_log_by_id,
)
from app.db.models import OCRStatus, User
from app.db.schemas import (
    MatchRequest,
    OCRLogResponse,
    OCRRawItem,
    OCRResponse,
    OCRStatusEnum,
    RecognitionResponse,
    RecognizedItem,
)
from app.db.session import get_db
from app.services.matching import match

router = APIRouter(prefix="/ocr", tags=["ocr"])

UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_upload(file: UploadFile) -> str:
    ext = os.path.splitext(file.filename)[1]
    file_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}{ext}")
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


@router.post("/scan", response_model=OCRResponse)
async def recognize(file: UploadFile = File(...),
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db),
):
    """Распознавание блюд на фото (без граммовки)."""
    logger.info(f"[OCR/scan] user_id={current_user.id} file={file.filename}")

    file_path = await save_upload(file)
    logger.info(f"[OCR/scan] saved to {file_path}")

    db_log = create_ocr_log(db, current_user.id, file_path)

    raw_items = extract_items(file_path)

    if not raw_items:
        update_ocr_status(db, db_log.id, OCRStatus.FAILED, None)
        logger.warning(f"[OCR/scan] log_id={db_log.id} — nothing recognized")
        return OCRResponse(log_id=db_log.id,
                           status=OCRStatusEnum.FAILED, items=[])

    items = [OCRRawItem(raw_text=i["raw_text"]) for i in raw_items]

    update_ocr_status(db, db_log.id,
                      OCRStatus.SUCCESS,
                      " ".join(i["raw_text"] for i in raw_items))

    logger.info(f"[OCR/scan] log_id={db_log.id} — recognized {len(items)} item(s): {[i.raw_text for i in items]}")

    return OCRResponse(
        log_id=db_log.id,
        status=OCRStatusEnum.SUCCESS,
        items=items
    )


@router.post("/recognize/{log_id}", response_model=RecognitionResponse)
async def process_ocr(log_id: int,
                      payload: MatchRequest,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    """FAISS-поиск семантически близких продуктов из базы."""
    log = get_ocr_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="OCR log not found")
    if log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    recognized = []
    for item in payload.items:
        result = match(item.raw_text) or match(item.raw_text.replace(" ", ""))
        food = get_food_by_id(db, result["matched_food_id"]) if result else None
        recognized.append(
            RecognizedItem(raw_text=item.raw_text,
                           matched_food_id=result["matched_food_id"] if result else None,
                           matched_name=food.name if food else None,
                           confidence=result["confidence"] if result else 0.0)
        )

    return RecognitionResponse(
        log_id=log_id,
        status=OCRStatusEnum.SUCCESS,
        items=recognized
    )


@router.post("/classify", response_model=RecognitionResponse)
async def classify(file: UploadFile = File(...),
                   current_user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    """
    Распознавание блюда на фото через классификатор (MobileNetV3, Food101).

    Возвращает top-3 совпадения из базы продуктов.
    Пользователь выбирает нужный вариант и вводит порцию,
    затем отправляет в POST /diary/bulk.
    """
    file_path = await save_upload(file)
    db_log = create_ocr_log(db, current_user.id, file_path)
    update_ocr_status(db, db_log.id, OCRStatus.SUCCESS, None)

    predictions = classify_image(file_path, top_k=3)

    recognized = []
    for pred in predictions:
        result = match(pred["class_name"])
        food = get_food_by_id(db, result["matched_food_id"]) if result else None
        # Итоговая уверенность — произведение confidence классификатора и FAISS
        combined_confidence = round(
            pred["confidence"] * (result["confidence"] if result else 0.0), 4
        )
        recognized.append(
            RecognizedItem(raw_text=pred["class_name"],
                           matched_food_id=result["matched_food_id"] if result else None,
                           matched_name=food.name if food else None,
                           confidence=combined_confidence)
        )

    return RecognitionResponse(
        log_id=db_log.id,
        status=OCRStatusEnum.SUCCESS,
        items=recognized,
    )


@router.get("/pending", response_model=list[OCRLogResponse])
async def get_pending(limit: int = 10,
                      db: Session = Depends(get_db)):
    """Получить необработанные OCR задачи."""
    return get_pending_ocr_logs(db, limit)


@router.get("/history", response_model=list[OCRLogResponse])
async def get_user_history(current_user: User = Depends(get_current_user),
                           limit: int = 20,
                           db: Session = Depends(get_db)):
    """История OCR пользователя."""
    return get_user_ocr_logs(db, current_user.id, limit)
