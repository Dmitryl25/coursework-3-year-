# Регистрация и логин

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class UserRegister(BaseModel):
    #email
    #password
    weight: float
    height: float
    age: int
    gender: str

@router.post("/register")
async def register(user: UserRegister):
    gender = 5 if user.gender == "male" else -161
    tdee = (10 * user.weight) + (6.25 * user.height) - (5 * user.age) + gender

    return {
        "status": "created",
        "calculated_tdee": tdee,
        "recommendation": "Данные сохранены, норма калорий рассчитана."
    }

@router.post("/login")
async def login(user: UserRegister):
    return {"message": "Логин пока в разработке"}