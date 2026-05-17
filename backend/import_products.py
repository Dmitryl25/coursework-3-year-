import csv
import asyncio
from sqlalchemy import select, delete, func
from app.db.session import AsyncSessionLocal
from app.db.models import Food


async def import_products(csv_file):
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(select(func.count()).select_from(Food))
            existing_count = result.scalar()
            if existing_count > 0:
                print(f"В базе уже есть {existing_count} продуктов. Удаляем старые...")
                await db.execute(delete(Food))
                await db.commit()

            count = 0
            with open(csv_file, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)

                for row in reader:
                    food = Food(
                        name=row['name'],
                        proteins=float(row['proteins']),
                        fats=float(row['fats']),
                        carbohydrates=float(row['carbs']),
                        calories=int(row['calories']),
                        meal_type=row.get('meal_type'),
                        category=row.get('category'),
                        min_portion=int(row['min_portion']) if row.get('min_portion') else None,
                        max_portion=int(row['max_portion']) if row.get('max_portion') else None,
                    )
                    db.add(food)
                    count += 1

                    if count % 100 == 0:
                        print(f"Добавлено {count} продуктов...")
                        await db.commit()

                await db.commit()
                print(f"✓ Успешно импортировано {count} продуктов!")

                print("\nПервые 5 продуктов:")
                result = await db.execute(select(Food).limit(5))
                first_foods = result.scalars().all()
                for f in first_foods:
                    print(f"  - {f.name}: {f.calories} ккал")

        except Exception as e:
            print(f"Ошибка: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(import_products("data/products_enhanced.csv"))
