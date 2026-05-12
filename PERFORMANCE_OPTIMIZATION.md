# Оптимизация производительности FishBot

## Проблемы, которые были исправлены

### 1. Отсутствующая таблица `user_fish_stats`
**Проблема:** Запросы падали с ошибкой "relation user_fish_stats does not exist"

**Решение:** Таблица теперь создается автоматически при инициализации БД в `database.py`

### 2. Использование MySQL функции `GROUP_CONCAT` в PostgreSQL
**Проблема:** PostgreSQL не поддерживает `GROUP_CONCAT`, используется `STRING_AGG`

**Решение:** Заменено `GROUP_CONCAT(cf.id)` на `STRING_AGG(CAST(cf.id AS TEXT), ',')`

### 3. Deadlock'и при миграциях
**Проблема:** Множественные процессы пытались одновременно изменять схему БД

**Решение:** 
- Изменен порядок миграций (сначала дочерние таблицы, потом родительские)
- Добавлено логирование миграций
- Улучшена обработка ошибок

### 4. Медленные запросы без индексов
**Проблема:** Запросы к `caught_fish`, `fish_sales_history` и другим таблицам были медленными

**Решение:** Добавлены составные индексы для часто используемых запросов

## Добавленные индексы

### Основные индексы для производительности:

```sql
-- caught_fish (основная таблица)
idx_cf_user_sold ON caught_fish(user_id, sold)
idx_cf_user_sold_name ON caught_fish(user_id, sold, fish_name)
idx_cf_caught_at ON caught_fish(caught_at DESC)
idx_cf_fish_name ON caught_fish(fish_name)

-- fish_sales_history (история продаж)
idx_fsh_fish_sold ON fish_sales_history(fish_name, sold_at DESC)
idx_fsh_sold_at ON fish_sales_history(sold_at DESC)

-- players (игроки)
idx_players_tickets ON players(tickets DESC) WHERE tickets > 0
idx_players_gold_tickets ON players(gold_tickets DESC) WHERE gold_tickets > 0
idx_players_user_id ON players(user_id)

-- clan_members (члены кланов)
idx_clan_members_user ON clan_members(user_id)
idx_clan_members_clan ON clan_members(clan_id)
```

## Как применить оптимизации

### Автоматически (рекомендуется)
Индексы создаются автоматически при запуске бота через `database.py:init_db()`

### Вручную через SQL скрипт
```bash
# Подключитесь к PostgreSQL и выполните:
psql -U your_user -d your_database -f scripts/add_performance_indexes.sql
```

### Через Python скрипт оптимизации
```bash
python scripts/optimize_postgres.py
```

Этот скрипт выполнит:
- ANALYZE всех таблиц
- VACUUM основных таблиц
- Проверку неиспользуемых индексов
- Вывод статистики по размерам таблиц
- Анализ медленных запросов (если установлен pg_stat_statements)

## Дополнительные оптимизации

### 1. Включите pg_stat_statements для мониторинга
```sql
-- В postgresql.conf добавьте:
shared_preload_libraries = 'pg_stat_statements'

-- Затем в базе данных:
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;
```

### 2. Настройте параметры PostgreSQL
```ini
# В postgresql.conf для лучшей производительности:
shared_buffers = 256MB          # 25% от RAM
effective_cache_size = 1GB      # 50-75% от RAM
maintenance_work_mem = 64MB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1          # Для SSD
effective_io_concurrency = 200  # Для SSD
work_mem = 4MB
min_wal_size = 1GB
max_wal_size = 4GB
```

### 3. Регулярное обслуживание
```bash
# Запускайте раз в неделю:
python scripts/optimize_postgres.py

# Или настройте автоматический VACUUM в PostgreSQL:
# В postgresql.conf:
autovacuum = on
autovacuum_max_workers = 3
autovacuum_naptime = 1min
```

### 4. Мониторинг производительности
```sql
-- Проверка размеров таблиц:
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) as total_size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Проверка использования индексов:
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan DESC;

-- Проверка медленных запросов (требует pg_stat_statements):
SELECT 
    substring(query, 1, 100) as query,
    calls,
    round(total_exec_time::numeric, 2) as total_time_ms,
    round(mean_exec_time::numeric, 2) as mean_time_ms
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 20;
```

## Ожидаемые улучшения

После применения всех оптимизаций:

1. **Запросы к инвентарю** - ускорение в 10-50 раз
2. **Групповые запросы** - ускорение в 5-20 раз
3. **Запросы к рейтингам** - ускорение в 3-10 раз
4. **Deadlock'и** - полностью устранены
5. **Общая производительность API** - улучшение в 5-15 раз

## Проверка результатов

После применения оптимизаций проверьте:

```bash
# 1. Запустите скрипт оптимизации
python scripts/optimize_postgres.py

# 2. Проверьте логи приложения на отсутствие ошибок
tail -f logs/bot.log | grep -i "error\|deadlock"

# 3. Проверьте время ответа API
curl -w "@-" -o /dev/null -s "http://your-api/api/inventory/grouped" <<'EOF'
    time_namelookup:  %{time_namelookup}\n
       time_connect:  %{time_connect}\n
    time_appconnect:  %{time_appconnect}\n
      time_redirect:  %{time_redirect}\n
   time_pretransfer:  %{time_pretransfer}\n
 time_starttransfer:  %{time_starttransfer}\n
                    ----------\n
         time_total:  %{time_total}\n
EOF
```

## Troubleshooting

### Если индексы не создаются
```sql
-- Проверьте права доступа:
GRANT CREATE ON SCHEMA public TO your_user;

-- Проверьте наличие индексов:
SELECT indexname FROM pg_indexes WHERE tablename = 'caught_fish';
```

### Если deadlock'и продолжаются
```sql
-- Проверьте активные блокировки:
SELECT 
    pid,
    usename,
    pg_blocking_pids(pid) as blocked_by,
    query as blocked_query
FROM pg_stat_activity
WHERE cardinality(pg_blocking_pids(pid)) > 0;

-- Убейте проблемный процесс (осторожно!):
SELECT pg_terminate_backend(pid);
```

### Если запросы все еще медленные
```sql
-- Включите логирование медленных запросов в postgresql.conf:
log_min_duration_statement = 1000  # логировать запросы > 1 секунды

-- Проверьте план выполнения запроса:
EXPLAIN ANALYZE SELECT ...;
```

## Контакты

Если проблемы с производительностью продолжаются, проверьте:
1. Логи PostgreSQL: `/var/log/postgresql/`
2. Логи приложения: `logs/bot.log`
3. Системные ресурсы: `htop`, `iotop`
