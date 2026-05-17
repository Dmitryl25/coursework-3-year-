from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional, Sequence
from datetime import datetime

from .. import OCRLog
from ..models import OCRLog, OCRStatus


async def create_ocr_log(db: AsyncSession,
                         user_id: int,
                         photo_path: str) -> OCRLog:
    """Создать запись об OCR обработке"""
    db_log = OCRLog(
        user_id=user_id,
        photo_path=photo_path,
        status=OCRStatus.PENDING
    )
    db.add(db_log)
    await db.commit()
    await db.refresh(db_log)
    return db_log


async def update_ocr_status(db: AsyncSession,
                            log_id: int,
                            status: OCRStatus,
                            raw_text: Optional[str] = None) -> OCRLog | None:
    """Обновить статус OCR обработки"""
    result = await db.execute(select(OCRLog).where(OCRLog.id == log_id))
    log = result.scalar_one_or_none()

    if log:
        log.status = status
        if raw_text:
            log.raw_text = raw_text
        await db.commit()
        await db.refresh(log)
    return log


async def get_pending_ocr_logs(db: AsyncSession,
                               limit: int = 10) -> Sequence[OCRLog]:
    """Получить необработанные OCR задачи"""
    result = await db.execute(
        select(OCRLog)
        .where(OCRLog.status == OCRStatus.PENDING)
        .order_by(OCRLog.created_at)
        .limit(limit)
    )
    return result.scalars().all()


async def get_user_ocr_logs(db: AsyncSession,
                            user_id: int,
                            limit: int = 20,
                            status: Optional[OCRStatus] = None) -> Sequence[OCRLog]:
    """Получить историю OCR пользователя"""
    stmt = select(OCRLog).where(OCRLog.user_id == user_id)

    if status:
        stmt = stmt.where(OCRLog.status == status)

    result = await db.execute(stmt.order_by(OCRLog.created_at.desc()).limit(limit))
    return result.scalars().all()


async def get_ocr_log_by_id(db: AsyncSession,
                            log_id: int) -> OCRLog | None:
    """Получить OCR лог по ID"""
    result = await db.execute(select(OCRLog).where(OCRLog.id == log_id))
    return result.scalar_one_or_none()
