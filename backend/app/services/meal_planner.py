"""
Планировщик питания на день — решение задачи о рюкзаке.

Алгоритм двухфазный:
  1. Отбор продуктов (жадный, с ограничением разнообразия):
     - Для каждого приёма пищи выбирается по одному продукту
       из приоритетных категорий (белки, каши, овощи и т.д.)
     - Не более MAX_CATEGORIES_PER_MEAL категорий на приём пищи
  2. Оптимизация порций (непрерывный рюкзак через SLSQP):
     - Найти веса порций w_i ∈ [min_portion_i, max_portion_i] такие,
       чтобы минимизировать квадратичное отклонение от целевых
       калорий и макронутриентов на данный приём пищи
Процедура повторяется MAX_RETRIES раз со случайным перемешиванием
продуктов, сохраняется лучший результат.
"""

from __future__ import annotations

import random
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from scipy.optimize import minimize

PRODUCTS_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "products_enhanced.csv"

# Доля калорий на каждый приём пищи
MEAL_RATIOS: dict[str, float] = {
    "breakfast": 0.30,
    "lunch":     0.40,
    "dinner":    0.30,
}

# Категории, которые в первую очередь попадают в каждый приём пищи
PRIORITY_CATEGORIES: dict[str, list[str]] = {
    "breakfast": ["porridge", "eggs", "dairy", "fruit", "nuts", "bakery"],
    "lunch":     ["meat","soup", "garnish", "fish", "seafood",  "vegetable", "ready_meal", "salad"],
    "dinner":    ["meat", "garnish", "fish", "seafood",  "vegetable", "dairy", "ready_meal", "salad"],
}

# Дополнительные категории, доступные для приёма пищи независимо от meal_type в CSV.
EXTRA_ELIGIBLE_CATEGORIES: dict[str, list[str]] = {
    "dinner": ["garnish", "seafood", "ready_meal"],
    "lunch":  ["seafood", "ready_meal"],
}

# Гарантированные категории: список альтернативных наборов обязательных слотов.
# Каждый retry случайно выбирает один из вариантов — лучший score побеждает.
# Для обеда: либо классика (мясо + гарнир), либо готовое блюдо (заменяет оба).
MANDATORY_CATEGORIES: dict[str, list[list[str]]] = {
    "breakfast": [["porridge"]],
    "lunch":     [["meat", "garnish"], ["ready_meal"]],
    "dinner":    [[]],
}

# Взаимоисключающие категории: выбор одной блокирует остальные в том же приёме пищи.
CATEGORY_CONFLICTS: dict[str, frozenset[str]] = {
    "ready_meal": frozenset({"meat", "garnish"}),
    "meat":       frozenset({"ready_meal"}),
    "garnish":    frozenset({"ready_meal"}),
}

# Категории, которые никогда не выбираются как основное блюдо.
EXCLUDED_CATEGORIES: frozenset[str] = frozenset({
    "fat", "sweet", "alcohol", "sauce", "drink", "processed",
})
MAX_CATEGORIES_PER_MEAL = 4
MAX_RETRIES = 20

LAST_MEAL_CAP_FACTOR = 1.5


class MealPlanner:
    def __init__(self, products_path: str | Path = PRODUCTS_PATH) -> None:
        df = pd.read_csv(products_path)
        df.columns = df.columns.str.strip().str.lower()
        if "carbs" in df.columns and "carbohydrates" not in df.columns:
            df = df.rename(columns={"carbs": "carbohydrates"})
        self._df = df

    # ------------------------------------------------------------------
    # Публичные методы
    # ------------------------------------------------------------------

    def plan_day(self,
                 targets: dict,
                 already_eaten: Optional[list[dict]] = None,
                 seed: Optional[int] = None,
                 meals_to_plan: Optional[list[str]] = None) -> dict:

        # XOR seed с хэшем названия приёма → независимый RNG для каждого из них
        def meal_rng(meal_name: str) -> random.Random:
            s = seed if seed is not None else random.randint(0, 2**31)
            return random.Random(s ^ (abs(hash(meal_name)) & 0xFFFF))

        raw_remaining = self._subtract_eaten(targets, already_eaten or [])
        surplus = {
            k: round(-v, 1) for k, v in raw_remaining.items() if v < 0
        }
        remaining = {k: max(0.0, v) for k, v in raw_remaining.items()}

        if remaining["calories"] <= 50:
            return {
                "breakfast": [],
                "lunch": [],
                "dinner": [],
                "totals": {k: 0.0 for k in targets},
                "targets": targets,
                "remaining_after_plan": remaining,
                "surplus": surplus,
                "coverage_pct": 100.0,
                "message": "Дневная норма уже выполнена.",
            }

        active_meals = meals_to_plan if meals_to_plan is not None else list(MEAL_RATIOS.keys())
        active_ratios = {m: MEAL_RATIOS[m] for m in active_meals if m in MEAL_RATIOS}
        total_ratio = sum(active_ratios.values()) or 1.0

        plan: dict[str, list[dict]] = {"breakfast": [], "lunch": [], "dinner": []}
        allocated_cal = 0.0
        allocated_macros = {"proteins": 0.0, "fats": 0.0, "carbohydrates": 0.0}

        meals = [m for m in MEAL_RATIOS.keys() if m in active_meals]
        for idx, meal_name in enumerate(meals):
            is_last = idx == len(meals) - 1
            if is_last:
                max_cal = remaining["calories"] * MEAL_RATIOS[meal_name] * LAST_MEAL_CAP_FACTOR
                cal_budget = min(max(remaining["calories"] - allocated_cal, 0), max_cal)
                macro_budget = {
                    k: max(remaining[k] - allocated_macros[k], 0.0) * (cal_budget / max(remaining["calories"] - allocated_cal, 1))
                    for k in allocated_macros
                }
            else:
                ratio = active_ratios[meal_name] / total_ratio
                cal_budget = remaining["calories"] * ratio
                macro_budget = {k: remaining[k] * ratio for k in allocated_macros}

            items = self._plan_meal(meal_name, cal_budget, macro_budget, meal_rng(meal_name))
            plan[meal_name] = items

            for item in items:
                allocated_cal += item["calories_total"]
                for macro in allocated_macros:
                    allocated_macros[macro] += item[f"{macro}_total"]

        totals = self._sum_totals(plan)
        coverage = round(
            sum(
                min(totals[k] / max(remaining[k], 1) * 100, 100.0)
                for k in ("calories", "proteins", "fats", "carbohydrates")
            ) / 4,
            1,
        )

        eaten_totals: dict[str, float] = {
            key: sum(float(e.get(key, 0)) for e in (already_eaten or []))
            for key in targets
        }
        remaining_after = {
            k: round(max(targets[k] - eaten_totals.get(k, 0.0) - totals.get(k, 0.0), 0.0), 1)
            for k in targets
        }

        return {
            "breakfast": plan["breakfast"],
            "lunch": plan["lunch"],
            "dinner": plan["dinner"],
            "totals": totals,
            "targets": targets,
            "remaining_after_plan": remaining_after,
            "surplus": surplus,
            "coverage_pct": coverage,
        }

    def plan_from_menu(self,
                       products: list[dict],
                       cal_budget: float,
                       macro_budget: dict,
                       seed: Optional[int] = None) -> list[dict]:
        """Выбрать оптимальные порции из произвольного списка продуктов (меню из OCR)."""
        rng = random.Random(seed)
        best_items: list[dict] = []
        best_score = float("inf")

        for _ in range(MAX_RETRIES):
            n = min(MAX_CATEGORIES_PER_MEAL, len(products))
            subset = rng.sample(products, n)
            portions = self._optimize_portions(subset, cal_budget, macro_budget)
            score = self._score(subset, portions, cal_budget, macro_budget)
            if score < best_score:
                best_score = score
                best_items = self._build_items(subset, portions)

        return best_items

    # ------------------------------------------------------------------
    # Внутренние методы
    # ------------------------------------------------------------------

    def _subtract_eaten(self, targets: dict, eaten: list[dict]) -> dict:
        result = {k: float(v) for k, v in targets.items()}
        for entry in eaten:
            result["calories"]      -= float(entry.get("calories", 0))
            result["proteins"]      -= float(entry.get("proteins", 0))
            result["fats"]          -= float(entry.get("fats", 0))
            result["carbohydrates"] -= float(entry.get("carbohydrates", 0))
        return result

    def _plan_meal(self,
                   meal_name: str,
                   cal_budget: float,
                   macro_budget: dict,
                   rng: random.Random) -> list[dict]:
        if cal_budget < 50:
            return []

        extra_cats = EXTRA_ELIGIBLE_CATEGORIES.get(meal_name, [])
        eligible = self._df[
            (
                (self._df["meal_type"] == meal_name) |
                (self._df["meal_type"] == "any") |
                (self._df["category"].isin(extra_cats))
            ) & ~self._df["category"].isin(EXCLUDED_CATEGORIES)
        ]

        best_items: list[dict] = []
        best_score = float("inf")

        for _ in range(MAX_RETRIES):
            products = self._select_diverse(eligible, meal_name, rng)
            if not products:
                continue

            portions = self._optimize_portions(products, cal_budget, macro_budget)
            score = self._score(products, portions, cal_budget, macro_budget)

            if score < best_score:
                best_score = score
                best_items = self._build_items(products, portions)

        return best_items

    def _select_diverse(self,
                        eligible: pd.DataFrame,
                        meal_name: str,
                        rng: random.Random) -> list[dict]:
        """Выбрать по одному продукту из разных категорий.

        Обязательные категории (MANDATORY_CATEGORIES) всегда занимают первые слоты.
        Оставшиеся слоты заполняются случайно из пула: приоритетные (без обязательных) + прочие.
        Это гарантирует, что все категории из PRIORITY_CATEGORIES со временем попадают в план.
        """
        alternatives = MANDATORY_CATEGORIES.get(meal_name, [[]])
        mandatory = rng.choice(alternatives)
        priority = PRIORITY_CATEGORIES.get(meal_name, [])
        available_cats = eligible["category"].unique().tolist()

        mandatory_cats = [c for c in mandatory if c in available_cats]
        # Приоритетные и rest перемешиваются раздельно:
        # priority даёт разнообразие внутри своей группы, rest никогда не вытесняет priority.
        optional_priority = [c for c in priority if c not in mandatory and c in available_cats]
        rest = [c for c in available_cats if c not in priority and c not in mandatory]
        rng.shuffle(optional_priority)
        rng.shuffle(rest)

        ordered = mandatory_cats + optional_priority + rest

        selected: list[dict] = []
        blocked: set[str] = set()
        for category in ordered:
            if len(selected) >= MAX_CATEGORIES_PER_MEAL:
                break
            if category in blocked:
                continue
            cat_df = eligible[eligible["category"] == category]
            row = cat_df.sample(1, random_state=rng.randint(0, 2**31)).iloc[0]
            selected.append(row.to_dict())
            blocked |= CATEGORY_CONFLICTS.get(category, frozenset())

        return selected

    def _optimize_portions(self,
                           products: list[dict],
                           cal_budget: float,
                           macro_budget: dict) -> np.ndarray:
        def objective(w: np.ndarray) -> float:
            cal  = sum(p["calories"]      * w[i] / 100 for i, p in enumerate(products))
            prot = sum(p["proteins"]      * w[i] / 100 for i, p in enumerate(products))
            fat  = sum(p["fats"]          * w[i] / 100 for i, p in enumerate(products))
            carb = sum(p["carbohydrates"] * w[i] / 100 for i, p in enumerate(products))

            def rel_err(actual: float, target: float) -> float:
                return ((actual - target) / max(target, 1.0)) ** 2

            return (
                2.0 * rel_err(cal,  cal_budget) +
                rel_err(prot, macro_budget["proteins"]) +
                rel_err(fat,  macro_budget["fats"]) +
                rel_err(carb, macro_budget["carbohydrates"])
            )

        bounds = [(p["min_portion"], p["max_portion"]) for p in products]
        x0 = [(lo + hi) / 2 for lo, hi in bounds]

        def make_constraints(fat_factor: float, carb_factor: float) -> list[dict]:
            fat_limit = macro_budget["fats"] * fat_factor
            prot_min  = macro_budget["proteins"] * 0.90
            carb_min  = macro_budget["carbohydrates"] * carb_factor
            return [
                {
                    "type": "ineq",
                    "fun": lambda w, fl=fat_limit: fl - sum(
                        p["fats"] * w[i] / 100 for i, p in enumerate(products)
                    ),
                },
                {
                    "type": "ineq",
                    "fun": lambda w, pm=prot_min: sum(
                        p["proteins"] * w[i] / 100 for i, p in enumerate(products)
                    ) - pm,
                },
                {
                    "type": "ineq",
                    "fun": lambda w, cm=carb_min: sum(
                        p["carbohydrates"] * w[i] / 100 for i, p in enumerate(products)
                    ) - cm,
                },
            ]

        result = minimize(objective, x0, bounds=bounds,
                          constraints=make_constraints(fat_factor=1.05, carb_factor=0.85),
                          method="SLSQP", options={"ftol": 1e-6, "maxiter": 200})

        actual_cal = sum(p["calories"] * result.x[i] / 100 for i, p in enumerate(products))
        if actual_cal < cal_budget * 0.85:
            result = minimize(objective, x0, bounds=bounds,
                              constraints=make_constraints(fat_factor=1.15, carb_factor=0.70),
                              method="SLSQP", options={"ftol": 1e-6, "maxiter": 200})

        return np.round(result.x).astype(float)

    def _score(self,
               products: list[dict],
               portions: np.ndarray,
               cal_budget: float,
               macro_budget: dict) -> float:

        cal  = sum(p["calories"]      * portions[i] / 100 for i, p in enumerate(products))
        prot = sum(p["proteins"]      * portions[i] / 100 for i, p in enumerate(products))
        fat  = sum(p["fats"]          * portions[i] / 100 for i, p in enumerate(products))
        carb = sum(p["carbohydrates"] * portions[i] / 100 for i, p in enumerate(products))

        return (
            abs(cal  - cal_budget)                   / max(cal_budget, 1) +
            abs(prot - macro_budget["proteins"])      / max(macro_budget["proteins"], 1) +
            abs(fat  - macro_budget["fats"])          / max(macro_budget["fats"], 1) +
            abs(carb - macro_budget["carbohydrates"]) / max(macro_budget["carbohydrates"], 1)
        )

    def _build_items(self, products: list[dict], portions: np.ndarray) -> list[dict]:
        items = []
        for i, p in enumerate(products):
            w = float(portions[i])
            items.append({
                "food_id":             int(p["id"]),
                "name":                p["name"],
                "portion_g":           round(w, 1),
                "calories_total":      round(p["calories"]      * w / 100, 1),
                "proteins_total":      round(p["proteins"]      * w / 100, 1),
                "fats_total":          round(p["fats"]          * w / 100, 1),
                "carbohydrates_total": round(p["carbohydrates"] * w / 100, 1),
                "category":            p["category"],
            })
        return items

    def _sum_totals(self, plan: dict[str, list[dict]]) -> dict:
        totals = {"calories": 0.0, "proteins": 0.0, "fats": 0.0, "carbohydrates": 0.0}
        for items in plan.values():
            for item in items:
                totals["calories"]      += item["calories_total"]
                totals["proteins"]      += item["proteins_total"]
                totals["fats"]          += item["fats_total"]
                totals["carbohydrates"] += item["carbohydrates_total"]
        return {k: round(v, 1) for k, v in totals.items()}


# Синглтон — загружается один раз при старте
_planner: Optional[MealPlanner] = None


def get_planner() -> MealPlanner:
    global _planner
    if _planner is None:
        _planner = MealPlanner()
    return _planner
