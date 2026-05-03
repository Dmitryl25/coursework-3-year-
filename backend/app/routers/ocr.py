from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import os
from ml_models.ocr.engine import extract_items
import uuid

from app.db.session import get_db
from ..db.schemas import (
    OCRLogResponse,
    RecognitionResponse,
    RecognizedItem,
    OCRStatusEnum,
    MatchRequest,
    OCRRawItem,
    OCRResponse
)
from ..db.crud import (
    create_ocr_log,
    update_ocr_status,
    get_pending_ocr_logs,
    get_user_ocr_logs,
    get_food_by_id,
    get_ocr_log_by_id
)
from ..db.models import OCRStatus
from app.services.matching import match
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/ocr", tags=["ocr"])

# Директория для сохранения фото
UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_upload(file: UploadFile) -> str:
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Сохраняем файл
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    return file_path


@router.post("/recognize/{log_id}", response_model=RecognitionResponse)
async def process_ocr(log_id: int,
                      payload: MatchRequest,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)
):
    """Использование FAISS для поиска семантически близких продуктов из базы"""

    log = get_ocr_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="OCR log not found")
    if log.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    recognized = []
    for item in payload.items:
        result = match(item.raw_text) or match(item.raw_text.replace(" ", ""))
        food = get_food_by_id(db, result["matched_food_id"]) if result else None
        recognized.append(RecognizedItem(raw_text=item.raw_text,
                                         weight_g=item.weight_g,
                                         matched_food_id=result["matched_food_id"] if result else None,
                                         matched_name=food.name if food else None,
                                         confidence=result["confidence"] if result else 0.0))

    return RecognitionResponse(log_id=log_id,
                               status=OCRStatusEnum.SUCCESS,
                               items=recognized)

@router.post("/scan", response_model=OCRResponse)
async def recognize(file: UploadFile = File(...),
                    current_user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):

    """Распознавание текста на фото"""
    file_path = await save_upload(file)

    db_log = create_ocr_log(db, current_user.id, file_path)

    raw_items = extract_items(file_path)

    if not raw_items:
        update_ocr_status(db, db_log.id, OCRStatus.FAILED, None)
        return OCRResponse(log_id=db_log.id,
                              status=OCRStatusEnum.FAILED,
                              items=[])

    items = [OCRRawItem(raw_text=i["raw_text"], weight_g=i["weight_g"]) for i in raw_items]

    update_ocr_status(db, db_log.id, OCRStatus.SUCCESS, " ".join(i["raw_text"] for i in raw_items))

    return OCRResponse(log_id=db_log.id, status=OCRStatusEnum.SUCCESS, items=items)


@router.get("/pending", response_model=list[OCRLogResponse])
async def get_pending(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Получить необработанные OCR задачи"""
    pending_logs = get_pending_ocr_logs(db, limit)
    return pending_logs

@router.get("/history", response_model=list[OCRLogResponse])
async def get_user_history(
    current_user: User = Depends(get_current_user),
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Получить историю OCR пользователя"""
    logs = get_user_ocr_logs(db, current_user.id, limit)
    return logs