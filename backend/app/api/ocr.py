# Прием фото и вызов ML-скриптов
from fastapi import APIRouter

router = APIRouter()

@router.post("/ocr/raw")
async def ocr_process():
    return {"message": "Модуль пока в разработке"}