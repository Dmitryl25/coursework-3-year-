from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone, timedelta

from app.db.session import get_db
from app.db.schemas import UserRegister, UserLogin, UserResponse, UserWithTDEE, TokenOut, RefreshRequest, GoalUpdate, ProfileUpdate
from app.db.crud import (
    get_user_by_email,
    create_user,
    verify_password,
    get_user_with_tdee,
    update_user_goal,
    update_user_profile,
)
from app.db.crud.token import create_token, deactivate_token, deactivate_all_user_tokens
from app.core.nutrition import calculate_tdee, calculate_macros
from app.core.security import create_access_token, create_refresh_token
from app.core.dependencies import get_current_user, get_current_user_from_refresh_token
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse,
             status_code=status.HTTP_201_CREATED)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    """Регистрация нового пользователя"""
    existing_user = await get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    return await create_user(db, user)


@router.post("/login")
async def login(user: UserLogin, request: Request,
                db: AsyncSession = Depends(get_db)):
    """Вход пользователя"""
    db_user = await verify_password(db, user.email, user.password)
    if not db_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )
    ip = request.client.host if request.client else None
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    db_token = await create_token(db, db_user.id, expires_at, ip)
    return TokenOut(
        access_token=create_access_token(db_user.id),
        refresh_token=create_refresh_token(db_token.id)
    )


@router.post("/refresh", response_model=TokenOut)
async def refresh(user_id_and_token=Depends(get_current_user_from_refresh_token),
                  db: AsyncSession = Depends(get_db)):
    """Пересоздание токенов по refresh токену"""
    user_id, token_db_id = user_id_and_token
    await deactivate_token(db, token_db_id)
    expires_at = datetime.now(timezone.utc) + timedelta(days=30)
    new_db_token = await create_token(db, user_id, expires_at)
    return TokenOut(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(new_db_token.id)
    )


@router.post("/logout")
async def logout(user_id_and_token: tuple = Depends(get_current_user_from_refresh_token),
                 db: AsyncSession = Depends(get_db)):
    """logout пользователя"""
    user_id, token_db_id = user_id_and_token
    await deactivate_token(db, token_db_id)
    return {"message": "Logged out"}


@router.post("/logout_all")
async def logout_all(current_user: User = Depends(get_current_user),
                     db: AsyncSession = Depends(get_db)):
    """logout всех сессий одного пользователя"""
    await deactivate_all_user_tokens(db, current_user.id)
    return {"message": "Logged out from all devices"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/me/tdee", response_model=UserWithTDEE)
async def get_user_tdee(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """Получить пользователя с рассчитанным TDEE"""
    return await get_user_with_tdee(db, current_user.id)


@router.get("/me/daily-needs")
async def get_daily_needs(current_user: User = Depends(get_current_user)):
    return calculate_macros(calculate_tdee(current_user), current_user.goal)


@router.patch("/me/goal", response_model=UserResponse)
async def update_goal(payload: GoalUpdate,
                      current_user: User = Depends(get_current_user),
                      db: AsyncSession = Depends(get_db)):
    """Изменить цель пользователя (loss / maintain / mass)"""
    await update_user_goal(db, current_user, payload.goal)
    await db.commit()
    await db.refresh(current_user)
    return current_user


@router.patch("/me/profile", response_model=UserResponse)
async def update_profile(payload: ProfileUpdate,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """Изменить антропометрические данные (вес, рост, возраст, активность, пол)"""
    await update_user_profile(db, current_user, payload)
    await db.commit()
    await db.refresh(current_user)
    return current_user
