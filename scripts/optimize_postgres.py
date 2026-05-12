#!/usr/bin/env python3
"""
Скрипт для оптимизации PostgreSQL базы данных.
Выполняет VACUUM, ANALYZE и проверяет индексы.
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("ERROR: psycopg2 не установлен. Установите: pip install psycopg2-binary")
    sys.exit(1)

from config import DB_PATH


def get_connection():
    """Получить подключение к базе данных."""
    if DB_PATH.startswith('postgresql://') or DB_PATH.startswith('postgres://'):
        conn = psycopg2.connect(DB_PATH)
        return conn
    else:
        print("ERROR: Этот скрипт работает только с PostgreSQL")
        sys.exit(1)


def optimize_database():
    """Оптимизировать базу данных."""
    print("Подключение к базе данных...")
    conn = get_connection()
    
    # Для VACUUM нужен autocommit режим
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    print("\n=== Анализ таблиц ===")
    try:
        # Получаем список всех таблиц
        cursor.execute("""
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"Найдено таблиц: {len(tables)}")
        
        # ANALYZE для каждой таблицы
        for table in tables:
            print(f"  Анализ таблицы {table}...")
            cursor.execute(f"ANALYZE {table}")
        
        print("✓ ANALYZE завершен")
    except Exception as e:
        print(f"✗ Ошибка при ANALYZE: {e}")
    
    print("\n=== VACUUM таблиц ===")
    try:
        # VACUUM для основных таблиц
        important_tables = ['caught_fish', 'players', 'fish', 'fish_sales_history', 
                           'clan_members', 'clans', 'player_trophies']
        
        for table in important_tables:
            if table in tables:
                print(f"  VACUUM таблицы {table}...")
                cursor.execute(f"VACUUM {table}")
        
        print("✓ VACUUM завершен")
    except Exception as e:
        print(f"✗ Ошибка при VACUUM: {e}")
    
    print("\n=== Проверка индексов ===")
    try:
        # Проверяем неиспользуемые индексы
        cursor.execute("""
            SELECT schemaname, tablename, indexname, idx_scan
            FROM pg_stat_user_indexes
            WHERE idx_scan = 0
            AND indexname NOT LIKE '%_pkey'
            ORDER BY tablename, indexname
        """)
        unused_indexes = cursor.fetchall()
        
        if unused_indexes:
            print("  Неиспользуемые индексы (возможно стоит удалить):")
            for schema, table, index, scans in unused_indexes:
                print(f"    - {table}.{index} (сканирований: {scans})")
        else:
            print("  ✓ Все индексы используются")
        
        # Проверяем размеры индексов
        cursor.execute("""
            SELECT schemaname, tablename, indexname, 
                   pg_size_pretty(pg_relation_size(indexrelid)) as size
            FROM pg_stat_user_indexes
            ORDER BY pg_relation_size(indexrelid) DESC
            LIMIT 10
        """)
        large_indexes = cursor.fetchall()
        
        print("\n  Самые большие индексы:")
        for schema, table, index, size in large_indexes:
            print(f"    - {table}.{index}: {size}")
        
    except Exception as e:
        print(f"✗ Ошибка при проверке индексов: {e}")
    
    print("\n=== Статистика таблиц ===")
    try:
        cursor.execute("""
            SELECT schemaname, tablename, 
                   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size,
                   pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) as table_size,
                   pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) - 
                                  pg_relation_size(schemaname||'.'||tablename)) as indexes_size
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC
            LIMIT 15
        """)
        table_sizes = cursor.fetchall()
        
        print("\n  Самые большие таблицы:")
        for schema, table, total, table_size, indexes in table_sizes:
            print(f"    - {table}: {total} (таблица: {table_size}, индексы: {indexes})")
        
    except Exception as e:
        print(f"✗ Ошибка при получении статистики: {e}")
    
    print("\n=== Проверка медленных запросов ===")
    try:
        # Проверяем pg_stat_statements если доступно
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_extension WHERE extname = 'pg_stat_statements'
            )
        """)
        has_pg_stat = cursor.fetchone()[0]
        
        if has_pg_stat:
            cursor.execute("""
                SELECT 
                    substring(query, 1, 100) as short_query,
                    calls,
                    round(total_exec_time::numeric, 2) as total_time_ms,
                    round(mean_exec_time::numeric, 2) as mean_time_ms,
                    round((100 * total_exec_time / sum(total_exec_time) OVER ())::numeric, 2) as percentage
                FROM pg_stat_statements
                WHERE query NOT LIKE '%pg_stat_statements%'
                ORDER BY total_exec_time DESC
                LIMIT 10
            """)
            slow_queries = cursor.fetchall()
            
            if slow_queries:
                print("\n  Самые медленные запросы:")
                for query, calls, total, mean, pct in slow_queries:
                    print(f"    - {query}...")
                    print(f"      Вызовов: {calls}, Среднее время: {mean}ms, Процент: {pct}%")
            else:
                print("  ✓ Нет данных о медленных запросах")
        else:
            print("  ℹ pg_stat_statements не установлен (для мониторинга запросов)")
            print("    Установите: CREATE EXTENSION pg_stat_statements;")
        
    except Exception as e:
        print(f"✗ Ошибка при проверке запросов: {e}")
    
    cursor.close()
    conn.close()
    
    print("\n✓ Оптимизация завершена!")


if __name__ == '__main__':
    try:
        optimize_database()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
