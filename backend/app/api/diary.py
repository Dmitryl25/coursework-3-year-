# Работа с дневником питания
from fastapi import APIRouter
from pydantic import BaseModel

class DiaryEntry(BaseModel):
    food_id: int
    wieght_grams: float
    meal_type: str

router = APIRouter()

@router.get("/day/{date}")
async def get_day(date: str):
    return {"message": "Модуль пока в разработке"}

@router.get("/recommendations/today")
async def get_recommendation(date: str):
    return {"message": "Модуль по рекомендациям пока в разработке"}

@router.post("entry")
async def create_entry(entry: DiaryEntry):
    return {"message": "Модуль по сохранению потрбления пищи пока в разработке"}