from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import asyncio
import bcrypt

from ..models import User
from ..schemas import UserRegister, UserWithTDEE
from app.core.nutrition import calculate_tdee


async def get_user_by_email(db: AsyncSession,
                            email: str) -> User | None:
    """Получить пользователя по email"""
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession,
                         user_id: int) -> User | None:
    """Получить пользователя по ID"""
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession,
                      user: UserRegister) -> User:
    """Создать нового пользователя"""
    salt = await asyncio.to_thread(bcrypt.gensalt)
    hashed_password = await asyncio.to_thread(bcrypt.hashpw, user.password.encode('utf-8'), salt)

    db_user = User(
        email=user.email,
        password_hash=hashed_password.decode('utf-8'),
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        height=user.height,
        activity_level=user.activity_level,
        goal=user.goal
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def verify_password(db: AsyncSession,
                          email: str,
                          password: str) -> User | None:
    """Проверить пароль пользователя"""
    user = await get_user_by_email(db, email)
    if not user:
        return None
    if await asyncio.to_thread(bcrypt.checkpw, password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None


async def get_user_with_tdee(db: AsyncSession,
                             user_id: int) -> UserWithTDEE | None:
    """Получить пользователя с рассчитанным TDEE"""
    user = await get_user_by_id(db, user_id)
    if not user:
        return None

    tdee = calculate_tdee(user)

    return UserWithTDEE(
        id=user.id,
        email=user.email,
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        height=user.height,
        activity_level=user.activity_level,
        goal=user.goal,
        tdee=tdee,
        created_at=user.created_at,
        updated_at=user.updated_at
    )


async def update_user_goal(db: AsyncSession,
                           user: User,
                           goal) -> User:
    """Обновить цель пользователя"""
    user.goal = goal
    return user


async def update_user_profile(db: AsyncSession,
                              user: User,
                              data) -> User:
    """Обновить антропометрические данные (только переданные поля)"""
    for field in ("weight", "height", "age", "activity_level", "gender"):
        value = getattr(data, field, None)
        if value is not None:
            setattr(user, field, value)
    return user
