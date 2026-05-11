import csv
from app.db.session import SessionLocal
from app.db.models import Food

def import_products(csv_file):
    db = SessionLocal()
    try:
        # Проверяем, есть ли уже продукты
        existing_count = db.query(Food).count()
        if existing_count > 0:
            print(f"В базе уже есть {existing_count} продуктов. Удаляем старые...")
            db.query(Food).delete()
            db.commit()
        
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
                    db.commit()
            
            db.commit()
            print(f"✓ Успешно импортировано {count} продуктов!")
            
            # Покажем первые 5 продуктов
            print("\nПервые 5 продуктов:")
            first_foods = db.query(Food).limit(5).all()
            for f in first_foods:
                print(f"  - {f.name}: {f.calories} ккал")
            
    except Exception as e:
        print(f"Ошибка: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_products("data/products_enhanced.csv")