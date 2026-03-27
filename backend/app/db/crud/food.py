from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional

from ..models import Food, DiaryEntry
from ..schemas import FoodCreate

def search_foods(db: Session, query: str, limit: int = 20) -> List[Food]:
    """Поиск продуктов по названию"""
    search_pattern = f"%{query}%"
    foods = db.query(Food).filter(
        Food.name.ilike(search_pattern)
    ).limit(limit).all()
    return foods

def get_food_by_id(db: Session, food_id: int) -> Food | None:
    """Получить продукт по ID"""
    return db.query(Food).filter(Food.id == food_id).first()

def get_foods_by_ids(db: Session, food_ids: List[int]) -> List[Food]:
    """Получить несколько продуктов по списку ID"""
    return db.query(Food).filter(Food.id.in_(food_ids)).all()

def create_food(db: Session, food: FoodCreate) -> Food:
    """Создать новый продукт"""
    db_food = Food(**food.model_dump())
    db.add(db_food)
    db.commit()
    db.refresh(db_food)
    return db_food

def search_foods_advanced(db: Session, query: str, 
                         min_calories: Optional[int] = None,
                         max_calories: Optional[int] = None,
                         limit: int = 20) -> List[Food]:
    """Расширенный поиск продуктов с фильтрами"""
    search_pattern = f"%{query}%"
    food_query = db.query(Food).filter(Food.name.ilike(search_pattern))
    
    if min_calories is not None:
        food_query = food_query.filter(Food.calories >= min_calories)
    if max_calories is not None:
        food_query = food_query.filter(Food.calories <= max_calories)
    
    return food_query.limit(limit).all()

def get_popular_foods(db: Session, limit: int = 10):
    """Получить самые популярные продукты (по количеству записей в дневнике)"""
    popular = db.query(
        Food.id,
        Food.name,
        Food.calories,
        Food.proteins,
        Food.fats,
        Food.carbohydrates,
        func.count(DiaryEntry.id).label('usage_count')
    ).join(DiaryEntry, Food.id == DiaryEntry.food_id).group_by(
        Food.id
    ).order_by(desc('usage_count')).limit(limit).all()
    
    return popular