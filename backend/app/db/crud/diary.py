from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from datetime import datetime, date, timedelta, timezone
from typing import List, Optional

MSK = timezone(timedelta(hours=3))

from ..models import DiaryEntry, Food, User
from ..schemas import DiaryEntryCreate, DiaryEntryResponse, DailyStats, DailySummary, WeeklyStats
from app.core.nutrition import calculate_tdee, calculate_macros


async def create_diary_entry(db: AsyncSession,
                             user_id: int,
                             entry: DiaryEntryCreate) -> DiaryEntry:
    """Создать запись в дневнике"""
    db_entry = DiaryEntry(
        user_id=user_id,
        food_id=entry.food_id,
        weight=entry.weight,
        datetime=entry.datetime,
        meal_type=entry.meal_type,
    )
    db.add(db_entry)
    return db_entry


async def get_diary_entries_by_date(db: AsyncSession,
                                    user_id: int, target_date: date) -> List:
    """Получить все записи за конкретную дату"""
    start_date = datetime.combine(target_date, datetime.min.time(), tzinfo=MSK).astimezone(timezone.utc)
    end_date = datetime.combine(target_date, datetime.max.time(), tzinfo=MSK).astimezone(timezone.utc)

    result = await db.execute(
        select(
            DiaryEntry.id,
            DiaryEntry.user_id,
            DiaryEntry.food_id,
            DiaryEntry.weight,
            DiaryEntry.datetime,
            DiaryEntry.created_at,
            DiaryEntry.meal_type,
            Food.name.label('food_name'),
            Food.calories,
            Food.proteins,
            Food.fats,
            Food.carbohydrates,
            (Food.calories * (DiaryEntry.weight / 100)).label('total_calories'),
            (Food.proteins * (DiaryEntry.weight / 100)).label('total_proteins'),
            (Food.fats * (DiaryEntry.weight / 100)).label('total_fats'),
            (Food.carbohydrates * (DiaryEntry.weight / 100)).label('total_carbohydrates')
        )
        .join(Food, DiaryEntry.food_id == Food.id)
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.datetime >= start_date,
                DiaryEntry.datetime <= end_date
            )
        )
        .order_by(desc(DiaryEntry.datetime))
    )
    return result.all()


async def get_daily_stats(db: AsyncSession,
                          user_id: int,
                          target_date: date) -> DailyStats:
    """Получить статистику за день"""
    start_date = datetime.combine(target_date, datetime.min.time(), tzinfo=MSK).astimezone(timezone.utc)
    end_date = datetime.combine(target_date, datetime.max.time(), tzinfo=MSK).astimezone(timezone.utc)

    result = await db.execute(
        select(
            func.coalesce(func.sum(Food.calories * (DiaryEntry.weight / 100)), 0).label('total_calories'),
            func.coalesce(func.sum(Food.proteins * (DiaryEntry.weight / 100)), 0).label('total_proteins'),
            func.coalesce(func.sum(Food.fats * (DiaryEntry.weight / 100)), 0).label('total_fats'),
            func.coalesce(func.sum(Food.carbohydrates * (DiaryEntry.weight / 100)), 0).label('total_carbohydrates'),
            func.count(DiaryEntry.id).label('entries_count')
        )
        .join(Food, DiaryEntry.food_id == Food.id)
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.datetime >= start_date,
                DiaryEntry.datetime <= end_date
            )
        )
    )
    stats = result.first()

    return DailyStats(
        total_calories=float(stats.total_calories),
        total_proteins=float(stats.total_proteins),
        total_fats=float(stats.total_fats),
        total_carbohydrates=float(stats.total_carbohydrates),
        entries_count=stats.entries_count
    )


async def get_daily_summary_with_tdee(db: AsyncSession,
                                      user: User,
                                      target_date: date) -> DailySummary:
    """Получить дневную сводку со сравнением с нормой"""
    stats = await get_daily_stats(db, user.id, target_date)

    tdee = calculate_tdee(user)
    target = calculate_macros(tdee, user.goal)["calories"]
    remaining = target - stats.total_calories

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


async def get_weekly_stats(db: AsyncSession,
                           user_id: int,
                           end_date: date = None) -> WeeklyStats:
    """Получить статистику за неделю"""
    if end_date is None:
        end_date = datetime.now(MSK).date()

    start_date = end_date - timedelta(days=6)
    week_start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=MSK).astimezone(timezone.utc)
    week_end_dt = datetime.combine(end_date, datetime.max.time(), tzinfo=MSK).astimezone(timezone.utc)

    from sqlalchemy import cast, Date as SADate, func as sqlfunc
    result = await db.execute(
        select(
            cast(DiaryEntry.datetime.op("AT TIME ZONE")("UTC").op("AT TIME ZONE")("Europe/Moscow"), SADate).label("day"),
            func.coalesce(func.sum(Food.calories * (DiaryEntry.weight / 100)), 0).label('total_calories'),
            func.coalesce(func.sum(Food.proteins * (DiaryEntry.weight / 100)), 0).label('total_proteins'),
            func.coalesce(func.sum(Food.fats * (DiaryEntry.weight / 100)), 0).label('total_fats'),
            func.coalesce(func.sum(Food.carbohydrates * (DiaryEntry.weight / 100)), 0).label('total_carbohydrates'),
            func.count(DiaryEntry.id).label('entries_count'),
        )
        .join(Food, DiaryEntry.food_id == Food.id)
        .where(
            and_(
                DiaryEntry.user_id == user_id,
                DiaryEntry.datetime >= week_start_dt,
                DiaryEntry.datetime <= week_end_dt,
            )
        )
        .group_by("day")
    )
    rows_by_day = {row.day: row for row in result.all()}

    daily_stats = []
    total_calories = 0.0
    for i in range(7):
        current_date = start_date + timedelta(days=i)
        row = rows_by_day.get(current_date)
        stats = DailyStats(
            total_calories=float(row.total_calories) if row else 0.0,
            total_proteins=float(row.total_proteins) if row else 0.0,
            total_fats=float(row.total_fats) if row else 0.0,
            total_carbohydrates=float(row.total_carbohydrates) if row else 0.0,
            entries_count=row.entries_count if row else 0,
        )
        daily_stats.append(stats)
        total_calories += stats.total_calories

    return WeeklyStats(
        week_start=start_date,
        week_end=end_date,
        daily_stats=daily_stats,
        total_calories=total_calories,
        average_calories=total_calories / 7
    )


async def get_confirmed_meals_today(db: AsyncSession,
                                    user_id: int) -> set:
    """Вернуть все meal_type из дневника за сегодня. Snack в результате не блокирует план — проверка идёт в роутере через ALL_MEALS"""
    today = datetime.now(MSK).date()
    start_date = datetime.combine(today, datetime.min.time(), tzinfo=MSK).astimezone(timezone.utc)
    end_date = datetime.combine(today, datetime.max.time(), tzinfo=MSK).astimezone(timezone.utc)

    result = await db.execute(
        select(DiaryEntry.meal_type)
        .where(
            DiaryEntry.user_id == user_id,
            DiaryEntry.datetime >= start_date,
            DiaryEntry.datetime <= end_date,
            DiaryEntry.meal_type.isnot(None),
        )
        .distinct()
    )
    return {r.meal_type for r in result.all()}


async def delete_diary_entry(db: AsyncSession,
                             entry_id: int,
                             user_id: int) -> bool:
    """Удалить запись из дневника"""
    result = await db.execute(
        select(DiaryEntry).where(
            and_(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id
            )
        )
    )
    entry = result.scalar_one_or_none()

    if entry:
        await db.delete(entry)
        return True
    return False


async def update_diary_entry(db: AsyncSession,
                             entry_id: int,
                             user_id: int,
                             weight: float) -> DiaryEntry | None:
    """Обновить вес в записи дневника"""
    result = await db.execute(
        select(DiaryEntry).where(
            and_(
                DiaryEntry.id == entry_id,
                DiaryEntry.user_id == user_id
            )
        )
    )
    entry = result.scalar_one_or_none()

    if entry:
        entry.weight = weight
    return entry
