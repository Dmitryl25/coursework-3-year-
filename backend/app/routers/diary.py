from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List

MSK = timezone(timedelta(hours=3))

from app.db.session import get_db
from ..db.schemas import (
    DiaryEntryCreate,
    DiaryEntryResponse,
    DailySummary,
    WeeklyStats,
    BulkDiaryCreate
)
from ..db.crud import (
    create_diary_entry,
    get_diary_entries_by_date,
    get_daily_summary_with_tdee,
    get_weekly_stats,
    delete_diary_entry,
    update_diary_entry,
    get_food_by_id
)
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/diary", tags=["diary"])


@router.post("/entry", response_model=DiaryEntryResponse, status_code=201)
async def create_entry(
    entry: DiaryEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись о приеме пищи"""
    food = get_food_by_id(db, entry.food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")

    db_entry = create_diary_entry(db, current_user.id, entry)
    db.commit()
    db.refresh(db_entry)

    return DiaryEntryResponse(
        id=db_entry.id,
        user_id=db_entry.user_id,
        food_id=db_entry.food_id,
        weight=db_entry.weight,
        datetime=db_entry.datetime,
        meal_type=db_entry.meal_type,
        created_at=db_entry.created_at,
        food_name=food.name,
        total_calories=food.calories * (db_entry.weight / 100),
        total_proteins=food.proteins * (db_entry.weight / 100),
        total_fats=food.fats * (db_entry.weight / 100),
        total_carbohydrates=food.carbohydrates * (db_entry.weight / 100),
    )


@router.post("/bulk", response_model=List[DiaryEntryResponse], status_code=201)
async def create_bulk(
    payload: BulkDiaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Создать несколько записей за один приём пищи"""
    db_entries = []
    foods = []

    for item in payload.items:
        food = get_food_by_id(db, item.food_id)
        if food is None:
            raise HTTPException(status_code=404, detail=f"Продукт с id={item.food_id} не найден")
        entry = DiaryEntryCreate(
            food_id=item.food_id,
            weight=item.portion_g,
            datetime=payload.datetime,
            meal_type=payload.meal_type,
        )
        db_entry = create_diary_entry(db, current_user.id, entry)
        db_entries.append(db_entry)
        foods.append(food)

    db.commit()

    results = []
    for db_entry, food in zip(db_entries, foods):
        db.refresh(db_entry)
        results.append(DiaryEntryResponse(
            id=db_entry.id,
            user_id=db_entry.user_id,
            food_id=db_entry.food_id,
            weight=db_entry.weight,
            datetime=db_entry.datetime,
            meal_type=db_entry.meal_type,
            created_at=db_entry.created_at,
            food_name=food.name,
            total_calories=food.calories * (db_entry.weight / 100),
            total_proteins=food.proteins * (db_entry.weight / 100),
            total_fats=food.fats * (db_entry.weight / 100),
            total_carbohydrates=food.carbohydrates * (db_entry.weight / 100),
        ))
    return results


@router.get("/entries/{target_date}", response_model=List[DiaryEntryResponse])
async def get_day_entries(
    target_date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить список записей о приёмах пищи за конкретный день."""
    try:
        parsed_date = datetime.strptime(target_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный формат даты. Используй YYYY-MM-DD")

    entries = get_diary_entries_by_date(db, current_user.id, parsed_date)
    return [
        DiaryEntryResponse(
            id=e.id,
            user_id=e.user_id,
            food_id=e.food_id,
            weight=e.weight,
            datetime=e.datetime,
            meal_type=e.meal_type,
            created_at=e.created_at,
            food_name=e.food_name,
            total_calories=e.total_calories,
            total_proteins=e.total_proteins,
            total_fats=e.total_fats,
            total_carbohydrates=e.total_carbohydrates,
        )
        for e in entries
    ]


@router.get("/day/{date}", response_model=DailySummary)
async def get_day(
    date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить сводку за день"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

    return get_daily_summary_with_tdee(db, current_user, target_date)


@router.get("/week", response_model=WeeklyStats)
async def get_week(
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику за неделю"""
    if end_date:
        try:
            target_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = datetime.now(MSK).date()

    return get_weekly_stats(db, current_user.id, target_date)


@router.delete("/entry/{entry_id}")
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Удалить запись из дневника"""
    deleted = delete_diary_entry(db, entry_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.commit()
    return {"status": "deleted", "entry_id": entry_id}


class WeightUpdate(BaseModel):
    weight: float = Field(..., gt=0, le=10000)


@router.patch("/entry/{entry_id}")
async def update_entry(
    entry_id: int,
    payload: WeightUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Обновить вес порции в записи"""
    entry = update_diary_entry(db, entry_id, current_user.id, payload.weight)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.commit()
    db.refresh(entry)
    return {"status": "updated", "entry_id": entry_id, "new_weight": payload.weight}
