from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.db.models import Token

def create_token(db: Session, user_id: int,
                 expires_at: datetime,
                 ip_address: str | None = None) -> Token:
    """Добавление токена в базу"""
    token = Token(user_id=user_id, expires_at=expires_at, ip_address=ip_address)
    db.add(token)
    db.commit()
    db.refresh(token)
    return token

def get_token(db: Session, token_id: int) -> Token | None:
    """Получение токена из базы по id"""
    return db.query(Token).filter(Token.id == token_id).first()

def deactivate_token(db: Session, token_id: int) -> None:
    """Деактивация токена"""
    db.query(Token).filter(Token.id == token_id).update({"is_active": False})
    db.commit()


def deactivate_all_user_tokens(db: Session, user_id: int) -> None:
    """Деактивация всех токенов одного пользователя"""
    db.query(Token).filter(Token.user_id == user_id).update({"is_active": False})
    db.commit()