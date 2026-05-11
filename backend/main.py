from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.models import Base
from app.db.session import engine
from app.services.matching import faiss_init as init_matching
from ml_models.ocr.engine import ocr_init as init_ocr
from ml_models.classifier.engine import classifier_init as init_classifier


# lifespan для загрузки моделей при старте сервера
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    init_matching()         # загрузка FAISS
    init_ocr()              # загрузка EasyOCR
    init_classifier()       # загрузка MobileNetV3
    yield


app = FastAPI(
    title="Food Diary API",
    description="API for tracking food intake and nutrition",
    version="1.0.0",
    lifespan=lifespan
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем роутеры
from app.routers import auth, diary, food, ocr, recommendations, meal_plan

app.include_router(auth.router)
app.include_router(diary.router)
app.include_router(food.router)
app.include_router(ocr.router)
app.include_router(recommendations.router)
app.include_router(meal_plan.router)

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