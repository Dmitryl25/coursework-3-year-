from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.db.session import get_db
from ..db.schemas import FoodResponse, FoodCreate, FoodSearchResult
from ..db.crud import (
    search_foods,
    get_food_by_id,
    create_food,
    search_foods_advanced,
    get_popular_foods
)

router = APIRouter(prefix="/food", tags=["food"])

@router.get("/search", response_model=List[FoodResponse])
async def search(
    query: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Поиск продуктов по названию"""
    foods = search_foods(db, query, limit)
    return foods

@router.get("/search/advanced", response_model=List[FoodResponse])
async def search_advanced(
    query: str = Query(..., min_length=1),
    min_calories: Optional[int] = None,
    max_calories: Optional[int] = None,
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """Расширенный поиск продуктов с фильтром по калориям"""
    foods = search_foods_advanced(db, query, min_calories, max_calories, limit)
    return foods

@router.get("/popular", response_model=List[FoodResponse])
async def popular(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Получить популярные продукты"""
    popular = get_popular_foods(db, limit)
    return popular

@router.get("/{food_id}", response_model=FoodResponse)
async def get_food(
    food_id: int,
    db: Session = Depends(get_db)
):
    """Получить продукт по ID"""
    food = get_food_by_id(db, food_id)
    if not food:
        raise HTTPException(status_code=404, detail="Food not found")
    return food

@router.post("/", response_model=FoodResponse, status_code=201)
async def create_food_endpoint(
    food: FoodCreate,
    db: Session = Depends(get_db)
):
    """Создать новый продукт (для админов)"""
    # Здесь добавить проверку прав администратора
    db_food = create_food(db, food)
    return db_food