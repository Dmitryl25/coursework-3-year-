from pydantic import BaseModel, EmailStr, Field, ConfigDict
from datetime import datetime, date
from typing import Optional, List
from enum import Enum
from app.db.models import UserGoal

class UserBase(BaseModel):
    email: EmailStr
    gender: str
    age: int = Field(..., ge=1, le=120)
    weight: float = Field(..., gt=0, le=500)
    height: float = Field(..., gt=0, le=300)
    activity_level: float = Field(..., ge=1.2, le=2.4)
    goal: UserGoal = Field(default=UserGoal.MAINTAIN)

class UserRegister(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)

class UserWithTDEE(UserResponse):
    tdee: float

# ========== FOOD SCHEMAS ==========
class FoodBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    calories: int = Field(..., gt=0)
    proteins: float = Field(..., ge=0)
    fats: float = Field(..., ge=0)
    carbohydrates: float = Field(..., ge=0)

class FoodCreate(FoodBase):
    pass

class FoodResponse(FoodBase):
    id: int
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)

class FoodSearchResult(FoodResponse):
    relevance: Optional[float] = None

# ========== DIARY SCHEMAS ==========
class DiaryEntryBase(BaseModel):
    food_id: int = Field(..., gt=0)
    weight: float = Field(..., gt=0, le=10000)
    datetime: datetime

class DiaryEntryCreate(DiaryEntryBase):
    pass

class DiaryEntryResponse(DiaryEntryBase):
    id: int
    user_id: int
    created_at: datetime
    food_name: str
    total_calories: float
    total_proteins: float
    total_fats: float
    total_carbohydrates: float
    
    model_config = ConfigDict(from_attributes=True)

class DailyStats(BaseModel):
    total_calories: float
    total_proteins: float
    total_fats: float
    total_carbohydrates: float
    entries_count: int

class DailySummary(DailyStats):
    date: str
    tdee: Optional[float] = None
    remaining_calories: Optional[float] = None

class WeeklyStats(BaseModel):
    week_start: date
    week_end: date
    daily_stats: List[DailyStats]
    total_calories: float
    average_calories: float

class RecommendationResponse(BaseModel):
    tdee: float
    consumed: DailyStats
    remaining_calories: float
    message: str


# ========== OCR SCHEMAS ==========
class OCRStatusEnum(str, Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"

class OCRLogBase(BaseModel):
    photo_path: str

class OCRLogCreate(OCRLogBase):
    pass

class OCRLogResponse(OCRLogBase):
    id: int
    user_id: int
    raw_text: Optional[str] = None
    status: OCRStatusEnum
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class OCRRawItem(BaseModel):
    raw_text: str = Field(..., min_length=1)
    weight_g: float = Field(..., gt=0, le=10000)

# Одна распознанная позиция с фото
class RecognizedItem(BaseModel):
    raw_text: str = Field(..., min_length=1)
    weight_g: float = Field(..., gt=0, le=10000)
    matched_food_id: Optional[int] = None
    matched_name: Optional[str] = None
    confidence: float = Field(..., ge=0.0, le=1.0)

# Запрос на поиск близких по семантике продуктов
class MatchRequest(BaseModel):
    items: List[OCRRawItem]

# Ответ от OCR
class OCRResponse(BaseModel):
    log_id: Optional[int] = None
    status: OCRStatusEnum
    items: List[OCRRawItem]

# Ответ, который отдаёт эндпоинт /ocr/recognize
class RecognitionResponse(BaseModel):
    log_id: Optional[int] = None
    status: OCRStatusEnum
    items: List[RecognizedItem]

# Запрос, который шлёт фронт в /diary/bulk после подтверждения
class BulkDiaryCreate(BaseModel):
    datetime: datetime
    items: List[RecognizedItem] = Field(..., min_length=1)

# Модели для токенов
class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

class RefreshRequest(BaseModel):
    refresh_token: str

