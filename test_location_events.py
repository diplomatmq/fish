# -*- coding: utf-8 -*-
"""
Тестовый скрипт для проверки работы новых событий на локациях.
"""
import sys
from database import db
from location_events import (
    SPAWN_EVENT_TYPE,
    MURDER_EVENT_TYPE,
    SCHOOL_EVENT_TYPE,
    get_event_description,
    format_event_info,
    LocationEvent,
)

def test_create_tables():
    """Проверяем создание таблиц для событий."""
    print("=== Тест 1: Создание таблиц ===")
    try:
        db._ensure_extended_gameplay_tables()
        print("✅ Таблицы созданы успешно")
        return True
    except Exception as e:
        print(f"❌ Ошибка при создании таблиц: {e}")
        return False


def test_spawn_event():
    """Тест события 'Нерест'."""
    print("\n=== Тест 2: Событие 'Нерест' ===")
    try:
        location = "Городской пруд"
        
        # Создаем событие
        event = db.start_location_event(
            event_type=SPAWN_EVENT_TYPE,
            location=location,
            duration_minutes=60,
            params={"catch_bonus_percent": 20}
        )
        
        print(f"✅ Событие создано: {event}")
        
        # Получаем активное событие
        active = db.get_active_location_event(location, SPAWN_EVENT_TYPE)
        print(f"✅ Активное событие получено: {active}")
        
        if not active:
            print("❌ Событие не найдено")
            return False
        
        # Форматируем информацию
        desc = get_event_description(SPAWN_EVENT_TYPE)
        print(f"✅ Описание: {desc}")
        
        # Останавливаем событие
        stopped = db.stop_location_event(location, SPAWN_EVENT_TYPE)
        print(f"✅ Событие остановлено: {stopped}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_murder_event():
    """Тест события 'Убийство'."""
    print("\n=== Тест 3: Событие 'Убийство' ===")
    try:
        location = "Городской пруд"
        
        # Получаем список рыб на локации
        with db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT DISTINCT fish_name FROM fish_locations WHERE LOWER(TRIM(location_name)) = LOWER(TRIM(?))',
                (location,)
            )
            location_fish = [row[0] for row in cursor.fetchall()]
        
        if not location_fish:
            print("❌ Нет рыб на локации")
            return False
        
        forced_fish = location_fish[0]
        print(f"Выбрана рыба для события: {forced_fish}")
        
        # Создаем событие
        event = db.start_location_event(
            event_type=MURDER_EVENT_TYPE,
            location=location,
            duration_minutes=30,
            params={"forced_fish": forced_fish}
        )
        
        print(f"✅ Событие создано: {event}")
        
        # Получаем активное событие
        active = db.get_active_location_event(location, MURDER_EVENT_TYPE)
        print(f"✅ Активное событие получено: {active}")
        
        if not active:
            print("❌ Событие не найдено")
            return False
        
        # Проверяем параметры
        if active['params'].get('forced_fish') != forced_fish:
            print(f"❌ Неверная рыба: {active['params'].get('forced_fish')} != {forced_fish}")
            return False
        
        print(f"✅ Принудительная рыба: {active['params'].get('forced_fish')}")
        
        # Останавливаем событие
        stopped = db.stop_location_event(location, MURDER_EVENT_TYPE)
        print(f"✅ Событие остановлено: {stopped}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_school_event():
    """Тест события 'Стайный инстинкт'."""
    print("\n=== Тест 4: Событие 'Стайный инстинкт' ===")
    try:
        location = "Городской пруд"
        test_user_id = 12345
        
        # Получаем список рыб на локации
        with db._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT DISTINCT fish_name FROM fish_locations WHERE LOWER(TRIM(location_name)) = LOWER(TRIM(?))',
                (location,)
            )
            location_fish = [row[0] for row in cursor.fetchall()]
        
        if not location_fish:
            print("❌ Нет рыб на локации")
            return False
        
        school_fish = location_fish[0]
        print(f"Выбрана рыба для стаи: {school_fish}")
        
        # Создаем событие
        event = db.start_location_event(
            event_type=SCHOOL_EVENT_TYPE,
            location=location,
            duration_minutes=60,
            params={
                "school_fish": school_fish,
                "weight_bonus_per_catch": 10,
                "max_bonus": 50,
                "max_chain": 5,
            }
        )
        
        print(f"✅ Событие создано: {event}")
        
        # Получаем активное событие
        active = db.get_active_location_event(location, SCHOOL_EVENT_TYPE)
        print(f"✅ Активное событие получено: {active}")
        
        if not active:
            print("❌ Событие не найдено")
            return False
        
        event_id = active['id']
        
        # Тестируем цепочку
        print("\n--- Тест цепочки ---")
        
        # Начальная цепочка
        chain = db.get_school_chain(test_user_id, event_id)
        print(f"Начальная цепочка: {chain}")
        
        # Обновляем цепочку
        db.update_school_chain(test_user_id, event_id, location, school_fish, 1)
        chain = db.get_school_chain(test_user_id, event_id)
        print(f"После 1 улова: {chain}")
        
        if chain.get('chain_count') != 1:
            print(f"❌ Неверная цепочка: {chain.get('chain_count')} != 1")
            return False
        
        # Увеличиваем цепочку
        db.update_school_chain(test_user_id, event_id, location, school_fish, 3)
        chain = db.get_school_chain(test_user_id, event_id)
        print(f"После 3 уловов: {chain}")
        
        if chain.get('chain_count') != 3:
            print(f"❌ Неверная цепочка: {chain.get('chain_count')} != 3")
            return False
        
        # Сбрасываем цепочку
        db.reset_school_chain(test_user_id, event_id)
        chain = db.get_school_chain(test_user_id, event_id)
        print(f"После сброса: {chain}")
        
        if chain.get('chain_count', 0) != 0:
            print(f"❌ Цепочка не сброшена: {chain.get('chain_count')} != 0")
            return False
        
        print("✅ Цепочка работает корректно")
        
        # Останавливаем событие
        stopped = db.stop_location_event(location, SCHOOL_EVENT_TYPE)
        print(f"✅ Событие остановлено: {stopped}")
        
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_event_format():
    """Тест форматирования информации о событии."""
    print("\n=== Тест 5: Форматирование событий ===")
    try:
        from datetime import datetime, timedelta
        
        # Создаем тестовое событие
        now = datetime.utcnow()
        ends_at = now + timedelta(minutes=45)
        
        event = LocationEvent(
            event_id=1,
            event_type=SPAWN_EVENT_TYPE,
            location="Городской пруд",
            started_at=now,
            ends_at=ends_at,
            is_active=True,
            params={"catch_bonus_percent": 20}
        )
        
        formatted = format_event_info(event)
        print(f"Форматированная информация:\n{formatted}")
        
        if "Нерест" not in formatted:
            print("❌ Неверное форматирование")
            return False
        
        print("✅ Форматирование работает")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Запуск всех тестов."""
    print("=" * 60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ СОБЫТИЙ НА ЛОКАЦИЯХ")
    print("=" * 60)
    
    tests = [
        test_create_tables,
        test_spawn_event,
        test_murder_event,
        test_school_event,
        test_event_format,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ Тест {test_func.__name__} провалился с исключением: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"РЕЗУЛЬТАТЫ: {passed} пройдено, {failed} провалено")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
