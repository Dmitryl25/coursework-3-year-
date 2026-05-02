# Расчет TDEE
def calculate_tdee(user) -> float:
    if user.gender == "male":
        BMR = 10 * user.weight + 6.25 * user.height - 5 * user.age + 5
    else:
        BMR = 10 * user.weight + 6.25 * user.height - 5 * user.age - 161
    TDEE = BMR * user.activity_level
    return TDEE


# Расчет БЖУ
def calculate_macros(tdee: float, goal: str) -> dict:
    if goal == "loss":
        calories = tdee - 500
        return {
            "calories": calories,
            "proteins": calories * 0.3 / 4,
            "fats": calories * 0.3 / 9,
            "carbohydrates": calories * 0.4 / 4
        }
    elif goal == "maintain":
        calories = tdee
        return {
            "calories": calories,
            "proteins": calories * 0.25 / 4,
            "fats": calories * 0.3 / 9,
            "carbohydrates": calories * 0.45 / 4
        }
    else:
        calories = tdee + 300
        return {
            "calories": calories,
            "proteins": calories * 0.25 / 4,
            "fats": calories * 0.25 / 9,
            "carbohydrates": calories * 0.5 / 4
        }