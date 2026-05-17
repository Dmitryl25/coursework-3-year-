# Описание таблиц (User, Food, Entry)
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()

# Enums для статусов
class OCRStatus(enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class UserGoal(str, enum.Enum):
    LOSS = "loss"
    MAINTAIN = "maintain"
    MASS = "mass"

class Token(Base):
    __tablename__ = "tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    ip_address = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="tokens")

    __table_args__ = (
        Index("ix_tokens_user_id", "user_id"),
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # Храним только хэш!
    
    # Антропометрические данные для расчета TDEE
    gender = Column(String(10), nullable=False)  # 'male' или 'female'
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)  # в кг
    height = Column(Float, nullable=False)  # в см
    activity_level = Column(Float, nullable=False)  # коэффициент от 1.2 до 2.4
    goal = Column(Enum(UserGoal), nullable=False, default=UserGoal.MAINTAIN)

    diary_entries = relationship("DiaryEntry", back_populates="user", cascade="all, delete-orphan")
    ocr_logs = relationship("OCRLog", back_populates="user", cascade="all, delete-orphan")
    tokens = relationship("Token", back_populates="user", cascade="all, delete-orphan")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Food(Base):
    __tablename__ = "foods"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    
    # КБЖУ на 100 грамм
    calories = Column(Integer, nullable=False)  # ккал
    proteins = Column(Float, nullable=False)    # белки в граммах
    fats = Column(Float, nullable=False)        # жиры в граммах
    carbohydrates = Column(Float, nullable=False)  # углеводы в граммах

    # Метаданные для планировщика
    meal_type = Column(String(20), nullable=True)   # breakfast / lunch / dinner / any
    category = Column(String(50), nullable=True)
    min_portion = Column(Integer, nullable=True)    # граммы
    max_portion = Column(Integer, nullable=True)    # граммы


    diary_entries = relationship("DiaryEntry", back_populates="food")

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_food_name_trgm", "name", postgresql_using="gin",
              postgresql_ops={"name": "gin_trgm_ops"}),
    )

class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Внешние ключи
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    food_id = Column(Integer, ForeignKey("foods.id", ondelete="RESTRICT"), nullable=False)
    
    # Данные приема пищи
    weight = Column(Float, nullable=False)  # вес порции в граммах
    datetime = Column(DateTime(timezone=True), nullable=False, index=True)
    meal_type = Column(String(20), nullable=True)  # breakfast / lunch / dinner / snack / None

    user = relationship("User", back_populates="diary_entries")
    food = relationship("Food", back_populates="diary_entries")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Индекс для быстрых запросов по пользователю и дате
    __table_args__ = (
        Index('idx_user_datetime', 'user_id', 'datetime'),
    )

class OCRLog(Base):
    __tablename__ = "ocr_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    photo_path = Column(String(512), nullable=False)  # путь к файлу на сервере
    raw_text = Column(String(2000))  # распознанный текст (может быть длинным)
    status = Column(Enum(OCRStatus), default=OCRStatus.PENDING, nullable=False)

    user = relationship("User", back_populates="ocr_logs")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())