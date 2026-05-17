from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from typing import List, Optional

from ..models import Food, DiaryEntry
from ..schemas import FoodCreate


async def search_foods(db: AsyncSession,
                       query: str,
                       limit: int = 20) -> List[Food]:
    """Поиск продуктов по названию"""
    search_pattern = f"%{query}%"
    result = await db.execute(
        select(Food).where(Food.name.ilike(search_pattern)).limit(limit)
    )
    return result.scalars().all()


async def get_food_by_id(db: AsyncSession,
                         food_id: int) -> Food | None:
    """Получить продукт по ID"""
    result = await db.execute(select(Food).where(Food.id == food_id))
    return result.scalar_one_or_none()


async def get_foods_by_ids(db: AsyncSession,
                           food_ids: List[int]) -> List[Food]:
    """Получить несколько продуктов по списку ID"""
    result = await db.execute(select(Food).where(Food.id.in_(food_ids)))
    return result.scalars().all()


async def create_food(db: AsyncSession,
                      food: FoodCreate) -> Food:
    """Создать новый продукт"""
    db_food = Food(**food.model_dump())
    db.add(db_food)
    await db.commit()
    await db.refresh(db_food)
    return db_food


async def search_foods_advanced(db: AsyncSession, query: str,
                                min_calories: Optional[int] = None,
                                max_calories: Optional[int] = None,
                                limit: int = 20) -> List[Food]:
    """Расширенный поиск продуктов с фильтрами"""
    search_pattern = f"%{query}%"
    stmt = select(Food).where(Food.name.ilike(search_pattern))

    if min_calories is not None:
        stmt = stmt.where(Food.calories >= min_calories)
    if max_calories is not None:
        stmt = stmt.where(Food.calories <= max_calories)

    result = await db.execute(stmt.limit(limit))
    return result.scalars().all()


async def get_popular_foods(db: AsyncSession,
                            limit: int = 10) -> List[Food]:
    """Получить самые популярные продукты (по количеству записей в дневнике)"""
    result = await db.execute(
        select(Food)
        .join(DiaryEntry, Food.id == DiaryEntry.food_id)
        .group_by(Food.id)
        .order_by(desc(func.count(DiaryEntry.id)))
        .limit(limit)
    )
    return result.scalars().all()
