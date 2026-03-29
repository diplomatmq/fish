import sys
import sqlite3
from pathlib import Path

# Добавляем корневую папку проекта в sys.path, чтобы импортировать базу данных
root_path = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root_path))

from database import DB_PATH

def update_fish_location(fish_name, new_location):
    """
    Находит рыбу по названию и обновляет её локацию ТОЛЬКО в таблице caught_fish.
    """
    print(f"Поиск рыбы '{fish_name}' в таблице caught_fish ({DB_PATH})...")
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # 1. Проверяем, есть ли вообще такая рыба в инвентарях
        cursor.execute("SELECT COUNT(*), GROUP_CONCAT(DISTINCT location) FROM caught_fish WHERE fish_name = ?", (fish_name,))
        count, old_locations = cursor.fetchone()
        
        if count == 0:
            print(f"❌ Ошибка: Рыба с названием '{fish_name}' не найдена в таблице caught_fish (инвентарях).")
            return
            
        print(f"✅ Найдено записей с рыбой '{fish_name}': {count}. Текущие локации в инвентарях: '{old_locations}'")

        # 2. Обновляем локацию ТОЛЬКО в уже пойманных рыбах (таблица caught_fish)
        cursor.execute("UPDATE caught_fish SET location = ? WHERE fish_name = ?", (new_location, fish_name))
        caught_updated = cursor.rowcount
        
        conn.commit()
        
        print("\n--- РЕЗУЛЬТАТЫ ОБНОВЛЕНИЯ ---")
        print(f"🔹 Инвентари (таблица caught_fish): {caught_updated} записей обновлено.")
        print(f" Локация для всех '{fish_name}' в инвентарях успешно изменена на '{new_location}'!")
        print("ℹ️ Справочник рыб (таблица fish) и улов на лодках НЕ изменялись.")

    except Exception as e:
        conn.rollback()
        print(f"❌ Произошла ошибка при обновлении: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # Проверка наличия аргументов командной строки
    if len(sys.argv) < 3:
        print("❌ Ошибка: Недостаточно аргументов.")
        print('Использование: python tools/change_fish_location.py "Название рыбы" "Новая локация"')
        print('Пример: python tools/change_fish_location.py "Валаамка" "Озеро"')
        sys.exit(1)
    
    TARGET_FISH = sys.argv[1]
    NEW_LOCATION = sys.argv[2]
    
    update_fish_location(TARGET_FISH, NEW_LOCATION)
