from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
import os
from ml_models.ocr.engine import extract_items
import uuid
from datetime import datetime

from app.db.session import get_db
from ..db.schemas import (
    OCRLogResponse,
    OCRProcessResponse,
    RecognitionResponse,
    RecognizedItem,
    OCRStatusEnum
)
from ..db.crud import (
    create_ocr_log,
    update_ocr_status,
    get_pending_ocr_logs,
    get_user_ocr_logs,
    get_food_by_id
)
from ..db.models import OCRStatus
from app.services.matching import match

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


@router.post("/upload", response_model=OCRLogResponse)
async def upload_photo(
    user_id: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузить фото для OCR обработки"""
    # Генерируем уникальное имя файла
    file_path = await save_upload(file)
    
    # Создаем запись в БД
    db_log = create_ocr_log(db, user_id, file_path)
    
    # Здесь будет вызов ML сервиса для OCR
    # Для примера просто возвращаем pending статус
    
    return db_log

@router.post("/process/{log_id}", response_model=OCRProcessResponse)
async def process_ocr(
    log_id: int,
    db: Session = Depends(get_db)
):
    """Обработать OCR задачу (вызов ML)"""
    # Здесь будет реальная логика OCR
    # Пока просто имитируем успешную обработку
    
    extracted_text = "овсянка 150г, яблоко 200г"
    updated_log = update_ocr_status(db, log_id, OCRStatus.SUCCESS, extracted_text)
    
    if not updated_log:
        raise HTTPException(status_code=404, detail="OCR log not found")
    
    return OCRProcessResponse(
        log_id=log_id,
        status="success",
        extracted_text=extracted_text
    )

@router.post("/recognize", response_model=RecognitionResponse)
async def recognize(file: UploadFile = File(...),
                    user_id: int = Query(...),
                    db: Session = Depends(get_db)):


    file_path = await save_upload(file)

    db_log = create_ocr_log(db, user_id, file_path)

    raw_items = extract_items(file_path)

    if not raw_items:
        update_ocr_status(db, db_log.id, OCRStatus.FAILED, None)
        return RecognitionResponse(log_id=db_log.id,
                                   status=OCRStatusEnum.FAILED,
                                   items=[])

    recognized = []
    for item in raw_items:
        result = match(item["raw_text"]) or match(item["raw_text"].replace(" ", ""))
        food = get_food_by_id(db, result["matched_food_id"]) if result else None
        recognized.append(RecognizedItem(raw_text=item["raw_text"],
                                         weight_g=item["weight_g"],
                                         matched_food_id=result["matched_food_id"] if result else None,
                                         matched_name=food.name if food else None,
                                         confidence=result["confidence"] if result else 0.0))
    update_ocr_status(db, db_log.id, OCRStatus.SUCCESS, " ".join(i["raw_text"] for i in raw_items))


    return RecognitionResponse(log_id=db_log.id,
                               status=OCRStatusEnum.SUCCESS,
                               items=recognized)

@router.post("/match-text", response_model=RecognitionResponse)
async def match_text(text: str = Query(...),
                     weight_g: float = Query(...),
                     user_id: int = Query(...),
                     db: Session = Depends(get_db)):
    result = match(text)
    if not result:
        return RecognitionResponse(status=OCRStatusEnum.FAILED,
                                   items=[])
    food = get_food_by_id(db, result["matched_food_id"])
    matched_name = food.name if food else None

    return RecognitionResponse(status=OCRStatusEnum.SUCCESS,
                               items=[RecognizedItem(raw_text=text,
                                                     weight_g=weight_g,
                                                     matched_food_id=result["matched_food_id"],
                                                     matched_name=matched_name,
                                                     confidence=result["confidence"])])


@router.get("/pending", response_model=list[OCRLogResponse])
async def get_pending(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Получить необработанные OCR задачи"""
    pending_logs = get_pending_ocr_logs(db, limit)
    return pending_logs

@router.get("/user/{user_id}", response_model=list[OCRLogResponse])
async def get_user_history(
    user_id: int,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Получить историю OCR пользователя"""
    logs = get_user_ocr_logs(db, user_id, limit)
    return logs