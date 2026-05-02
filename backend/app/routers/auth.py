from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, date

# Правильный импорт get_db
from app.db.session import get_db
from app.db.schemas import UserRegister, UserLogin, UserResponse, UserWithTDEE
from app.db.crud import (
    get_user_by_email,
    create_user,
    verify_password,
    get_user_with_tdee,
    get_user_by_id,
)
from app.core.nutrition import calculate_tdee, calculate_macros

router = APIRouter(prefix="/auth", tags=["authentication"])

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    db_user = create_user(db, user)
    return db_user

@router.post("/login")
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """Вход пользователя"""
    db_user = verify_password(db, user.email, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    
    # Здесь нужно добавить JWT токен
    return {
        "status": "success",
        "message": "Login successful",
        "user_id": db_user.id,
        "email": db_user.email
    }

@router.get("/user/{user_id}/tdee", response_model=UserWithTDEE)
async def get_user_tdee(user_id: int, db: Session = Depends(get_db)):
    """Получить пользователя с рассчитанным TDEE"""
    user = get_user_with_tdee(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.get("/user/{user_id}/daily-needs")
async def get_daily_needs(user_id: int, db: Session = Depends(get_db)):
    """Получить дневную норму калорий и КБЖУ"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    tdee = calculate_tdee(user)
    return calculate_macros(tdee, user.goal)