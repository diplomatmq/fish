#!/usr/bin/env python3
"""
Скрипт для проверки всех исправлений производительности.
"""

import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    import psycopg2
except ImportError:
    print("ERROR: psycopg2 не установлен. Установите: pip install psycopg2-binary")
    sys.exit(1)

from config import DB_PATH


def check_database():
    """Проверить базу данных на наличие всех исправлений."""
    
    if not (DB_PATH.startswith('postgresql://') or DB_PATH.startswith('postgres://')):
        print("ERROR: Этот скрипт работает только с PostgreSQL")
        sys.exit(1)
    
    print("Подключение к базе данных...")
    conn = psycopg2.connect(DB_PATH)
    cursor = conn.cursor()
    
    issues = []
    fixes = []
    
    print("\n=== Проверка таблиц ===")
    
    # Проверка user_fish_stats
    cursor.execute("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'user_fish_stats'
        )
    """)
    if cursor.fetchone()[0]:
        print("✓ Таблица user_fish_stats существует")
        fixes.append("user_fish_stats table exists")
    else:
        print("✗ Таблица user_fish_stats НЕ существует")
        issues.append("user_fish_stats table missing")
    
    print("\n=== Проверка индексов ===")
    
    # Список ожидаемых индексов
    expected_indexes = [
        ('caught_fish', 'idx_cf_user_sold'),
        ('caught_fish', 'idx_cf_user_sold_name'),
        ('caught_fish', 'idx_cf_caught_at'),
        ('caught_fish', 'idx_cf_fish_name'),
        ('fish_sales_history', 'idx_fsh_fish_sold'),
        ('fish_sales_history', 'idx_fsh_sold_at'),
        ('players', 'idx_players_tickets'),
        ('players', 'idx_players_gold_tickets'),
        ('players', 'idx_players_user_id'),
        ('clan_members', 'idx_clan_members_user'),
        ('clan_members', 'idx_clan_members_clan'),
        ('user_fish_stats', 'idx_ufs_user'),
    ]
    
    missing_indexes = []
    for table, index in expected_indexes:
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM pg_indexes 
                WHERE schemaname = 'public' 
                AND tablename = %s 
                AND indexname = %s
            )
        """, (table, index))
        
        if cursor.fetchone()[0]:
            print(f"✓ Индекс {table}.{index} существует")
            fixes.append(f"{table}.{index} index exists")
        else:
            print(f"✗ Индекс {table}.{index} НЕ существует")
            missing_indexes.append((table, index))
            issues.append(f"{table}.{index} index missing")
    
    print("\n=== Проверка типов колонок ===")
    
    # Проверка BIGINT колонок
    bigint_columns = [
        ('players', 'user_id'),
        ('caught_fish', 'user_id'),
        ('player_rods', 'user_id'),
        ('player_baits', 'user_id'),
        ('player_nets', 'user_id'),
    ]
    
    for table, column in bigint_columns:
        cursor.execute("""
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_schema = 'public' 
            AND table_name = %s 
            AND column_name = %s
        """, (table, column))
        
        row = cursor.fetchone()
        if row and row[0] == 'bigint':
            print(f"✓ {table}.{column} имеет тип BIGINT")
            fixes.append(f"{table}.{column} is BIGINT")
        elif row:
            print(f"✗ {table}.{column} имеет тип {row[0]} (ожидается BIGINT)")
            issues.append(f"{table}.{column} is {row[0]}, not BIGINT")
        else:
            print(f"✗ {table}.{column} не найдена")
            issues.append(f"{table}.{column} not found")
    
    print("\n=== Проверка производительности запросов ===")
    
    # Тестовый запрос для проверки использования индексов
    test_user_id = 793216884
    
    cursor.execute("""
        EXPLAIN (FORMAT JSON) 
        SELECT cf.fish_name, COUNT(cf.id), SUM(cf.weight)
        FROM caught_fish cf
        WHERE cf.user_id = %s AND cf.sold = 0
        GROUP BY cf.fish_name
    """, (test_user_id,))
    
    plan = cursor.fetchone()[0][0]
    uses_index = False
    
    def check_plan(node):
        nonlocal uses_index
        if 'Index Scan' in node.get('Node Type', ''):
            uses_index = True
        if 'Plans' in node:
            for child in node['Plans']:
                check_plan(child)
    
    check_plan(plan['Plan'])
    
    if uses_index:
        print("✓ Запрос к caught_fish использует индекс")
        fixes.append("caught_fish query uses index")
    else:
        print("✗ Запрос к caught_fish НЕ использует индекс (может быть медленным)")
        issues.append("caught_fish query doesn't use index")
    
    print("\n=== Проверка статистики таблиц ===")
    
    # Проверка последнего ANALYZE
    cursor.execute("""
        SELECT 
            schemaname,
            tablename,
            last_analyze,
            last_autoanalyze
        FROM pg_stat_user_tables
        WHERE schemaname = 'public'
        AND tablename IN ('caught_fish', 'players', 'fish_sales_history')
        ORDER BY tablename
    """)
    
    for schema, table, last_analyze, last_autoanalyze in cursor.fetchall():
        if last_analyze or last_autoanalyze:
            print(f"✓ {table} имеет статистику (последний ANALYZE: {last_analyze or last_autoanalyze})")
            fixes.append(f"{table} has statistics")
        else:
            print(f"⚠ {table} не имеет статистики (рекомендуется ANALYZE)")
            issues.append(f"{table} needs ANALYZE")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*60)
    print("ИТОГИ ПРОВЕРКИ")
    print("="*60)
    print(f"✓ Исправлено: {len(fixes)}")
    print(f"✗ Проблем: {len(issues)}")
    
    if issues:
        print("\nОбнаруженные проблемы:")
        for issue in issues:
            print(f"  - {issue}")
        
        if missing_indexes:
            print("\nДля создания отсутствующих индексов выполните:")
            print("  python scripts/optimize_postgres.py")
            print("  или")
            print("  psql -U your_user -d your_database -f scripts/add_performance_indexes.sql")
        
        return 1
    else:
        print("\n✓ Все проверки пройдены успешно!")
        print("\nРекомендации:")
        print("  1. Регулярно запускайте: python scripts/optimize_postgres.py")
        print("  2. Мониторьте медленные запросы через pg_stat_statements")
        print("  3. Настройте автоматический VACUUM в postgresql.conf")
        return 0


if __name__ == '__main__':
    try:
        sys.exit(check_database())
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ОШИБКА: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
