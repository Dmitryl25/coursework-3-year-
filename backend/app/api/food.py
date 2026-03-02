# Поиск по базе продуктов

from fastapi import APIRouter

router = APIRouter()

@router.get("/search")
async def search():
    return {"message": "Поиск еды пока в разработке"}