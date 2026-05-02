from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.db.crud.user import get_user_by_id
from app.core.nutrition import calculate_tdee, calculate_macros
from app.db.crud.diary import get_daily_stats
from datetime import date

router = APIRouter(prefix="/recommendations", tags=["recommendations"])

@router.get("/today")
async def get_recommendations(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    tdee = calculate_tdee(user)
    target_calories = calculate_macros(tdee, user.goal)["calories"]
    daily_stats = get_daily_stats(db, user_id, date.today())
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
