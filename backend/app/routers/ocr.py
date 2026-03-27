from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional
import os
import uuid
from datetime import datetime

from app.db.session import get_db
from ..db.schemas import OCRLogResponse, OCRProcessResponse
from ..db.crud import (
    create_ocr_log,
    update_ocr_status,
    get_pending_ocr_logs,
    get_user_ocr_logs
)

router = APIRouter(prefix="/ocr", tags=["ocr"])

# Директория для сохранения фото
UPLOAD_DIR = "uploads/photos"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=OCRLogResponse)
async def upload_photo(
    user_id: int = Query(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Загрузить фото для OCR обработки"""
    # Генерируем уникальное имя файла
    file_extension = os.path.splitext(file.filename)[1]
    filename = f"{uuid.uuid4()}{file_extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    # Сохраняем файл
    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)
    
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
    updated_log = update_ocr_status(db, log_id, "success", extracted_text)
    
    if not updated_log:
        raise HTTPException(status_code=404, detail="OCR log not found")
    
    return OCRProcessResponse(
        log_id=log_id,
        status="success",
        extracted_text=extracted_text
    )

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