from .base import Base, get_db, init_db
from .models import User, Food, DiaryEntry, OCRLog, OCRStatus

# Импортируем engine и SessionLocal только если они нужны
try:
    from .base import engine, SessionLocal
except ImportError:
    engine = None
    SessionLocal = None

__all__ = [
    'Base',
    'get_db',
    'init_db',
    'engine',
    'SessionLocal',
    'User',
    'Food',
    'DiaryEntry',
    'OCRLog',
    'OCRStatus'
]
