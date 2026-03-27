from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc
from datetime import datetime, date, timedelta
from typing import List, Optional

from ..models import DiaryEntry, Food, User
from ..schemas import DiaryEntryCreate, DiaryEntryResponse, DailyStats, DailySummary, WeeklyStats
from .user import calculate_tdee

def create_diary_entry(db: Session, user_id: int, entry: DiaryEntryCreate) -> DiaryEntry:
    """Создать запись в дневнике"""
    db_entry = DiaryEntry(
        user_id=user_id,
        food_id=entry.food_id,
        weight=entry.weight,
        datetime=entry.datetime
    )
    db.add(db_entry)
    db.commit()
    db.refresh(db_entry)
    return db_entry

def get_diary_entries_by_date(db: Session, user_id: int, target_date: date) -> List:
    """Получить все записи за конкретную дату"""
    start_date = datetime.combine(target_date, datetime.min.time())
    end_date = datetime.combine(target_date, datetime.max.time())
    
    entries = db.query(
        DiaryEntry.id,
        DiaryEntry.user_id,
        DiaryEntry.food_id,
        DiaryEntry.weight,
        DiaryEntry.datetime,
        DiaryEntry.created_at,
        Food.name.label('food_name'),
        Food.calories,
        Food.proteins,
        Food.fats,
        Food.carbohydrates,
        (Food.calories * (DiaryEntry.weight / 100)).label('total_calories'),
        (Food.proteins * (DiaryEntry.weight / 100)).label('total_proteins'),
        (Food.fats * (DiaryEntry.weight / 100)).label('total_fats'),
        (Food.carbohydrates * (DiaryEntry.weight / 100)).label('total_carbohydrates')
    ).join(Food, DiaryEntry.food_id == Food.id).filter(
        and_(
            DiaryEntry.user_id == user_id,
            DiaryEntry.datetime >= start_date,
            DiaryEntry.datetime <= end_date
        )
    ).order_by(desc(DiaryEntry.datetime)).all()
    
    return entries

def get_daily_stats(db: Session, user_id: int, target_date: date) -> DailyStats:
    """Получить статистику за день"""
    start_date = datetime.combine(target_date, datetime.min.time())
    end_date = datetime.combine(target_date, datetime.max.time())
    
    stats = db.query(
        func.coalesce(func.sum(Food.calories * (DiaryEntry.weight / 100)), 0).label('total_calories'),
        func.coalesce(func.sum(Food.proteins * (DiaryEntry.weight / 100)), 0).label('total_proteins'),
        func.coalesce(func.sum(Food.fats * (DiaryEntry.weight / 100)), 0).label('total_fats'),
        func.coalesce(func.sum(Food.carbohydrates * (DiaryEntry.weight / 100)), 0).label('total_carbohydrates'),
        func.count(DiaryEntry.id).label('entries_count')
    ).join(Food, DiaryEntry.food_id == Food.id).filter(
        and_(
            DiaryEntry.user_id == user_id,
            DiaryEntry.datetime >= start_date,
            DiaryEntry.datetime <= end_date
        )
    ).first()
    
    return DailyStats(
        total_calories=float(stats.total_calories),
        total_proteins=float(stats.total_proteins),
        total_fats=float(stats.total_fats),
        total_carbohydrates=float(stats.total_carbohydrates),
        entries_count=stats.entries_count
    )

def get_daily_summary_with_tdee(db: Session, user_id: int, target_date: date) -> DailySummary:
    """Получить дневную сводку с сравнением с нормой"""
    stats = get_daily_stats(db, user_id, target_date)
    user = db.query(User).filter(User.id == user_id).first()
    
    if user:
        tdee = calculate_tdee(user)
        remaining = tdee - stats.total_calories
    else:
        tdee = None
        remaining = None
    
    return DailySummary(
        date=target_date.isoformat(),
        total_calories=stats.total_calories,
        total_proteins=stats.total_proteins,
        total_fats=stats.total_fats,
        total_carbohydrates=stats.total_carbohydrates,
        entries_count=stats.entries_count,
        tdee=tdee,
        remaining_calories=remaining
    )

def get_weekly_stats(db: Session, user_id: int, end_date: date = None) -> WeeklyStats:
    """Получить статистику за неделю"""
    if end_date is None:
        end_date = date.today()
    
    start_date = end_date - timedelta(days=6)
    week_start = start_date
    week_end = end_date
    
    daily_stats = []
    total_calories = 0
    
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        stats = get_daily_stats(db, user_id, current_date)
        daily_stats.append(stats)
        total_calories += stats.total_calories
    
    return WeeklyStats(
        week_start=week_start,
        week_end=week_end,
        daily_stats=daily_stats,
        total_calories=total_calories,
        average_calories=total_calories / 7
    )

def delete_diary_entry(db: Session, entry_id: int, user_id: int) -> bool:
    """Удалить запись из дневника"""
    entry = db.query(DiaryEntry).filter(
        and_(
            DiaryEntry.id == entry_id,
            DiaryEntry.user_id == user_id
        )
    ).first()
    
    if entry:
        db.delete(entry)
        db.commit()
        return True
    return False

def update_diary_entry(db: Session, entry_id: int, user_id: int, weight: float) -> DiaryEntry | None:
    """Обновить вес в записи дневника"""
    entry = db.query(DiaryEntry).filter(
        and_(
            DiaryEntry.id == entry_id,
            DiaryEntry.user_id == user_id
        )
    ).first()
    
    if entry:
        entry.weight = weight
        db.commit()
        db.refresh(entry)
    return entry