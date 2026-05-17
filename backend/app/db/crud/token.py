from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import Token


async def create_token(db: AsyncSession,
                       user_id: int,
                       expires_at: datetime,
                       ip_address: str | None = None) -> Token:
    """Добавление токена в базу"""
    token = Token(user_id=user_id, expires_at=expires_at, ip_address=ip_address)
    db.add(token)
    await db.commit()
    await db.refresh(token)
    return token


async def get_token(db: AsyncSession,
                    token_id: int) -> Token | None:
    """Получение токена из базы по id"""
    result = await db.execute(select(Token).where(Token.id == token_id))
    return result.scalar_one_or_none()


async def deactivate_token(db: AsyncSession,
                           token_id: int) -> None:
    """Деактивация токена"""
    await db.execute(update(Token).where(Token.id == token_id).values(is_active=False))
    await db.commit()


async def deactivate_all_user_tokens(db: AsyncSession,
                                     user_id: int) -> None:
    """Деактивация всех токенов одного пользователя"""
    await db.execute(update(Token).where(Token.user_id == user_id).values(is_active=False))
    await db.commit()
