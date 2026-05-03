from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date, datetime
from typing import Optional, List

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
    # Проверяем, существует ли продукт
    food = get_food_by_id(db, entry.food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    
    db_entry = create_diary_entry(db, current_user.id, entry)
    db.commit()
    db.refresh(db_entry)
    
    # Формируем ответ с рассчитанными значениями
    total_calories = food.calories * (db_entry.weight / 100)
    total_proteins = food.proteins * (db_entry.weight / 100)
    total_fats = food.fats * (db_entry.weight / 100)
    total_carbohydrates = food.carbohydrates * (db_entry.weight / 100)
    
    return DiaryEntryResponse(
        id=db_entry.id,
        user_id=db_entry.user_id,
        food_id=db_entry.food_id,
        weight=db_entry.weight,
        datetime=db_entry.datetime,
        created_at=db_entry.created_at,
        food_name=food.name,
        total_calories=total_calories,
        total_proteins=total_proteins,
        total_fats=total_fats,
        total_carbohydrates=total_carbohydrates
    )


# Метод создаёт записи в дневнике питания из списка распознанных позиций
@router.post("/bulk", response_model=List[DiaryEntryResponse], status_code=201)
async def create_bulk(payload: BulkDiaryCreate,
                      current_user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    db_entries = []
    foods = []

    for item in payload.items:
        if item.matched_food_id is None:
            continue
        food = get_food_by_id(db, item.matched_food_id)
        if food is None:
            continue
        entry = DiaryEntryCreate(food_id=item.matched_food_id,
                                 weight=item.weight_g,
                                 datetime=payload.datetime)
        db_entry = create_diary_entry(db, current_user.id, entry)
        db_entries.append(db_entry)
        foods.append(food)

    db.commit()

    results = []
    for db_entry, food in zip(db_entries, foods):
        db.refresh(db_entry)
        results.append(DiaryEntryResponse(id=db_entry.id,
                                          user_id=db_entry.user_id,
                                          food_id=db_entry.food_id,
                                          weight=db_entry.weight,
                                          datetime=db_entry.datetime, created_at=db_entry.created_at,
                                          food_name=food.name,
                                          total_calories=food.calories * (db_entry.weight / 100),
                                          total_proteins=food.proteins * (db_entry.weight / 100),
                                          total_fats=food.fats * (db_entry.weight / 100),
                                          total_carbohydrates=food.carbohydrates * (db_entry.weight / 100)
                                          ))
    return results


@router.get("/day/{date}", response_model=DailySummary)
async def get_day(
    date: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сводку за день"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")
    
    summary = get_daily_summary_with_tdee(db, current_user, target_date)
    return summary

@router.get("/week", response_model=WeeklyStats)
async def get_week(
    end_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику за неделю"""
    if end_date:
        try:
            target_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format")
    else:
        target_date = date.today()
    
    stats = get_weekly_stats(db, current_user.id, target_date)
    return stats

@router.delete("/entry/{entry_id}")
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить запись из дневника"""
    deleted = delete_diary_entry(db, entry_id, current_user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"status": "deleted", "entry_id": entry_id}

@router.patch("/entry/{entry_id}")
async def update_entry(
    entry_id: int,
    weight: float,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить вес в записи"""
    entry = update_diary_entry(db, entry_id, current_user.id, weight)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    return {"status": "updated", "entry_id": entry_id, "new_weight": weight}