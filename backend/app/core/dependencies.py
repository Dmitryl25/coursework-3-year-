from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.db.session import get_db
from app.db.crud.user import get_user_by_id
from app.db.crud.token import get_token
from app.core.security import decode_token
from app.db.models import User

bearer = HTTPBearer()

# получение пользователя из access токена
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                           db: AsyncSession = Depends(get_db)) -> User:
    payload = decode_token(credentials.credentials)
    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        user_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # получение самого пользователя из таблицы
    user = await get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user

# получение пользователя из refresh токена
async def get_current_user_from_refresh_token(credentials: HTTPAuthorizationCredentials = Depends(bearer),
                                              db: AsyncSession = Depends(get_db)) -> tuple[int, int]:
    payload = decode_token(credentials.credentials)

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")
    try:
        token_db_id = int(payload["sub"])
    except (KeyError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    # получение самого токена из таблицы
    token = await get_token(db, token_db_id)
    if not token or not token.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token revoked or not found")
    if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    return token.user_id, token_db_id
