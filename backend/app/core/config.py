# Настройки (DB_URL, Secret Keys)
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./food_diary.db")
    SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # Загрузка директория
    UPLOAD_DIR = "uploads/photos"
    
    # Создаем директорию если её нет
    os.makedirs(UPLOAD_DIR, exist_ok=True)

# Для удобства создаем экземпляр
settings = Config()