from sqlalchemy.orm import Session
import bcrypt

from ..models import User
from ..schemas import UserRegister, UserWithTDEE

def get_user_by_email(db: Session, email: str) -> User | None:
    """Получить пользователя по email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_id(db: Session, user_id: int) -> User | None:
    """Получить пользователя по ID"""
    return db.query(User).filter(User.id == user_id).first()

def create_user(db: Session, user: UserRegister) -> User:
    """Создать нового пользователя"""
    # Хешируем пароль
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(user.password.encode('utf-8'), salt)
    
    db_user = User(
        email=user.email,
        password_hash=hashed_password.decode('utf-8'),
        gender=user.gender,
        age=user.age,
        weight=user.weight,
        height=user.height,
        activity_level=user.activity_level
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def verify_password(db: Session, email: str, password: str) -> User | None:
    """Проверить пароль пользователя"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    
    if bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        return user
    return None

def calculate_tdee(user: User) -> float:
    """Рассчитать TDEE для пользователя"""
    if user.gender == "male":
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) + 5
    else:
        bmr = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) - 161
    
    return bmr * user.activity_level

def get_user_with_tdee(db: Session, user_id: int) -> UserWithTDEE | None:
    """Получить пользователя с рассчитанным TDEE"""
    user = get_user_by_id(db, user_id)
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
        tdee=tdee,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

def update_user_weight(db: Session, user_id: int, new_weight: float) -> User | None:
    """Обновить вес пользователя"""
    user = get_user_by_id(db, user_id)
    if user:
        user.weight = new_weight
        db.commit()
        db.refresh(user)
    return user

def update_user_activity(db: Session, user_id: int, new_activity: float) -> User | None:
    """Обновить уровень активности"""
    user = get_user_by_id(db, user_id)
    if user:
        user.activity_level = new_activity
        db.commit()
        db.refresh(user)
    return user