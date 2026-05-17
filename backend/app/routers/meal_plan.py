from datetime import date, datetime, timezone, timedelta

MSK = timezone(timedelta(hours=3))

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.nutrition import calculate_macros, calculate_tdee
from app.db.crud.diary import create_diary_entry, get_confirmed_meals_today, get_daily_stats
from app.db.crud.food import get_food_by_id, get_foods_by_ids
from app.db.models import User
from app.db.schemas import (
    DiaryEntryCreate,
    MacroTargets,
    MealConfirmRequest,
    MealConfirmResponse,
    MealPlanResponse,
    MenuPlanRequest,
    MenuPlanResponse,
)
from app.db.session import get_db
from app.services.meal_planner import MEAL_RATIOS, get_planner

router = APIRouter(prefix="/meal-plan", tags=["meal-plan"])

ALL_MEALS = {"breakfast", "lunch", "dinner"}


@router.get("/today", response_model=MealPlanResponse)
async def get_meal_plan(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):
    """
    Сгенерировать план питания на оставшуюся часть дня.

    Учитывает уже съеденное и пропускает приёмы пищи,
    уже подтверждённые через POST /meal-plan/confirm.
    """
    tdee = calculate_tdee(current_user)
    targets = calculate_macros(tdee, current_user.goal)

    today = datetime.now(MSK).date()
    daily = await get_daily_stats(db, current_user.id, today)
    already_eaten = [{"calories": daily.total_calories,
                      "proteins": daily.total_proteins,
                      "fats": daily.total_fats,
                      "carbohydrates": daily.total_carbohydrates}]

    confirmed = await get_confirmed_meals_today(db, current_user.id)
    meals_to_plan = sorted(ALL_MEALS - confirmed,
                           key=lambda m: ["breakfast", "lunch", "dinner"].index(m))

    if not meals_to_plan:
        eaten = already_eaten[0]
        remaining_after = {
            k: round(max(targets[k] - eaten.get(k, 0.0), 0.0), 1)
            for k in targets
        }
        surplus = {
            k: round(eaten.get(k, 0.0) - targets[k], 1)
            for k in targets
            if eaten.get(k, 0.0) > targets[k]
        }
        return {
            "breakfast": [], "lunch": [], "dinner": [],
            "totals": {"calories": 0.0, "proteins": 0.0, "fats": 0.0, "carbohydrates": 0.0},
            "targets": targets,
            "remaining_after_plan": remaining_after,
            "surplus": surplus,
            "coverage_pct": 100.0,
            "confirmed_meals": sorted(confirmed),
            "message": "Все приёмы пищи на сегодня подтверждены.",
        }

    daily_seed = today.toordinal()
    plan = get_planner().plan_day(targets, already_eaten, seed=daily_seed, meals_to_plan=meals_to_plan)
    plan["confirmed_meals"] = sorted(confirmed)
    return plan


@router.post("/confirm", response_model=MealConfirmResponse)
async def confirm_meal(payload: MealConfirmRequest,
                       current_user: User = Depends(get_current_user),
                       db: AsyncSession = Depends(get_db)):
    """
    Подтвердить приём пищи из плана.

    Сохраняет позиции в дневник с тегом meal_type,
    чтобы следующий GET /meal-plan/today пропустил этот приём.

    """
    confirmed = await get_confirmed_meals_today(db, current_user.id)
    if payload.meal in confirmed:
        raise HTTPException(status_code=409,
                            detail=f"Приём пищи '{payload.meal}' уже подтверждён сегодня.")

    now = datetime.now(MSK)
    saved_count = 0
    total = {
        "calories": 0.0,
        "proteins": 0.0,
        "fats": 0.0,
        "carbohydrates": 0.0
    }

    for item in payload.items:
        food = await get_food_by_id(db, item.food_id)
        if food is None:
            raise HTTPException(status_code=404,
                                detail=f"Продукт с id={item.food_id} не найден")

        entry = DiaryEntryCreate(food_id=item.food_id,
                                 weight=item.portion_g,
                                 datetime=now,
                                 meal_type=payload.meal)

        await create_diary_entry(db, current_user.id, entry)
        saved_count += 1

        factor = item.portion_g / 100
        total["calories"]      += food.calories      * factor
        total["proteins"]      += food.proteins      * factor
        total["fats"]          += food.fats          * factor
        total["carbohydrates"] += food.carbohydrates * factor

    await db.commit()

    return MealConfirmResponse(
        meal=payload.meal,
        saved_count=saved_count,
        total_calories=round(total["calories"], 1),
        total_proteins=round(total["proteins"], 1),
        total_fats=round(total["fats"], 1),
        total_carbohydrates=round(total["carbohydrates"], 1),
    )


@router.post("/from-menu", response_model=MenuPlanResponse)
async def plan_from_menu(payload: MenuPlanRequest,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    """
    Подобрать блюда и порции из меню, отсканированного через OCR.

    Клиент передаёт список food_id, полученных после /ocr/recognize.
    Планировщик выбирает оптимальную комбинацию (3-4 блюда) и рассчитывает
    порции под калорийный бюджет указанного приёма пищи.
    """
    tdee = calculate_tdee(current_user)
    targets = calculate_macros(tdee, current_user.goal)

    today = datetime.now(MSK).date()
    daily = await get_daily_stats(db, current_user.id, today)

    already_cal = daily.total_calories
    remaining_cal = max(targets["calories"] - already_cal, 0.0)

    meal = payload.meal
    ratio = MEAL_RATIOS.get(meal, 0.25)   # snack получает 25% как запасной вариант
    active_ratios = MEAL_RATIOS if meal in MEAL_RATIOS else {**MEAL_RATIOS, meal: ratio}
    total_ratio = sum(active_ratios.values())
    norm_ratio = ratio / total_ratio

    cal_budget = remaining_cal * norm_ratio
    macro_budget = {
        "proteins":      max(targets["proteins"]      - daily.total_proteins, 0.0)      * norm_ratio,
        "fats":          max(targets["fats"]          - daily.total_fats, 0.0)          * norm_ratio,
        "carbohydrates": max(targets["carbohydrates"] - daily.total_carbohydrates, 0.0) * norm_ratio,
    }

    if cal_budget < 50:
        raise HTTPException(status_code=400, detail="Калорийный бюджет на этот приём уже исчерпан.")

    foods = await get_foods_by_ids(db, payload.food_ids)

    products = [
        {
            "id":            f.id,
            "name":          f.name,
            "calories":      f.calories,
            "proteins":      f.proteins,
            "fats":          f.fats,
            "carbohydrates": f.carbohydrates,
            "min_portion":   f.min_portion or 50,
            "max_portion":   f.max_portion or 500,
            "category":      f.category or "menu",
        }
        for f in foods if f is not None
    ]

    if not products:
        raise HTTPException(status_code=404,
                            detail="Ни один из переданных продуктов не найден в базе.")

    items = get_planner().plan_from_menu(products, cal_budget, macro_budget)

    totals = MacroTargets(
        calories=round(sum(i["calories_total"] for i in items), 1),
        proteins=round(sum(i["proteins_total"] for i in items), 1),
        fats=round(sum(i["fats_total"] for i in items), 1),
        carbohydrates=round(sum(i["carbohydrates_total"] for i in items), 1),
    )

    return MenuPlanResponse(
        meal=meal,
        items=items,
        totals=totals,
        cal_budget=round(cal_budget, 1),
    )


@router.post("/custom")
async def get_custom_meal_plan(targets: dict,
                               current_user: User = Depends(get_current_user)):
    required = {"calories", "proteins", "fats", "carbohydrates"}
    missing = required - targets.keys()
    if missing:
        raise HTTPException(status_code=422,
                            detail=f"Отсутствуют поля: {', '.join(missing)}")

    plan = get_planner().plan_day(targets)
    return plan
