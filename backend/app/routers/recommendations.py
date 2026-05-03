from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.nutrition import calculate_tdee, calculate_macros
from app.db.crud.diary import get_daily_stats
from datetime import date
from app.core.dependencies import get_current_user
from app.db.models import User

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/today")
async def get_recommendations(current_user: User = Depends(get_current_user),
                              db: Session = Depends(get_db)):
    """Получение рекомендаций по текущим TDEE и цели пользователя"""
    tdee = calculate_tdee(current_user)
    target_calories = calculate_macros(tdee, current_user.goal)["calories"]
    daily_stats = get_daily_stats(db, current_user.id, date.today())
    remaining_calories = target_calories - daily_stats.total_calories
    response = ""
    if remaining_calories > 500:
        response = "Вы съели мало, не забудьте поесть"
    elif remaining_calories > 0:
        response = "Вы на верном пути, осталось X ккал"
    elif remaining_calories <= 0:
        response = "Дневная норма превышена"

    return {
        "tdee": tdee,
        "consumed": daily_stats,
        "remaining_calories": remaining_calories,
        "message": response.replace("X", str(round(remaining_calories)))
    }
