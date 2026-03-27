from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime

from ..models import OCRLog, OCRStatus
from ..schemas import OCRLogCreate

def create_ocr_log(db: Session, user_id: int, photo_path: str) -> OCRLog:
    """Создать запись об OCR обработке"""
    db_log = OCRLog(
        user_id=user_id,
        photo_path=photo_path,
        status=OCRStatus.PENDING
    )
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    return db_log

def update_ocr_status(db: Session, log_id: int, 
                      status: OCRStatus, 
                      raw_text: Optional[str] = None) -> OCRLog | None:
    """Обновить статус OCR обработки"""
    log = db.query(OCRLog).filter(OCRLog.id == log_id).first()
    
    if log:
        log.status = status
        if raw_text:
            log.raw_text = raw_text
        db.commit()
        db.refresh(log)
    return log

def get_pending_ocr_logs(db: Session, limit: int = 10) -> List[OCRLog]:
    """Получить необработанные OCR задачи"""
    return db.query(OCRLog).filter(
        OCRLog.status == OCRStatus.PENDING
    ).order_by(OCRLog.created_at).limit(limit).all()

def get_user_ocr_logs(db: Session, user_id: int, 
                     limit: int = 20, 
                     status: Optional[OCRStatus] = None) -> List[OCRLog]:
    """Получить историю OCR пользователя"""
    query = db.query(OCRLog).filter(OCRLog.user_id == user_id)
    
    if status:
        query = query.filter(OCRLog.status == status)
    
    return query.order_by(OCRLog.created_at.desc()).limit(limit).all()

def get_ocr_log_by_id(db: Session, log_id: int) -> OCRLog | None:
    """Получить OCR лог по ID"""
    return db.query(OCRLog).filter(OCRLog.id == log_id).first()