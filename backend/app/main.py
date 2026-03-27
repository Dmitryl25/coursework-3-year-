from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.db.base import Base

# Создаем engine и session
engine = create_engine(settings.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Создаем таблицы
Base.metadata.create_all(bind=engine)

# Создаем экземпляр FastAPI
app = FastAPI(
    title="Food Diary API",
    description="API for tracking food intake and nutrition",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Функция для получения сессии
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Подключаем роутеры
from app.routers import auth, diary, food, ocr

app.include_router(auth.router)
app.include_router(diary.router)
app.include_router(food.router)
app.include_router(ocr.router)

# Эндпоинты
@app.get("/")
async def root():
    return {
        "message": "Food Diary API",
        "version": "1.0.0",
        "endpoints": [
            "/auth",
            "/diary",
            "/food",
            "/ocr"
        ]
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}