from contextlib import asynccontextmanager
import logging
from fastapi import FastAPI

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.db.models import Base
from app.db.session import engine
from app.services.matching import faiss_init as init_matching
from ml_models.ocr.engine import ocr_init as init_ocr
from ml_models.classifier.engine import classifier_init as init_classifier

logger = logging.getLogger(__name__)


# lifespan для загрузки моделей при старте сервера
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
        await conn.run_sync(Base.metadata.create_all)

    try:
        init_matching()
        logger.info("✅ FAISS matching engine loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load FAISS: {e}", exc_info=True)
        raise RuntimeError("Cannot start application: FAISS loading failed") from e

    try:
        init_ocr()
        logger.info("✅ EasyOCR engine loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load EasyOCR: {e}", exc_info=True)
        raise RuntimeError("Cannot start application: EasyOCR loading failed") from e

    try:
        init_classifier()
        logger.info("✅ MobileNetV3 classifier loaded")
    except Exception as e:
        logger.error(f"❌ Failed to load classifier: {e}", exc_info=True)
        raise RuntimeError("Cannot start application: Classifier loading failed") from e

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