import os
import json
import logging
import random
import secrets
import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from config import DB_PATH

# Optional Postgres support
try:
    import psycopg2
except Exception:
    psycopg2 = None

class PostgresConnWrapper:
    """A thin wrapper exposing a sqlite-like connection API for psycopg2.
    It provides execute(), cursor(), commit(), and context-manager support.
    """
    def __init__(self, dsn_or_conn):
        if not psycopg2:
            raise RuntimeError('psycopg2 is required for Postgres support')
        # accept full DATABASE_URL or components, or an existing raw connection
        if isinstance(dsn_or_conn, str):
            self._conn = psycopg2.connect(dsn_or_conn)
        else:
            self._conn = dsn_or_conn

    def _translate_sql(self, sql: str) -> str:
        s = sql
        # normalize whitespace for pattern matching
        import re
        # Replace SQLite AUTOINCREMENT with Postgres serial primary key
        s = re.sub(r"INTEGER\s+PRIMARY\s+KEY\s+AUTOINCREMENT", 'SERIAL PRIMARY KEY', s, flags=re.IGNORECASE)
        # Also handle bare AUTOINCREMENT token
        s = re.sub(r"AUTOINCREMENT", '', s, flags=re.IGNORECASE)
        # Convert empty double-quoted string literals ("") to PostgreSQL single-quoted ('').
        # SQLite allows "" as an empty string; Postgres treats "" as an invalid zero-length identifier.
        s = s.replace('""', "''")
        # Convert sqlite '?' placeholders to psycopg2 '%s'
        s = s.replace('?', '%s')
        # Replace sqlite datetime(...) with inner expression (Postgres uses native timestamp types)
        s = re.sub(r"datetime\s*\(([^)]+)\)", r"\1", s, flags=re.IGNORECASE)
        # remove sqlite-specific PRAGMA statements
        if s.strip().upper().startswith('PRAGMA'):
            return ''
        # translate INSERT OR IGNORE -> INSERT ... ON CONFLICT DO NOTHING
        if 'INSERT OR IGNORE' in s.upper():
            # simple replacement: remove OR IGNORE and append ON CONFLICT DO NOTHING
            # append only if not already present
            s = s.replace('INSERT OR IGNORE', 'INSERT')
            if 'ON CONFLICT' not in s.upper():
                s = s.rstrip().rstrip(';') + ' ON CONFLICT DO NOTHING;'

        # translate INSERT OR REPLACE for common tables to Postgres upsert
        # Use a robust parser for matching parentheses instead of a fragile regex,
        # because VALUES(...) can contain nested parentheses (e.g. COALESCE, SELECT).
        try:
            import re
            m = re.search(r"INSERT\s+OR\s+REPLACE\s+INTO\s+(\w+)", s, re.IGNORECASE)
            if m:
                table = m.group(1)
                # find the first '(' after the table name for columns
                start_cols = s.find('(', m.end())
                if start_cols != -1:
                    # find matching ')' for cols
                    depth = 0
                    end_cols = None
                    for idx in range(start_cols, len(s)):
                        ch = s[idx]
                        if ch == '(':
                            depth += 1
                        elif ch == ')':
                            depth -= 1
                            if depth == 0:
                                end_cols = idx
                                break
                    if end_cols:
                        cols_text = s[start_cols+1:end_cols]
                        cols = [c.strip() for c in cols_text.split(',')]
                        # Find VALUES keyword after end_cols
                        vals_kw = re.search(r"VALUES\s*\(", s[end_cols:], re.IGNORECASE)
                        if vals_kw:
                            start_vals = end_cols + vals_kw.start() + s[end_cols+vals_kw.start():].find('(')
                            # find matching ')' for vals, accounting for nesting
                            depth = 0
                            end_vals = None
                            for idx in range(start_vals, len(s)):
                                ch = s[idx]
                                if ch == '(':
                                    depth += 1
                                elif ch == ')':
                                    depth -= 1
                                    if depth == 0:
                                        end_vals = idx
                                        break
                            if end_vals:
                                vals = s[start_vals+1:end_vals]
                                # mapping of tables -> conflict target
                                conflict_map = {
                                    'baits': 'name',
                                    'fish': 'name',
                                    'player_baits': 'user_id, bait_name',
                                    'player_nets': 'user_id, net_name',
                                    'player_rods': 'user_id, rod_name',
                                    'chat_configs': 'chat_id',
                                    'user_ref_links': 'user_id',
                                    'system_flags': 'key',
                                }
                                conflict_cols = conflict_map.get(table.lower())
                                if conflict_cols:
                                    updates = ', '.join([f"{col} = EXCLUDED.{col}" for col in cols if col])
                                    s = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({vals}) ON CONFLICT ({conflict_cols}) DO UPDATE SET {updates};"
        except Exception:
            # fallback to original behavior on any parse error
            pass
        # psycopg2 uses Python %-format-style param interpolation; stray '%' in SQL
        # (e.g. LIKE '%Все%') will be treated as format specifiers and cause errors.
        # Preserve '%s' placeholders, escape other '%' by doubling them.
        if '%s' in s:
            s = s.replace('%s', '__PG_PLACEHOLDER__')
            s = s.replace('%', '%%')
            s = s.replace('__PG_PLACEHOLDER__', '%s')
        else:
            s = s.replace('%', '%%')

        return s

    def execute(self, sql: str, params=None):
        sql = sql or ''
        # Short-circuit sqlite-specific sqlite_master queries which don't exist in Postgres
        try:
            if 'sqlite_master' in sql.lower():
                return FakeCursor([])
        except Exception:
            pass
        # Handle PRAGMA table_info(...) emulation
        if sql.strip().upper().startswith('PRAGMA TABLE_INFO'):
            # extract table name
            import re
            m = re.search(r"PRAGMA\s+table_info\(([^)]+)\)", sql, re.IGNORECASE)
            table = m.group(1).strip(' \"') if m else None
            cur = self._conn.cursor()
            if table:
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name=%s ORDER BY ordinal_position", (table,))
                cols = cur.fetchall()
                # emulate sqlite pragma rows: (cid, name, type, notnull, dflt_value, pk)
                rows = []
                for i, (colname,) in enumerate(cols):
                    rows.append((i, colname, None, None, None, 0))
                return FakeCursor(rows)
            return FakeCursor([])

        out_sql = self._translate_sql(sql)
        if not out_sql:
            return FakeCursor([])

        cur = self._conn.cursor()
        # psycopg2 expects a sequence/tuple for parameters
        try:
            if params is not None:
                # convert list->tuple for psycopg2
                if isinstance(params, list):
                    params = tuple(params)
                try:
                    logger.debug("Postgres executing SQL: %s PARAMS: %s", out_sql, params)
                    cur.execute(out_sql, params)
                except Exception:
                    logger.exception("DB execute failed. SQL: %s PARAMS: %s", out_sql, params)
                    raise
            else:
                try:
                    logger.debug("Postgres executing SQL: %s (no params)", out_sql)
                    cur.execute(out_sql)
                except Exception:
                    logger.exception("DB execute failed. SQL: %s", out_sql)
                    raise
        except Exception:
            # re-raise so caller sees DB errors
            raise
        return cur

    def cursor(self):
        parent = self

        class _CursorWrapper:
            def __init__(self):
                self._last = None

            @property
            def rowcount(self):
                try:
                    return getattr(self._last, 'rowcount', -1)
                except Exception:
                    return -1

            @property
            def lastrowid(self):
                try:
                    return getattr(self._last, 'lastrowid', None)
                except Exception:
                    return None

            def execute(self, sql, params=None):
                # Delegate to the parent.execute so translations and PRAGMA emulation apply
                self._last = parent.execute(sql, params)
                return self._last

            def executemany(self, sql, seq_of_params):
                # executemany isn't used heavily; emulate by executing in a loop so translations apply
                last = None
                for params in seq_of_params:
                    last = parent.execute(sql, params)
                self._last = last
                return last

            def fetchall(self):
                try:
                    return self._last.fetchall() if self._last is not None else []
                except Exception:
                    return []

            def fetchone(self):
                try:
                    return self._last.fetchone() if self._last is not None else None
                except Exception:
                    return None

            @property
            def description(self):
                try:
                    return getattr(self._last, 'description', None)
                except Exception:
                    return None

            def __iter__(self):
                return iter(self._last) if self._last is not None else iter(())

            def close(self):
                try:
                    if hasattr(self._last, 'close'):
                        self._last.close()
                except Exception:
                    pass

        return _CursorWrapper()

    def commit(self):
        self._conn.commit()

    def rollback(self):
        self._conn.rollback()

    def close(self):
        try:
            self._conn.close()
        except Exception:
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        try:
            if exc_type:
                self._conn.rollback()
            else:
                self._conn.commit()
        except Exception:
            pass
        try:
            self._conn.close()
        except Exception:
            pass
        return False


class FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)
    
    @property
    def rowcount(self):
        try:
            return len(self._rows)
        except Exception:
            return -1

    @property
    def description(self):
        return None


logger = logging.getLogger(__name__)


def ensure_serial_pk(conn, table: str, id_col: str = 'id'):
    """Ensure the integer primary key column has a Postgres sequence DEFAULT.
    Safe to call multiple times; will create sequence if missing and set it to max(id).
    """
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT column_default FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
            (table, id_col),
        )
        row = cur.fetchone()
        if not row:
            return
        col_default = row[0]
        if col_default:
            return
        seq_name = f"{table}_{id_col}_seq"
        cur.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
        cur.execute(f"ALTER SEQUENCE {seq_name} OWNED BY {table}.{id_col}")
        cur.execute(f"ALTER TABLE {table} ALTER COLUMN {id_col} SET DEFAULT nextval('{seq_name}')")
        cur.execute(f"SELECT COALESCE(MAX({id_col}), 0) FROM {table}")
        max_id = cur.fetchone()[0] or 0
        if max_id <= 0:
            cur.execute("SELECT setval(%s, %s, false)", (seq_name, 1))
        else:
            cur.execute("SELECT setval(%s, %s, true)", (seq_name, max_id))
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    except Exception:
        logger.exception('ensure_serial_pk failed for %s.%s', table, id_col)
        try:
            conn.rollback()
        except Exception:
            pass


def ensure_all_serial_pks(conn):
    """Ensure all integer primary-key columns have a Postgres sequence DEFAULT.
    Finds PK columns of integer types without a nextval() default and installs
    a sequence + DEFAULT for them. Safe to call multiple times.
    """
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT c.table_name, c.column_name
            FROM information_schema.columns c
            JOIN information_schema.table_constraints tc
              ON c.table_schema = tc.table_schema AND c.table_name = tc.table_name
            JOIN information_schema.key_column_usage k
              ON k.table_schema = c.table_schema AND k.table_name = c.table_name AND k.column_name = c.column_name AND k.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND c.table_schema = 'public'
                            AND c.data_type IN ('integer','bigint','smallint')
                            AND (c.column_default IS NULL OR c.column_default NOT LIKE 'nextval(%')
            """
        )
        rows = cur.fetchall()
        for table, col in rows:
            try:
                ensure_serial_pk(conn, table, col)
            except Exception:
                logger.exception('failed to ensure serial for %s.%s', table, col)
        try:
            conn.commit()
        except Exception:
            try:
                conn.rollback()
            except Exception:
                pass
    except Exception:
        logger.exception('ensure_all_serial_pks failed')
        try:
            conn.rollback()
        except Exception:
            pass

BAMBOO_ROD = "Бамбуковая удочка"
TEMP_ROD_RANGES = {
    "Углепластиковая удочка": (30, 70),
    "Карбоновая удочка": (50, 100),
    "Золотая удочка": (90, 150),
    "Удачливая удочка": (140, 160),
}

LEVEL_XP_REQUIREMENTS = [
    100, 250, 700, 1450, 2500, 3850, 5500, 7450, 9700, 12250,
    15100, 18250, 21700, 25450, 29500, 33850, 38500, 43450, 48700, 54250,
    60100, 66250, 72700, 79450, 86500, 93850, 101500, 109450, 117700, 126250,
    135100, 144250, 153700, 163450, 173500, 183850, 194500, 205450, 216700, 228250,
    240100, 252250, 264700, 277450, 290500, 303850, 317500, 331450, 345700, 360250,
    375100, 390250, 405700, 421450, 437500, 453850, 470500, 487450, 504700, 522250,
    540100, 558250, 576700, 595450, 614500, 633850, 653500, 673450, 693700, 714250,
    735100, 756250, 777700, 799450, 821500, 843850, 866500, 889450, 912700, 936250,
    960100, 984250, 1008700, 1033450, 1058500, 1083850, 1109500, 1135450, 1161700, 1188250,
    1215100, 1242250, 1269700, 1297450, 1325500, 1353850, 1382500, 1411450, 1440700, 1470250,
]

LEVEL_XP_THRESHOLDS = [0]
for requirement in LEVEL_XP_REQUIREMENTS:
    LEVEL_XP_THRESHOLDS.append(LEVEL_XP_THRESHOLDS[-1] + requirement)

MAX_LEVEL = len(LEVEL_XP_REQUIREMENTS)

BASE_XP_BY_RARITY = {
    "Обычная": 5,
    "Редкая": 20,
    "Легендарная": 100,
    "Мифическая": 50,
}

RARITY_XP_MULTIPLIERS = {
    "Обычная": 1.0,
    "Редкая": 1.1,
    "Легендарная": 1.2,
    "Мифическая": 1.15,
}

LIVE_BAIT_FISH_NAMES = ("Плотва", "Верховка")
LIVE_BAIT_NAME = "Живец"

CLAN_MEMBER_LIMITS = {
    1: 5,
    2: 8,
    3: 12,
    4: 16,
    5: 20,
}

CLAN_UPGRADE_REQUIREMENTS = {
    2: {"Коряга": 8, "Консервная банка": 12},
    3: {"Ботинок": 12, "Пластиковая бутылка": 20, "Веревка": 10},
    4: {"Поломанная удочка": 20, "Рыболовная сетка": 16, "Ржавый крючок": 24},
    5: {"Старая шина": 16, "Кусок трубы": 12, "Старый якорь": 8, "Деревянная доска": 20},
}

class Database:
    def get_system_flag(self, key: str) -> Optional[str]:
        """Получить значение системного флага по ключу."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_flags WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_system_flag(self, key: str, value: str):
        """Установить значение системного флага."""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Теперь INSERT OR REPLACE корректно транслируется в ON CONFLICT для Postgres
            cursor.execute("INSERT OR REPLACE INTO system_flags (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    def get_system_flag(self, key: str) -> Optional[str]:
        """Получить значение системного флага по ключу."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_flags WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row[0] if row else None

    def set_system_flag(self, key: str, value: str):
        """Установить значение системного флага."""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Используем INSERT OR REPLACE (эмулируется в PostgresWrapper)
            cursor.execute("INSERT OR REPLACE INTO system_flags (key, value) VALUES (?, ?)", (key, value))
            conn.commit()

    @staticmethod
    def _normalize_item_name(value: Any) -> str:
        return str(value or '').strip().casefold()

    def get_clan_member_limit(self, level: int) -> int:
        try:
            lvl = max(1, int(level or 1))
        except Exception:
            lvl = 1
        if lvl in CLAN_MEMBER_LIMITS:
            return int(CLAN_MEMBER_LIMITS[lvl])
        return int(CLAN_MEMBER_LIMITS[max(CLAN_MEMBER_LIMITS.keys())])

    def get_active_ecological_disaster(self, location: str) -> Optional[Dict[str, Any]]:
        """Вернуть активную эко-катастрофу на локации, если она есть."""
        loc = str(location or '').strip()
        if not loc:
            return None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE is_active = 1 AND ends_at <= CURRENT_TIMESTAMP
                '''
            )
            cursor.execute(
                '''
                SELECT id, location, reward_type, reward_multiplier, started_at, ends_at, is_active
                FROM ecological_disasters
                WHERE LOWER(TRIM(location)) = LOWER(TRIM(?))
                  AND is_active = 1
                  AND ends_at > CURRENT_TIMESTAMP
                ORDER BY ends_at DESC
                LIMIT 1
                ''',
                (loc,),
            )
            row = cursor.fetchone()
            conn.commit()

        if not row:
            return None

        return {
            'id': int(row[0]),
            'location': row[1],
            'reward_type': str(row[2] or 'xp'),
            'reward_multiplier': int(row[3] or 5),
            'started_at': row[4],
            'ends_at': row[5],
            'is_active': int(row[6] or 0),
        }

    def start_ecological_disaster(
        self,
        location: str,
        reward_type: str = 'xp',
        duration_minutes: int = 60,
        reward_multiplier: int = 5,
    ) -> Optional[Dict[str, Any]]:
        """Запустить эко-катастрофу на локации."""
        loc = str(location or '').strip()
        if not loc:
            return None

        safe_reward_type = str(reward_type or 'xp').strip().lower()
        if safe_reward_type not in ('xp', 'coins'):
            safe_reward_type = 'xp'

        safe_minutes = max(1, int(duration_minutes or 60))
        safe_multiplier = max(2, int(reward_multiplier or 5))
        now_dt = datetime.utcnow()
        ends_dt = now_dt + timedelta(minutes=safe_minutes)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE LOWER(TRIM(location)) = LOWER(TRIM(?))
                  AND is_active = 1
                ''',
                (loc,),
            )
            cursor.execute(
                '''
                INSERT INTO ecological_disasters
                    (location, reward_type, reward_multiplier, started_at, ends_at, is_active)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP, ?, 1)
                RETURNING id, location, reward_type, reward_multiplier, started_at, ends_at, is_active
                ''',
                (loc, safe_reward_type, safe_multiplier, ends_dt.isoformat()),
            )
            row = cursor.fetchone()
            conn.commit()

        if not row:
            return None

        return {
            'id': int(row[0]),
            'location': row[1],
            'reward_type': str(row[2] or 'xp'),
            'reward_multiplier': int(row[3] or safe_multiplier),
            'started_at': row[4],
            'ends_at': row[5],
            'is_active': int(row[6] or 0),
        }

    def stop_ecological_disaster(self, location: str) -> bool:
        loc = str(location or '').strip()
        if not loc:
            return False
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE LOWER(TRIM(location)) = LOWER(TRIM(?))
                  AND is_active = 1
                ''',
                (loc,),
            )
            changed = int(cursor.rowcount or 0)
            conn.commit()
        return changed > 0

    def maybe_start_ecological_disaster(self, location: str) -> Optional[Dict[str, Any]]:
        """С небольшим шансом запускает катастрофу (по умолчанию только в городском пруду)."""
        loc = str(location or '').strip()
        if self._normalize_item_name(loc) != self._normalize_item_name('Городской пруд'):
            return None
        if self.get_active_ecological_disaster(loc):
            return None

        # Примерно 1.5% шанс на запуск за попытку заброса.
        if random.random() > 0.015:
            return None

        reward_type = 'xp' if random.random() < 0.5 else 'coins'
        return self.start_ecological_disaster(
            location=loc,
            reward_type=reward_type,
            duration_minutes=60,
            reward_multiplier=5,
        )

    def set_daily_market_offer(
        self,
        fish_name: str,
        multiplier: float = 2.0,
        target_weight: float = 50.0,
        market_day: Optional[str] = None,
    ) -> bool:
        """Установить рыбу дня на рынке."""
        fish_value = str(fish_name or '').strip()
        if not fish_value:
            return False

        day_key = str(market_day or datetime.utcnow().date().isoformat())
        safe_multiplier = max(1.0, float(multiplier or 2.0))
        safe_target_weight = max(1.0, float(target_weight or 50.0))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO daily_fish_market (market_day, fish_name, multiplier, target_weight, sold_weight, created_at)
                VALUES (?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
                ON CONFLICT (market_day)
                DO UPDATE SET
                    fish_name = EXCLUDED.fish_name,
                    multiplier = EXCLUDED.multiplier,
                    target_weight = EXCLUDED.target_weight,
                    sold_weight = 0,
                    created_at = CURRENT_TIMESTAMP
                ''',
                (day_key, fish_value, safe_multiplier, safe_target_weight),
            )
            conn.commit()
        return True

    def get_today_market_offer(self, day_key: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Получить текущую акцию рыбного рынка."""
        query_day = str(day_key or datetime.utcnow().date().isoformat())
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, market_day, fish_name, multiplier, target_weight, sold_weight, created_at
                FROM daily_fish_market
                WHERE market_day = ?
                LIMIT 1
                ''',
                (query_day,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        target_weight = float(row[4] or 0.0)
        sold_weight = float(row[5] or 0.0)
        remaining = max(0.0, target_weight - sold_weight)

        return {
            'id': int(row[0]),
            'market_day': str(row[1]),
            'fish_name': str(row[2] or ''),
            'multiplier': float(row[3] or 1.0),
            'target_weight': target_weight,
            'sold_weight': sold_weight,
            'remaining_weight': remaining,
            'active': remaining > 0.0,
            'created_at': row[6],
        }

    def get_fish_price_modifiers(self, fish_name: str) -> Dict[str, Any]:
        """Модификаторы цены: объем продаж за час, дефицит и рынок дня."""
        name_value = str(fish_name or '').strip()
        if not name_value:
            return {
                'sales_multiplier': 1.0,
                'scarcity_multiplier': 1.0,
                'market_multiplier': 1.0,
                'total_multiplier': 1.0,
                'sold_last_hour_weight': 0.0,
                'hours_since_last_sale': None,
                'market': None,
            }

        sold_last_hour_weight = 0.0
        hours_since_last_sale = None
        market_offer = self.get_today_market_offer()

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COALESCE(SUM(weight), 0)
                FROM fish_sales_history
                WHERE LOWER(TRIM(fish_name)) = LOWER(TRIM(?))
                  AND sold_at >= (CURRENT_TIMESTAMP - INTERVAL '1 hour')
                ''',
                (name_value,),
            )
            row = cursor.fetchone()
            sold_last_hour_weight = float((row[0] if row else 0.0) or 0.0)

            cursor.execute(
                '''
                SELECT sold_at
                FROM fish_sales_history
                WHERE LOWER(TRIM(fish_name)) = LOWER(TRIM(?))
                ORDER BY sold_at DESC
                LIMIT 1
                ''',
                (name_value,),
            )
            last_sale_row = cursor.fetchone()

        if last_sale_row and last_sale_row[0]:
            last_sale_dt = self._parse_utc_datetime(last_sale_row[0])
            if last_sale_dt is not None:
                now_utc = datetime.now(timezone.utc)
                hours_since_last_sale = max(0.0, (now_utc - last_sale_dt).total_seconds() / 3600.0)

        if sold_last_hour_weight >= 120.0:
            sales_multiplier = 0.75
        elif sold_last_hour_weight >= 70.0:
            sales_multiplier = 0.85
        elif sold_last_hour_weight >= 35.0:
            sales_multiplier = 0.93
        else:
            sales_multiplier = 1.0

        if hours_since_last_sale is None:
            scarcity_multiplier = 1.35
        elif hours_since_last_sale >= 12.0:
            scarcity_multiplier = 1.35
        elif hours_since_last_sale >= 6.0:
            scarcity_multiplier = 1.20
        elif hours_since_last_sale >= 3.0:
            scarcity_multiplier = 1.10
        else:
            scarcity_multiplier = 1.0

        market_multiplier = 1.0
        if market_offer and market_offer.get('active'):
            if self._normalize_item_name(market_offer.get('fish_name')) == self._normalize_item_name(name_value):
                market_multiplier = float(market_offer.get('multiplier') or 1.0)

        total_multiplier = sales_multiplier * scarcity_multiplier * market_multiplier
        total_multiplier = max(0.45, min(3.0, total_multiplier))

        return {
            'sales_multiplier': sales_multiplier,
            'scarcity_multiplier': scarcity_multiplier,
            'market_multiplier': market_multiplier,
            'total_multiplier': total_multiplier,
            'sold_last_hour_weight': sold_last_hour_weight,
            'hours_since_last_sale': hours_since_last_sale,
            'market': market_offer,
        }

    def get_clan_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT c.id, c.name, c.owner_user_id, c.level, c.created_at, cm.role
                FROM clan_members cm
                JOIN clans c ON c.id = cm.clan_id
                WHERE cm.user_id = ?
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()
        if not row:
            return None
        return {
            'id': int(row[0]),
            'name': str(row[1] or ''),
            'owner_user_id': int(row[2] or 0),
            'level': int(row[3] or 1),
            'created_at': row[4],
            'role': str(row[5] or 'member'),
        }

    def list_clan_members(self, clan_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT cm.user_id, cm.role, cm.joined_at, COALESCE(MAX(p.username), '') AS username
                FROM clan_members cm
                LEFT JOIN players p ON p.user_id = cm.user_id
                WHERE cm.clan_id = ?
                GROUP BY cm.user_id, cm.role, cm.joined_at
                ORDER BY cm.role DESC, cm.joined_at ASC
                ''',
                (int(clan_id),),
            )
            rows = cursor.fetchall() or []

        result: List[Dict[str, Any]] = []
        for row in rows:
            result.append(
                {
                    'user_id': int(row[0] or 0),
                    'role': str(row[1] or 'member'),
                    'joined_at': row[2],
                    'username': str(row[3] or '') or f"id{int(row[0] or 0)}",
                }
            )
        return result

    def get_clan_donations(self, clan_id: int) -> Dict[str, int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT item_name, quantity
                FROM clan_donations
                WHERE clan_id = ?
                ''',
                (int(clan_id),),
            )
            rows = cursor.fetchall() or []

        result: Dict[str, int] = {}
        for item_name, quantity in rows:
            result[str(item_name or '')] = int(quantity or 0)
        return result

    def get_clan_info(self, clan_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, name, owner_user_id, level, created_at
                FROM clans
                WHERE id = ?
                LIMIT 1
                ''',
                (int(clan_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None

            clan_level = int(row[3] or 1)
            cursor.execute('SELECT COUNT(*) FROM clan_members WHERE clan_id = ?', (int(clan_id),))
            member_count_row = cursor.fetchone()
            member_count = int(member_count_row[0] or 0) if member_count_row else 0

        return {
            'id': int(row[0]),
            'name': str(row[1] or ''),
            'owner_user_id': int(row[2] or 0),
            'level': clan_level,
            'created_at': row[4],
            'member_count': member_count,
            'max_members': self.get_clan_member_limit(clan_level),
            'donations': self.get_clan_donations(int(row[0])),
        }

    def create_clan(self, owner_user_id: int, name: str) -> Dict[str, Any]:
        clan_name = str(name or '').strip()
        if len(clan_name) < 3:
            return {'ok': False, 'reason': 'name_too_short'}

        if self.get_clan_by_user(owner_user_id):
            return {'ok': False, 'reason': 'already_in_clan'}

        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    '''
                    INSERT INTO clans (name, owner_user_id, level, created_at)
                    VALUES (?, ?, 1, CURRENT_TIMESTAMP)
                    RETURNING id, name, owner_user_id, level, created_at
                    ''',
                    (clan_name, int(owner_user_id)),
                )
                row = cursor.fetchone()
                if not row:
                    conn.rollback()
                    return {'ok': False, 'reason': 'insert_failed'}

                clan_id = int(row[0])
                cursor.execute(
                    '''
                    INSERT INTO clan_members (clan_id, user_id, role, joined_at)
                    VALUES (?, ?, 'leader', CURRENT_TIMESTAMP)
                    ''',
                    (clan_id, int(owner_user_id)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                return {'ok': False, 'reason': 'name_taken'}

        return {
            'ok': True,
            'clan': {
                'id': clan_id,
                'name': str(row[1] or ''),
                'owner_user_id': int(row[2] or 0),
                'level': int(row[3] or 1),
                'created_at': row[4],
                'member_count': 1,
                'max_members': self.get_clan_member_limit(1),
            },
        }

    def join_clan(self, user_id: int, clan_name: str) -> Dict[str, Any]:
        if self.get_clan_by_user(user_id):
            return {'ok': False, 'reason': 'already_in_clan'}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, level
                FROM clans
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                LIMIT 1
                ''',
                (str(clan_name or '').strip(),),
            )
            clan_row = cursor.fetchone()
            if not clan_row:
                return {'ok': False, 'reason': 'clan_not_found'}

            clan_id = int(clan_row[0])
            level = int(clan_row[1] or 1)
            max_members = self.get_clan_member_limit(level)

            cursor.execute('SELECT COUNT(*) FROM clan_members WHERE clan_id = ?', (clan_id,))
            count_row = cursor.fetchone()
            member_count = int(count_row[0] or 0) if count_row else 0
            if member_count >= max_members:
                return {'ok': False, 'reason': 'clan_full', 'max_members': max_members}

            try:
                cursor.execute(
                    '''
                    INSERT INTO clan_members (clan_id, user_id, role, joined_at)
                    VALUES (?, ?, 'member', CURRENT_TIMESTAMP)
                    ''',
                    (clan_id, int(user_id)),
                )
                conn.commit()
            except Exception:
                conn.rollback()
                return {'ok': False, 'reason': 'already_in_clan'}

        return {'ok': True, 'clan_id': clan_id}

    def get_clan_upgrade_requirements(self, next_level: int) -> Dict[str, int]:
        return {
            item_name: int(qty)
            for item_name, qty in (CLAN_UPGRADE_REQUIREMENTS.get(int(next_level), {}) or {}).items()
        }

    def upgrade_clan(self, user_id: int) -> Dict[str, Any]:
        clan = self.get_clan_by_user(user_id)
        if not clan:
            return {'ok': False, 'reason': 'not_in_clan'}
        if str(clan.get('role') or 'member') != 'leader':
            return {'ok': False, 'reason': 'not_leader'}

        current_level = int(clan.get('level') or 1)
        next_level = current_level + 1
        requirements = self.get_clan_upgrade_requirements(next_level)
        if not requirements:
            return {'ok': False, 'reason': 'max_level'}

        donations = self.get_clan_donations(int(clan['id']))
        missing: Dict[str, int] = {}
        for item_name, required_qty in requirements.items():
            available_qty = int(donations.get(item_name, 0) or 0)
            if available_qty < required_qty:
                missing[item_name] = required_qty - available_qty
        if missing:
            return {'ok': False, 'reason': 'not_enough_donations', 'missing': missing, 'required': requirements}

        with self._connect() as conn:
            cursor = conn.cursor()
            for item_name, required_qty in requirements.items():
                cursor.execute(
                    '''
                    UPDATE clan_donations
                    SET quantity = GREATEST(0, quantity - ?), updated_at = CURRENT_TIMESTAMP
                    WHERE clan_id = ? AND item_name = ?
                    ''',
                    (int(required_qty), int(clan['id']), item_name),
                )

            cursor.execute(
                '''
                UPDATE clans
                SET level = ?
                WHERE id = ?
                ''',
                (next_level, int(clan['id'])),
            )
            conn.commit()

        return {
            'ok': True,
            'new_level': next_level,
            'max_members': self.get_clan_member_limit(next_level),
            'spent': requirements,
        }

    def get_location_fish_leaderboard_weight(self, location_name: str, fish_name: str, starts_at: datetime, ends_at: datetime, limit: int = 10) -> list:
        """Топ по суммарному весу определённой рыбы на локации."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    cf.user_id,
                    COALESCE(SUM(cf.weight), 0) AS total_weight,
                    COUNT(cf.id) AS total_fish
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.location = ?
                  AND LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(?))
                  AND cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
                GROUP BY cf.user_id
                ORDER BY total_weight DESC, total_fish DESC
                LIMIT ?
                ''',
                (location_name, fish_name, starts_at, ends_at, max(1, int(limit or 10)))
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_location_fish_leaderboard_count(self, location_name: str, fish_name: str, starts_at: datetime, ends_at: datetime, limit: int = 10) -> list:
        """Топ по количеству определённой рыбы на локации."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    cf.user_id,
                    COUNT(cf.id) AS total_fish,
                    COALESCE(SUM(cf.weight), 0) AS total_weight
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.location = ?
                  AND LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(?))
                  AND cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
                GROUP BY cf.user_id
                ORDER BY total_fish DESC, total_weight DESC
                LIMIT ?
                ''',
                (location_name, fish_name, starts_at, ends_at, max(1, int(limit or 10)))
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]
    def skip_boat_cooldown(self, user_id: int, price: int = 20) -> bool:
        """Обойти КД лодки за звёзды. Списывает звёзды, сбрасывает КД, активирует лодку."""
        self._ensure_boat_tables()
        player = self.get_player(user_id, 0)
        stars = int(player.get('stars', 0)) if player else 0
        if stars < price:
            return False
        self.increment_chat_stars(0, -price)
        with self._connect() as conn:
            cursor = conn.cursor()
            # Сбрасываем КД для любой лодки пользователя
            cursor.execute('''
                UPDATE boats SET cooldown_until = NULL, is_active = 1 WHERE user_id = ?
            ''', (user_id,))
            # Сбрасываем и КД по времени последнего возврата (новая логика на players)
            cursor.execute(
                'UPDATE players SET last_boat_return_time = NULL WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)',
                (user_id,)
            )
            if getattr(cursor, 'rowcount', 0) == 0:
                cursor.execute('UPDATE players SET last_boat_return_time = NULL WHERE user_id = ?', (user_id,))
            conn.commit()
        return True

    def cure_seasick(self, user_id: int, price: int = 10) -> bool:
        """Вылечить морскую болезнь за звёзды. Списывает звёзды, удаляет эффект."""
        self._ensure_user_effects_table()
        if not self.is_user_seasick(user_id):
            return False
        player = self.get_player(user_id, 0)
        stars = int(player.get('stars', 0)) if player else 0
        if stars < price:
            return False
        self.increment_chat_stars(0, -price)
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM user_effects WHERE user_id = ? AND effect_type = 'seasick'
            ''', (user_id,))
            conn.commit()
        return True

    def apply_seasick_event(self, user_id: int, duration_minutes: int = 18 * 60) -> bool:
        """Наложить морскую болезнь на пользователя после шторма."""
        self._ensure_user_effects_table()
        return self.apply_timed_effect(
            user_id,
            'seasick',
            duration_minutes=max(1, int(duration_minutes or 0)),
            replace_existing=True,
        )

    def return_boat_trip_and_split_catch(self, user_id: int) -> tuple:
        """Возврат лодки: делит улов между участниками, добавляет в caught_fish, возвращает (results, boat_id). Может вызвать любой участник лодки."""
        self._ensure_boat_tables()
        self._ensure_boat_catch_table()
        import logging
        logger = logging.getLogger(__name__)
        with self._connect() as conn:
            cursor = conn.cursor()
            # Найти активную лодку, где пользователь — участник
            cursor.execute('''
                SELECT b.id, b.user_id, b.type, b.capacity FROM boats b
                JOIN boat_members bm ON bm.boat_id = b.id
                WHERE bm.user_id = ? AND b.is_active = 1 LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            if not row:
                logger.warning(f"[boat] Не найдена активная лодка для пользователя {user_id} при возврате.")
                return [], None, 'not_found'
            boat_id = row[0]
            boat_owner_id = int(row[1]) if row[1] is not None else user_id
            boat_type = str(row[2] or "")
            try:
                boat_capacity = int(row[3]) if row[3] is not None else 1
            except (TypeError, ValueError):
                boat_capacity = 1

            def _mark_boat_return_time(owner_id: int):
                """Фиксирует время завершения плавания в профиле игрока."""
                from datetime import datetime, timezone
                returned_at = datetime.now(timezone.utc).isoformat()
                cursor.execute(
                    'UPDATE players SET last_boat_return_time = ? WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)',
                    (returned_at, owner_id),
                )
                if getattr(cursor, 'rowcount', 0) == 0:
                    cursor.execute(
                        'UPDATE players SET last_boat_return_time = ? WHERE user_id = ?',
                        (returned_at, owner_id),
                    )
                logger.info("[boat] last_boat_return_time updated: owner_id=%s returned_at=%s", owner_id, returned_at)

            # Предварительная проверка на крушение перед возвратом
            cursor.execute('SELECT current_weight, max_weight FROM boats WHERE id = ?', (boat_id,))
            bw_row = cursor.fetchone()
            if bw_row and float(bw_row[0]) > float(bw_row[1]):
                # Крушение!
                from datetime import datetime, timedelta, timezone
                cd_until = datetime.now(timezone.utc) + timedelta(hours=12)
                cursor.execute('DELETE FROM boat_members WHERE boat_id = ? AND is_owner = 0', (boat_id,))
                cursor.execute('DELETE FROM boat_catch WHERE boat_id = ?', (boat_id,))
                cursor.execute('''
                    UPDATE boats 
                    SET is_active = 0, current_weight = 0, durability = 0, cooldown_until = ? 
                    WHERE id = ?
                ''', (cd_until.isoformat(), boat_id))
                _mark_boat_return_time(boat_owner_id)
                conn.commit()
                logger.info(f"[boat] Крушение лодки {boat_id}, весь улов утерян.")
                return [], boat_id, 'sunk'
            # Получить участников
            cursor.execute('''
                SELECT user_id FROM boat_members WHERE boat_id = ?
            ''', (boat_id,))
            members = [r[0] for r in cursor.fetchall()]
            logger.info(f"[boat] Участники лодки {boat_id}: {members}")
            if not members:
                logger.warning(f"[boat] Нет участников в лодке {boat_id} при возврате.")
                return [], boat_id, 'no_members'
            # Получить улов
            cursor.execute('''
                SELECT fish_id, weight, chat_id, location, caught_at, item_name FROM boat_catch WHERE boat_id = ?
            ''', (boat_id,))
            catch = cursor.fetchall()
            logger.info(f"[boat] Улов лодки {boat_id}: {catch}")
            total_fish = len(catch)
            if total_fish == 0:
                # Просто завершить плавание
                from datetime import datetime, timedelta, timezone
                cd_until = datetime.now(timezone.utc) + timedelta(hours=12)
                cursor.execute('DELETE FROM boat_members WHERE boat_id = ? AND is_owner = 0', (boat_id,))
                cursor.execute('''
                    UPDATE boats 
                    SET is_active = 0, current_weight = 0, cooldown_until = ? 
                    WHERE id = ?
                ''', (cd_until.isoformat(), boat_id))
                _mark_boat_return_time(boat_owner_id)
                conn.commit()
                logger.info(f"[boat] Нет улова в лодке {boat_id} при возврате.")
                return [], boat_id, 'empty'

            # Бесплатная/одноместная лодка не делит улов: весь улов забирает владелец.
            if boat_type == 'free' or boat_capacity <= 1:
                distribution_members = [boat_owner_id]
                logger.info(
                    "[boat] Лодка %s (%s, capacity=%s): делёж отключён, весь улов владельцу %s",
                    boat_id,
                    boat_type,
                    boat_capacity,
                    boat_owner_id,
                )
            else:
                distribution_members = members

            per_user = total_fish // len(distribution_members)
            remainder = total_fish % len(distribution_members)
            remainder_receiver = user_id if user_id in distribution_members else distribution_members[0]
            # Получить имена
            usernames = {}
            for uid in distribution_members:
                player = self.get_player(uid, 0)
                usernames[uid] = player.get('username', f'id{uid}') if player else f'id{uid}'
            # Раздать рыбу
            idx = 0
            results = []
            assigned_count = 0
            inserted_count = 0
            skipped_count = 0
            for uid in distribution_members:
                # Весь остаток отдаём вызывающему (как было задумано ранее), без потери записей.
                count = per_user + (remainder if uid == remainder_receiver else 0)
                user_catch = catch[idx:idx+count]
                idx += count
                assigned_count += count
                total_weight = sum(float(item[1] or 0) for item in user_catch)
                if not user_catch:
                    logger.warning(f"[boat] Для пользователя {uid} не нашлось рыбы для распределения (user_catch пустой)")
                else:
                    logger.info(f"[boat] Рыба для пользователя {uid}: {user_catch}")
                # Добавить в caught_fish
                for fish_id, weight, item_chat_id, catch_location, catch_time, item_name in user_catch:
                    fish_name = None
                    length = 0.0

                    # Основной сценарий: fish_id указывает на рыбу из справочника.
                    if fish_id:
                        cursor.execute('SELECT name, min_length, max_length FROM fish WHERE id = ?', (fish_id,))
                        fish_row = cursor.fetchone()
                        if fish_row:
                            fish_name = fish_row[0]
                            min_len, max_len = fish_row[1], fish_row[2]
                            # Генерируем длину на основе диапазона, если он валиден.
                            if min_len is not None and max_len is not None and float(max_len) >= float(min_len):
                                length = round(random.uniform(float(min_len), float(max_len)), 1)

                    # Fallback для мусора/особых предметов, где fish_id может быть 0.
                    if not fish_name and item_name:
                        fish_name = str(item_name).strip()
                        length = 0.0
                        logger.info(
                            "[boat] Fallback insert by item_name: boat_id=%s user_id=%s fish_id=%s item_name=%s",
                            boat_id,
                            uid,
                            fish_id,
                            fish_name,
                        )

                    if not fish_name:
                        skipped_count += 1
                        logger.warning(
                            "[boat] Пропуск записи при возврате: boat_id=%s user_id=%s fish_id=%s item_name=%s",
                            boat_id,
                            uid,
                            fish_id,
                            item_name,
                        )
                        continue

                    # Используем сохраненную локацию, если она есть
                    final_location = catch_location if catch_location else "Море"
                    cursor.execute('''
                        INSERT INTO caught_fish (user_id, chat_id, fish_name, weight, location, length, caught_at, sold)
                        VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                    ''', (uid, item_chat_id, fish_name, weight, final_location, length, catch_time))
                    inserted_count += 1
                    logger.info(f"[boat] Записана рыба: user_id={uid}, chat_id={item_chat_id}, fish_name={fish_name}, weight={weight}, location={final_location}, length={length}, caught_at={catch_time}")
                if user_catch:
                    logger.info(f"[boat] Пользователь {uid} получил {len(user_catch)} рыб(ы), общий вес: {total_weight:.2f} кг. Улов не пропал, а распределён.")
                results.append((uid, usernames[uid], count, total_weight))
            from datetime import datetime, timedelta, timezone
            cd_until = datetime.now(timezone.utc) + timedelta(hours=12)
            # Очистить улов и выгнать всех, кроме владельца
            cursor.execute('DELETE FROM boat_catch WHERE boat_id = ?', (boat_id,))
            cursor.execute('DELETE FROM boat_members WHERE boat_id = ? AND is_owner = 0', (boat_id,))
            cursor.execute('''
                UPDATE boats 
                SET is_active = 0, current_weight = 0, cooldown_until = ? 
                WHERE id = ?
            ''', (cd_until.isoformat(), boat_id))
            _mark_boat_return_time(boat_owner_id)
            conn.commit()
            logger.info(
                "[boat] Возврат лодки %s завершён. assigned=%s inserted_to_caught_fish=%s skipped=%s results=%s",
                boat_id,
                assigned_count,
                inserted_count,
                skipped_count,
                results,
            )
            if skipped_count > 0:
                logger.warning(
                    "[boat] Возврат лодки %s: пропущены записи в caught_fish (%s из %s)",
                    boat_id,
                    skipped_count,
                    assigned_count,
                )
            return results, boat_id, 'ok'
    def _ensure_boat_invites_table(self):
        """Создать таблицу boat_invites, если её нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boat_invites (
                    id INTEGER PRIMARY KEY,
                    boat_id INTEGER NOT NULL,
                    from_user BIGINT NOT NULL,
                    to_user BIGINT NOT NULL,
                    status TEXT DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            conn.commit()

    def create_boat_invite(self, from_user: int, to_user: int) -> bool:
        """Создать приглашение в лодку от from_user к to_user."""
        self._ensure_boat_tables()
        self._ensure_boat_invites_table()
        boat = self.get_user_boat(from_user)
        if not boat or not boat['is_active']:
            return False
            
        # Проверка вместимости
        current_members = self.get_boat_members_count(boat['id'])
        if current_members >= boat['capacity']:
            return False
            
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO boat_invites (boat_id, from_user, to_user, status)
                VALUES (?, ?, ?, 'pending')
            ''', (boat['id'], from_user, to_user))
            conn.commit()
        return True

    def get_last_pending_invite_id(self, user_id: int) -> Optional[int]:
        """Найти ID последнего активного приглашения для пользователя."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id FROM boat_invites 
                WHERE to_user = ? AND status = 'pending' 
                ORDER BY created_at DESC LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None

    def respond_boat_invite(self, invite_id: int, accept: bool) -> bool:
        """Принять или отклонить приглашение в лодку."""
        self._ensure_boat_invites_table()
        with self._connect() as conn:
            cursor = conn.cursor()
            status = 'accepted' if accept else 'declined'
            
            if accept:
                # Найти лодку и проверить вместимость
                cursor.execute('SELECT b.id, b.capacity FROM boats b JOIN boat_invites bi ON bi.boat_id = b.id WHERE bi.id = ?', (invite_id,))
                row = cursor.fetchone()
                if not row:
                    return False
                boat_id, capacity = row
                
                # Посчитать текущих участников
                cursor.execute('SELECT COUNT(*) FROM boat_members WHERE boat_id = ?', (boat_id,))
                current_members = cursor.fetchone()[0]
                if current_members >= capacity:
                    # Принудительно отклоняем, так как лодка полна
                    cursor.execute('UPDATE boat_invites SET status = ? WHERE id = ?', ('declined', invite_id))
                    conn.commit()
                    return False

                # Добавить пользователя в boat_members
                cursor.execute('SELECT to_user FROM boat_invites WHERE id = ?', (invite_id,))
                row_user = cursor.fetchone()
                if row_user:
                    user_id = row_user[0]
                    cursor.execute('''
                        INSERT OR IGNORE INTO boat_members (boat_id, user_id, is_owner)
                        VALUES (?, ?, 0)
                    ''', (boat_id, user_id))
            
            cursor.execute('''
                UPDATE boat_invites SET status = ? WHERE id = ?
            ''', (status, invite_id))
            conn.commit()
        return True
    def buy_paid_boat(self, user_id: int, name: str = 'Платная лодка', price: int = 50, capacity: int = 3, max_weight: float = 1500.0, durability: int = 150) -> bool:
        """Покупка платной лодки за бриллианты. Возвращает True если успешно."""
        self._ensure_boat_tables()
        # Проверить, хватает ли бриллиантов
        player = self.get_player(user_id, 0)
        diamonds = int(player.get('diamonds', 0)) if player else 0
        if diamonds < price:
            return False
        # Списать бриллианты
        self.subtract_diamonds(user_id, 0, price)
        # Создать лодку
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO boats (user_id, type, name, capacity, max_weight, durability, max_durability, is_active)
                VALUES (?, 'paid', ?, ?, ?, ?, ?, 0)
            ''', (user_id, name, capacity, max_weight, durability, durability))
            cursor.execute("SELECT id FROM boats WHERE user_id = ? AND type = 'paid' ORDER BY id DESC LIMIT 1", (user_id,))
            boat_id = cursor.fetchone()[0]
            cursor.execute('''
                INSERT INTO boat_members (boat_id, user_id, is_owner)
                VALUES (?, ?, 1)
            ''', (boat_id, user_id))
            conn.commit()
        return True
    def get_user_id_by_username(self, username: str) -> Optional[int]:
        """Получить user_id по username."""
        if not username:
            return None
        # Remove @ if present
        if username.startswith('@'):
            username = username[1:]
        
        with self._connect() as conn:
            cursor = conn.cursor()
            # Поиск в таблице игроков (регистронезависимо)
            cursor.execute("SELECT user_id FROM players WHERE LOWER(username) = ? LIMIT 1", (username.lower(),))
            row = cursor.fetchone()
            if row:
                return row[0]
        return None

    def get_username_by_user_id(self, user_id: int) -> Optional[str]:
        """Получить последний известный username по user_id."""
        try:
            normalized_user_id = int(user_id)
        except (TypeError, ValueError):
            return None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT username
                FROM players
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                ''',
                (normalized_user_id,),
            )
            row = cursor.fetchone()

        if not row:
            return None

        username = str(row[0] or '').strip()
        return username or None

    def _ensure_user_effects_table(self):
        """Создать таблицу user_effects, если её нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_effects (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    effect_type TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_user_effects_user_type_expires
                ON user_effects (user_id, effect_type, expires_at)
            ''')
            conn.commit()

    def has_active_effect(self, user_id: int, effect_type: str) -> bool:
        """Проверить, есть ли у пользователя неистекший эффект."""
        self._ensure_user_effects_table()
        now = datetime.utcnow()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT 1
                FROM user_effects
                WHERE user_id = ?
                  AND LOWER(TRIM(effect_type)) = LOWER(TRIM(?))
                  AND expires_at > ?
                LIMIT 1
                ''',
                (int(user_id), str(effect_type or ''), now),
            )
            return cursor.fetchone() is not None

    def is_user_seasick(self, user_id: int) -> bool:
        """Проверить, есть ли у пользователя морская болезнь."""
        return self.has_active_effect(user_id, 'seasick')

    def count_active_effects(self, user_id: int, effect_type: str) -> int:
        """Количество активных эффектов заданного типа."""
        self._ensure_user_effects_table()
        now = datetime.utcnow()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COUNT(*)
                FROM user_effects
                WHERE user_id = ?
                  AND LOWER(TRIM(effect_type)) = LOWER(TRIM(?))
                  AND expires_at > ?
                ''',
                (int(user_id), str(effect_type or ''), now),
            )
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0

    def get_effect_remaining_seconds(self, user_id: int, effect_type: str) -> int:
        """Сколько секунд осталось у активного эффекта."""
        self._ensure_user_effects_table()
        now = datetime.utcnow()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT MAX(expires_at)
                FROM user_effects
                WHERE user_id = ?
                  AND LOWER(TRIM(effect_type)) = LOWER(TRIM(?))
                  AND expires_at > ?
                ''',
                (int(user_id), str(effect_type or ''), now),
            )
            row = cursor.fetchone()
            expires_at = row[0] if row else None
            if not expires_at:
                return 0
            try:
                delta = expires_at - now
                return max(0, int(delta.total_seconds()))
            except Exception:
                return 0

    def clear_timed_effect(self, user_id: int, effect_type: str) -> bool:
        """Удалить активный timed-эффект."""
        self._ensure_user_effects_table()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM user_effects WHERE user_id = ? AND LOWER(TRIM(effect_type)) = LOWER(TRIM(?))',
                (int(user_id), str(effect_type or '')),
            )
            conn.commit()
            return bool(getattr(cursor, 'rowcount', 0))

    def apply_timed_effect(
        self,
        user_id: int,
        effect_type: str,
        duration_minutes: int,
        replace_existing: bool = False,
    ) -> bool:
        """Добавить timed-эффект пользователю."""
        self._ensure_user_effects_table()
        effect_type_norm = str(effect_type or '').strip().lower()
        if not effect_type_norm:
            return False

        expires_at = datetime.utcnow() + timedelta(minutes=max(1, int(duration_minutes or 0)))
        with self._connect() as conn:
            cursor = conn.cursor()
            if replace_existing:
                cursor.execute(
                    'DELETE FROM user_effects WHERE user_id = ? AND LOWER(TRIM(effect_type)) = LOWER(TRIM(?))',
                    (int(user_id), effect_type_norm),
                )
            cursor.execute(
                '''
                INSERT INTO user_effects (user_id, effect_type, expires_at)
                VALUES (?, ?, ?)
                ''',
                (int(user_id), effect_type_norm, expires_at),
            )
            conn.commit()
            return True

    def get_active_beer_bonus_percent(self, user_id: int) -> float:
        """Суммарный бонус от активных пивных эффектов."""
        beer_effect_bonus = {
            'beer_courage': 5.0,
            'beer_lucky_wave': 3.0,
            'beer_foamy_focus': 7.0,
        }
        self._ensure_user_effects_table()
        now = datetime.utcnow()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT effect_type
                FROM user_effects
                WHERE user_id = ?
                  AND expires_at > ?
                ''',
                (int(user_id), now),
            )
            total = 0.0
            for row in cursor.fetchall() or []:
                effect_type = str(row[0] or '').strip().lower()
                total += float(beer_effect_bonus.get(effect_type, 0.0))
            return float(total)

    def _ensure_antibot_captcha_table(self):
        """Создать таблицу анти-абуза для капчи Mini App, если её нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS anti_abuse_captcha (
                    user_id BIGINT PRIMARY KEY,
                    first_link_at TIMESTAMP,
                    link_count INTEGER DEFAULT 0,
                    rhythm_streak INTEGER DEFAULT 0,
                    last_free_fish_at TIMESTAMP,
                    penalty_until TIMESTAMP,
                    active_token TEXT,
                    active_payload TEXT,
                    active_answer TEXT,
                    active_difficulty INTEGER DEFAULT 1,
                    active_created_at TIMESTAMP,
                    active_expires_at TIMESTAMP,
                    solved_at TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_anti_abuse_penalty_until
                ON anti_abuse_captcha (penalty_until)
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS idx_anti_abuse_active_token
                ON anti_abuse_captcha (active_token)
            ''')
            conn.commit()

    def _ensure_duel_tables(self):
        """Создать таблицы дуэлей и дневных бесплатных попыток."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duel_daily_attempts (
                    user_id BIGINT NOT NULL,
                    day_key TEXT NOT NULL,
                    used_invites INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (user_id, day_key)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS duels (
                    id SERIAL PRIMARY KEY,
                    chat_id BIGINT NOT NULL,
                    inviter_id BIGINT NOT NULL,
                    target_id BIGINT NOT NULL,
                    inviter_username TEXT,
                    target_username TEXT,
                    status TEXT NOT NULL DEFAULT 'pending',
                    attempt_type TEXT NOT NULL DEFAULT 'free',
                    attempt_day_key TEXT,
                    invite_expires_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    accepted_at TIMESTAMP,
                    finished_at TIMESTAMP,
                    inviter_catch_id BIGINT,
                    inviter_fish_name TEXT,
                    inviter_weight REAL,
                    inviter_length REAL,
                    target_catch_id BIGINT,
                    target_fish_name TEXT,
                    target_weight REAL,
                    target_length REAL,
                    winner_id BIGINT,
                    loser_id BIGINT,
                    free_attempt_refunded INTEGER DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_duels_status_expires
                ON duels (status, invite_expires_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_duels_inviter_status
                ON duels (inviter_id, status)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_duels_target_status
                ON duels (target_id, status)
            ''')
            conn.commit()

    def _ensure_extended_gameplay_tables(self):
        """Создать таблицы расширенных механик: экология, рынок, артели."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ecological_disasters (
                    id SERIAL PRIMARY KEY,
                    location TEXT NOT NULL,
                    reward_type TEXT NOT NULL DEFAULT 'xp',
                    reward_multiplier INTEGER NOT NULL DEFAULT 5,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ends_at TIMESTAMP NOT NULL,
                    is_active INTEGER DEFAULT 1
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ecological_disasters_active
                ON ecological_disasters (location, is_active, ends_at)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fish_sales_history (
                    id SERIAL PRIMARY KEY,
                    fish_name TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 0,
                    sold_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_fish_sales_history_name_sold_at
                ON fish_sales_history (fish_name, sold_at)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS daily_fish_market (
                    id SERIAL PRIMARY KEY,
                    market_day DATE NOT NULL UNIQUE,
                    fish_name TEXT NOT NULL,
                    multiplier REAL NOT NULL DEFAULT 2.0,
                    target_weight REAL NOT NULL DEFAULT 50.0,
                    sold_weight REAL NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_daily_fish_market_day
                ON daily_fish_market (market_day)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clans (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    owner_user_id BIGINT NOT NULL,
                    level INTEGER NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clan_members (
                    id SERIAL PRIMARY KEY,
                    clan_id BIGINT NOT NULL,
                    user_id BIGINT NOT NULL UNIQUE,
                    role TEXT NOT NULL DEFAULT 'member',
                    joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_clan_members_clan
                ON clan_members (clan_id)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS clan_donations (
                    id SERIAL PRIMARY KEY,
                    clan_id BIGINT NOT NULL,
                    item_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(clan_id, item_name)
                )
            ''')
            conn.commit()

    def _ensure_webapp_ui_tables(self):
        """Создать таблицы для UI-разделов webapp (приключения/друзья/состояние)."""
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_adventure_scores (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    game_code TEXT NOT NULL,
                    best_score INTEGER NOT NULL DEFAULT 0,
                    best_distance REAL NOT NULL DEFAULT 0,
                    runs_count INTEGER NOT NULL DEFAULT 0,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, game_code)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_adventure_game_score
                ON webapp_adventure_scores (game_code, best_score DESC)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_friend_links (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    friend_user_id BIGINT NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, friend_user_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_friend_links_user
                ON webapp_friend_links (user_id)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_friend_requests (
                    id SERIAL PRIMARY KEY,
                    requester_user_id BIGINT NOT NULL,
                    addressee_user_id BIGINT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_friend_requests_addressee
                ON webapp_friend_requests (addressee_user_id, status, created_at DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_friend_requests_requester
                ON webapp_friend_requests (requester_user_id, status, created_at DESC)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_clan_requests (
                    id SERIAL PRIMARY KEY,
                    clan_id BIGINT NOT NULL,
                    requester_user_id BIGINT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    processed_at TIMESTAMP,
                    UNIQUE(clan_id, requester_user_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_clan_requests_clan
                ON webapp_clan_requests (clan_id, status, created_at DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_clan_requests_requester
                ON webapp_clan_requests (requester_user_id, status, created_at DESC)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_ui_state (
                    user_id BIGINT PRIMARY KEY,
                    preferred_tab TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS webapp_clan_profiles (
                    clan_id BIGINT PRIMARY KEY,
                    avatar_emoji TEXT,
                    color_hex TEXT,
                    access_type TEXT,
                    description TEXT,
                    min_level INTEGER DEFAULT 0,
                    created_by BIGINT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_webapp_clan_profiles_color
                ON webapp_clan_profiles (color_hex)
            ''')
            conn.commit()

    def get_webapp_clan(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию об артели (клане) пользователя."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            
            clan_id = row[0]
            cursor.execute('''
                SELECT 
                    c.id, c.name, c.level, c.owner_user_id,
                    cp.avatar_emoji, cp.color_hex, cp.description, cp.min_level
                FROM clans c
                LEFT JOIN webapp_clan_profiles cp ON c.id = cp.clan_id
                WHERE c.id = ?
            ''', (clan_id,))
            
            clan_row = cursor.fetchone()
            if not clan_row:
                return None
            
            cursor.execute('''
                SELECT p.user_id, p.username, p.level, cm.role
                FROM clan_members cm
                JOIN players p ON cm.user_id = p.user_id
                WHERE cm.clan_id = ?
                ORDER BY CASE cm.role WHEN 'owner' THEN 1 WHEN 'officer' THEN 2 ELSE 3 END, p.level DESC
            ''', (clan_id,))
            
            members = []
            for m in cursor.fetchall():
                members.append({
                    "user_id": m[0],
                    "username": m[1],
                    "level": m[2],
                    "role": m[3]
                })
                
            return {
                "id": clan_row[0],
                "name": clan_row[1],
                "level": clan_row[2],
                "owner_id": clan_row[3],
                "avatar": clan_row[4] or "🔱",
                "color": clan_row[5] or "#00b4d8",
                "description": clan_row[6] or "",
                "min_level": clan_row[7] or 0,
                "members": members
            }

    def _parse_utc_datetime(self, raw_value: Any) -> Optional[datetime]:
        """Безопасно распарсить datetime и привести к UTC."""
        if raw_value is None or raw_value == "":
            return None

        if isinstance(raw_value, datetime):
            dt_val = raw_value
        else:
            try:
                dt_val = datetime.fromisoformat(str(raw_value))
            except Exception:
                return None

        if dt_val.tzinfo is None:
            return dt_val.replace(tzinfo=timezone.utc)
        return dt_val.astimezone(timezone.utc)

    def _to_utc_iso(self, dt_val: datetime) -> str:
        """Преобразовать datetime в ISO-строку UTC."""
        if dt_val.tzinfo is None:
            dt_val = dt_val.replace(tzinfo=timezone.utc)
        else:
            dt_val = dt_val.astimezone(timezone.utc)
        return dt_val.isoformat()

    @staticmethod
    def _normalize_item_name(value: Any) -> str:
        return str(value or '').strip().lower()

    def get_clan_member_limit(self, level: int) -> int:
        lvl = max(1, int(level or 1))
        if lvl in CLAN_MEMBER_LIMITS:
            return int(CLAN_MEMBER_LIMITS[lvl])
        return int(CLAN_MEMBER_LIMITS[max(CLAN_MEMBER_LIMITS.keys())])

    def get_clan_upgrade_requirements(self, next_level: int) -> Dict[str, int]:
        requirements = CLAN_UPGRADE_REQUIREMENTS.get(int(next_level or 0), {})
        return {str(k): int(v) for k, v in requirements.items()}

    def get_active_ecological_disaster(self, location: str) -> Optional[Dict[str, Any]]:
        now_iso = datetime.utcnow().isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE is_active = 1 AND ends_at <= ?
                ''',
                (now_iso,),
            )
            cursor.execute(
                '''
                SELECT id, location, reward_type, reward_multiplier, started_at, ends_at, is_active
                FROM ecological_disasters
                WHERE location = ? AND is_active = 1 AND ends_at > ?
                ORDER BY started_at DESC
                LIMIT 1
                ''',
                (location, now_iso),
            )
            row = cursor.fetchone()
            if not row:
                conn.commit()
                return None

            columns = [d[0] for d in cursor.description]
            conn.commit()
            return dict(zip(columns, row))

    def start_ecological_disaster(
        self,
        location: str,
        reward_type: str = 'xp',
        reward_multiplier: int = 5,
        duration_minutes: int = 60,
    ) -> Dict[str, Any]:
        normalized_type = 'coins' if str(reward_type).strip().lower() in ('coins', 'coin', 'money') else 'xp'
        multiplier = max(2, int(reward_multiplier or 5))
        duration = max(5, int(duration_minutes or 60))
        now = datetime.utcnow()
        ends_at = now + timedelta(minutes=duration)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE location = ? AND is_active = 1
                ''',
                (location,),
            )
            cursor.execute(
                '''
                INSERT INTO ecological_disasters (
                    location, reward_type, reward_multiplier, started_at, ends_at, is_active
                )
                VALUES (?, ?, ?, ?, ?, 1)
                RETURNING id, location, reward_type, reward_multiplier, started_at, ends_at, is_active
                ''',
                (location, normalized_type, multiplier, now.isoformat(), ends_at.isoformat()),
            )
            row = cursor.fetchone()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            conn.commit()
            return dict(zip(columns, row)) if row else {}

    def stop_ecological_disaster(self, location: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE ecological_disasters
                SET is_active = 0
                WHERE location = ? AND is_active = 1
                ''',
                (location,),
            )
            changed = int(getattr(cursor, 'rowcount', 0) or 0)
            conn.commit()
            return changed > 0

    def maybe_start_ecological_disaster(self, location: str, chance: float = 0.03) -> Optional[Dict[str, Any]]:
        if self._normalize_item_name(location) != self._normalize_item_name('Городской пруд'):
            return None

        active = self.get_active_ecological_disaster(location)
        if active:
            return active

        if random.random() > max(0.0, min(1.0, float(chance or 0.0))):
            return None

        reward_type = random.choice(['xp', 'coins'])
        return self.start_ecological_disaster(
            location=location,
            reward_type=reward_type,
            reward_multiplier=5,
            duration_minutes=60,
        )

    def _pick_daily_market_fish(self) -> Optional[str]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT name
                FROM fish
                WHERE rarity IN ('Обычная', 'Редкая', 'Легендарная', 'Мифическая', 'Аквариумная')
                ORDER BY RANDOM()
                LIMIT 1
                '''
            )
            row = cursor.fetchone()
            return str(row[0]) if row and row[0] else None

    def get_daily_market_offer(self, create_if_missing: bool = True) -> Optional[Dict[str, Any]]:
        day_key = datetime.utcnow().date().isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, market_day, fish_name, multiplier, target_weight, sold_weight, created_at
                FROM daily_fish_market
                WHERE market_day = ?
                LIMIT 1
                ''',
                (day_key,),
            )
            row = cursor.fetchone()
            if row:
                columns = [d[0] for d in cursor.description]
                return dict(zip(columns, row))

            if not create_if_missing:
                return None

            fish_name = self._pick_daily_market_fish()
            if not fish_name:
                return None

            cursor.execute(
                '''
                INSERT INTO daily_fish_market (market_day, fish_name, multiplier, target_weight, sold_weight)
                VALUES (?, ?, 2.0, 50.0, 0)
                RETURNING id, market_day, fish_name, multiplier, target_weight, sold_weight, created_at
                ''',
                (day_key, fish_name),
            )
            created = cursor.fetchone()
            columns = [d[0] for d in cursor.description] if cursor.description else []
            conn.commit()
            return dict(zip(columns, created)) if created else None

    def get_daily_market_status(self) -> Dict[str, Any]:
        offer = self.get_daily_market_offer(create_if_missing=True)
        if not offer:
            return {
                'active': False,
                'fish_name': None,
                'multiplier': 1.0,
                'target_weight': 0.0,
                'sold_weight': 0.0,
                'remaining_weight': 0.0,
            }

        sold_weight = max(0.0, float(offer.get('sold_weight') or 0.0))
        target_weight = max(0.0, float(offer.get('target_weight') or 0.0))
        remaining_weight = max(0.0, target_weight - sold_weight)

        return {
            'active': True,
            'id': offer.get('id'),
            'market_day': offer.get('market_day'),
            'fish_name': offer.get('fish_name'),
            'multiplier': float(offer.get('multiplier') or 1.0),
            'target_weight': target_weight,
            'sold_weight': sold_weight,
            'remaining_weight': remaining_weight,
            'is_open': remaining_weight > 0,
        }

    def get_recent_fish_sales_weight(self, fish_name: str, hours: int = 1) -> float:
        normalized_name = self._normalize_item_name(fish_name)
        if not normalized_name:
            return 0.0

        window_hours = max(1, int(hours or 1))
        since_iso = (datetime.utcnow() - timedelta(hours=window_hours)).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COALESCE(SUM(weight), 0)
                FROM fish_sales_history
                WHERE LOWER(TRIM(fish_name)) = ? AND sold_at >= ?
                ''',
                (normalized_name, since_iso),
            )
            row = cursor.fetchone()
            return float(row[0] or 0.0) if row else 0.0

    def get_hours_since_last_sale(self, fish_name: str) -> Optional[float]:
        normalized_name = self._normalize_item_name(fish_name)
        if not normalized_name:
            return None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT sold_at
                FROM fish_sales_history
                WHERE LOWER(TRIM(fish_name)) = ?
                ORDER BY sold_at DESC
                LIMIT 1
                ''',
                (normalized_name,),
            )
            row = cursor.fetchone()
            if not row or not row[0]:
                return None

            last_sale = self._parse_utc_datetime(row[0])
            if not last_sale:
                return None
            return max(0.0, (datetime.now(timezone.utc) - last_sale).total_seconds() / 3600.0)

    def get_fish_price_modifiers(self, fish_name: str) -> Dict[str, Any]:
        normalized_name = self._normalize_item_name(fish_name)
        if not normalized_name:
            return {
                'volume_multiplier': 1.0,
                'scarcity_multiplier': 1.0,
                'dynamic_multiplier': 1.0,
                'market_multiplier': 1.0,
                'total_multiplier': 1.0,
                'hour_volume': 0.0,
                'hours_since_last_sale': None,
                'market_active': False,
            }

        hour_volume = self.get_recent_fish_sales_weight(normalized_name, hours=1)
        # Динамика лавки: при массовых продажах цена падает ступенчато.
        # В пике просадка может доходить до x0.6.
        if hour_volume >= 260.0:
            volume_multiplier = 0.60
        elif hour_volume >= 200.0:
            volume_multiplier = 0.68
        elif hour_volume >= 150.0:
            volume_multiplier = 0.76
        elif hour_volume >= 110.0:
            volume_multiplier = 0.84
        elif hour_volume >= 80.0:
            volume_multiplier = 0.90
        elif hour_volume >= 40.0:
            volume_multiplier = 0.95
        elif hour_volume >= 20.0:
            volume_multiplier = 0.98
        else:
            volume_multiplier = 1.0

        hours_since_last_sale = self.get_hours_since_last_sale(normalized_name)
        if hours_since_last_sale is None:
            scarcity_multiplier = 1.08
        elif hours_since_last_sale >= 24:
            scarcity_multiplier = 1.15
        elif hours_since_last_sale >= 12:
            scarcity_multiplier = 1.12
        elif hours_since_last_sale >= 6:
            scarcity_multiplier = 1.08
        elif hours_since_last_sale >= 3:
            scarcity_multiplier = 1.04
        else:
            scarcity_multiplier = 1.0

        dynamic_multiplier = volume_multiplier * scarcity_multiplier
        dynamic_multiplier = max(0.60, min(1.20, dynamic_multiplier))

        market_offer = self.get_daily_market_offer(create_if_missing=True)
        market_multiplier = 1.0
        market_active = False
        if market_offer:
            market_fish = self._normalize_item_name(market_offer.get('fish_name'))
            sold_weight = float(market_offer.get('sold_weight') or 0.0)
            target_weight = float(market_offer.get('target_weight') or 0.0)
            if market_fish == normalized_name and sold_weight < target_weight:
                market_active = True
                market_multiplier = max(1.0, float(market_offer.get('multiplier') or 1.0))

        total_multiplier = dynamic_multiplier * market_multiplier
        total_multiplier = max(0.6, min(3.0, total_multiplier))

        return {
            'volume_multiplier': volume_multiplier,
            'scarcity_multiplier': scarcity_multiplier,
            'dynamic_multiplier': dynamic_multiplier,
            'market_multiplier': market_multiplier,
            'total_multiplier': total_multiplier,
            'hour_volume': hour_volume,
            'hours_since_last_sale': hours_since_last_sale,
            'market_active': market_active,
        }

    def get_clan_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT c.id, c.name, c.owner_user_id, c.level, c.created_at, cm.role,
                       (SELECT COUNT(*) FROM clan_members m WHERE m.clan_id = c.id) AS members_count
                FROM clan_members cm
                JOIN clans c ON c.id = cm.clan_id
                WHERE cm.user_id = ?
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [d[0] for d in cursor.description]
            clan = dict(zip(columns, row))
            clan['max_members'] = self.get_clan_member_limit(int(clan.get('level') or 1))
            return clan

    def get_clan_by_id(self, clan_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT c.id, c.name, c.owner_user_id, c.level, c.created_at,
                       (SELECT COUNT(*) FROM clan_members m WHERE m.clan_id = c.id) AS members_count
                FROM clans c
                WHERE c.id = ?
                LIMIT 1
                ''',
                (int(clan_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [d[0] for d in cursor.description]
            clan = dict(zip(columns, row))
            clan['max_members'] = self.get_clan_member_limit(int(clan.get('level') or 1))
            return clan

    def list_clans(self, limit: int = 10) -> List[Dict[str, Any]]:
        limit_val = max(1, min(50, int(limit or 10)))
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT c.id, c.name, c.owner_user_id, c.level, c.created_at,
                       (SELECT COUNT(*) FROM clan_members m WHERE m.clan_id = c.id) AS members_count
                FROM clans c
                ORDER BY c.level DESC, c.created_at ASC
                LIMIT ?
                ''',
                (limit_val,),
            )
            rows = cursor.fetchall() or []
            columns = [d[0] for d in cursor.description] if cursor.description else []
            result = [dict(zip(columns, row)) for row in rows]
            for clan in result:
                clan['max_members'] = self.get_clan_member_limit(int(clan.get('level') or 1))
            return result

    def get_clan_donations(self, clan_id: int) -> Dict[str, int]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT item_name, quantity
                FROM clan_donations
                WHERE clan_id = ?
                ''',
                (int(clan_id),),
            )
            rows = cursor.fetchall() or []
            result: Dict[str, int] = {}
            for item_name, quantity in rows:
                result[str(item_name)] = int(quantity or 0)
            return result

    def create_clan(self, owner_user_id: int, clan_name: str) -> Dict[str, Any]:
        clean_name = str(clan_name or '').strip()
        if len(clean_name) < 3:
            return {'ok': False, 'reason': 'name_too_short'}
        if len(clean_name) > 32:
            return {'ok': False, 'reason': 'name_too_long'}

        if self.get_clan_by_user(owner_user_id):
            return {'ok': False, 'reason': 'already_in_clan'}

        cost = 100000
        with self._connect() as conn:
            cursor = conn.cursor()
            # Check balance
            cursor.execute('SELECT coins FROM players WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) LIMIT 1', (owner_user_id,))
            row = cursor.fetchone()
            if not row:
                # Fallback to any row
                cursor.execute('SELECT coins FROM players WHERE user_id = ? LIMIT 1', (owner_user_id,))
                row = cursor.fetchone()
            
            if not row or int(row[0] or 0) < cost:
                return {'ok': False, 'reason': 'not_enough_coins', 'cost': cost}

            cursor.execute('SELECT id FROM clans WHERE LOWER(TRIM(name)) = ?', (self._normalize_item_name(clean_name),))
            if cursor.fetchone():
                return {'ok': False, 'reason': 'name_taken'}

            # Deduct coins
            cursor.execute('UPDATE players SET coins = coins - ? WHERE user_id = ?', (cost, int(owner_user_id)))

            cursor.execute(
                '''
                INSERT INTO clans (name, owner_user_id, level)
                VALUES (?, ?, 1)
                RETURNING id, name, owner_user_id, level, created_at
                ''',
                (clean_name, int(owner_user_id)),
            )
            clan_row = cursor.fetchone()
            if not clan_row:
                conn.rollback()
                return {'ok': False, 'reason': 'create_failed'}

            clan_id = int(clan_row[0])
            cursor.execute(
                '''
                INSERT INTO clan_members (clan_id, user_id, role)
                VALUES (?, ?, 'leader')
                ''',
                (clan_id, int(owner_user_id)),
            )
            conn.commit()

        clan = self.get_clan_by_id(clan_id)
        return {'ok': True, 'clan': clan}

    def join_clan(self, user_id: int, clan_id: Any) -> Dict[str, Any]:
        if self.get_clan_by_user(user_id):
            return {'ok': False, 'reason': 'already_in_clan'}

        resolved_clan_id: Optional[int] = None
        raw_value = str(clan_id or '').strip()
        if not raw_value:
            return {'ok': False, 'reason': 'clan_not_found'}

        if raw_value.isdigit():
            resolved_clan_id = int(raw_value)
        else:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT id
                    FROM clans
                    WHERE LOWER(TRIM(name)) = LOWER(TRIM(?))
                    LIMIT 1
                    ''',
                    (raw_value,),
                )
                row = cursor.fetchone()
                if row:
                    resolved_clan_id = int(row[0])

        if not resolved_clan_id:
            return {'ok': False, 'reason': 'clan_not_found'}

        clan = self.get_clan_by_id(resolved_clan_id)
        if not clan:
            return {'ok': False, 'reason': 'clan_not_found'}

        members_count = int(clan.get('members_count') or 0)
        max_members = int(clan.get('max_members') or self.get_clan_member_limit(int(clan.get('level') or 1)))
        if members_count >= max_members:
            return {'ok': False, 'reason': 'clan_full'}

        # Check min_level from webapp profile
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT min_level, access_type FROM webapp_clan_profiles WHERE clan_id = ?', (int(resolved_clan_id),))
            profile_row = cursor.fetchone()
            if profile_row:
                min_level = int(profile_row[0] or 0)
                access_type = str(profile_row[1] or 'open')
                
                # Check level
                cursor.execute('SELECT level FROM players WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) LIMIT 1', (user_id,))
                user_row = cursor.fetchone()
                if not user_row:
                     cursor.execute('SELECT level FROM players WHERE user_id = ? LIMIT 1', (user_id,))
                     user_row = cursor.fetchone()
                
                user_level = int(user_row[0] or 0) if user_row else 0
                if user_level < min_level:
                    return {'ok': False, 'reason': 'level_too_low', 'required': min_level}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO clan_members (clan_id, user_id, role)
                VALUES (?, ?, 'member')
                ''',
                (int(resolved_clan_id), int(user_id)),
            )
            conn.commit()

        return {'ok': True, 'clan': self.get_clan_by_id(resolved_clan_id)}

    def leave_clan(self, user_id: int) -> Dict[str, Any]:
        clan = self.get_clan_by_user(user_id)
        if not clan:
            return {'ok': False, 'reason': 'not_in_clan'}

        clan_id = int(clan['id'])
        is_leader = str(clan.get('role') or 'member') == 'leader'
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if is_leader:
                # Find new leader
                cursor.execute('''
                    SELECT user_id 
                    FROM clan_members 
                     WHERE clan_id = ? AND user_id != ?
                     ORDER BY CASE role WHEN 'officer' THEN 1 ELSE 2 END, joined_at ASC
                     LIMIT 1
                ''', (clan_id, int(user_id)))
                new_leader_row = cursor.fetchone()
                
                if new_leader_row:
                    new_leader_id = int(new_leader_row[0])
                    # Transfer leadership
                    cursor.execute('UPDATE clan_members SET role = "leader" WHERE user_id = ? AND clan_id = ?', (new_leader_id, clan_id))
                    cursor.execute('UPDATE clans SET owner_user_id = ? WHERE id = ?', (new_leader_id, clan_id))
                else:
                    # No other members, but user said "она остается"
                    # However, we still need to remove the current leader from clan_members
                    # If we don't delete the clan, it will have 0 members and no owner.
                    # We'll just leave the clan record in 'clans' but it will be empty.
                    pass
            
            cursor.execute('DELETE FROM clan_members WHERE user_id = ? AND clan_id = ?', (int(user_id), clan_id))
            conn.commit()

        return {'ok': True, 'disbanded': False}

    def upgrade_clan(self, user_id: int) -> Dict[str, Any]:
        clan = self.get_clan_by_user(user_id)
        if not clan:
            return {'ok': False, 'reason': 'not_in_clan'}
        if str(clan.get('role') or 'member') != 'leader':
            return {'ok': False, 'reason': 'leader_only'}

        clan_id = int(clan['id'])
        current_level = int(clan.get('level') or 1)
        next_level = current_level + 1
        requirements = self.get_clan_upgrade_requirements(next_level)
        if not requirements:
            return {'ok': False, 'reason': 'max_level'}

        donations = self.get_clan_donations(clan_id)
        missing: Dict[str, int] = {}
        for item_name, required_qty in requirements.items():
            have_qty = int(donations.get(item_name, 0) or 0)
            if have_qty < required_qty:
                missing[item_name] = required_qty - have_qty

        if missing:
            return {'ok': False, 'reason': 'not_enough_resources', 'missing': missing, 'requirements': requirements}

        with self._connect() as conn:
            cursor = conn.cursor()
            for item_name, required_qty in requirements.items():
                cursor.execute(
                    '''
                    UPDATE clan_donations
                    SET quantity = CASE WHEN quantity - ? > 0 THEN quantity - ? ELSE 0 END,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE clan_id = ? AND item_name = ?
                    ''',
                    (required_qty, required_qty, clan_id, item_name),
                )

            cursor.execute('UPDATE clans SET level = ? WHERE id = ?', (next_level, clan_id))
            conn.commit()

        return {'ok': True, 'clan': self.get_clan_by_id(clan_id), 'requirements': requirements}

    @staticmethod
    def _normalize_captcha_answer(value: str) -> str:
        """Нормализовать ответ на капчу для простого сравнения."""
        normalized = str(value or "").strip().casefold()
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized

    def _generate_wave_cipher_captcha(self, difficulty: int) -> Dict[str, Any]:
        """Сгенерировать простую капчу-вопрос (математика/базовые факты)."""
        normalized_difficulty = max(1, min(10, int(difficulty or 1)))

        a = random.randint(2, 9)
        b = random.randint(2, 9)
        if random.random() < 0.5:
            math_prompt = f"Сколько будет {a} + {b}?"
            math_answer = str(a + b)
        else:
            greater, lower = max(a, b), min(a, b)
            math_prompt = f"Сколько будет {greater} - {lower}?"
            math_answer = str(greater - lower)

        quiz_pool: List[Dict[str, Any]] = [
            {
                "prompt": "Столица Италии?",
                "answer": "рим|rome",
            },
            {
                "prompt": "Какой день идет после понедельника?",
                "answer": "вторник",
            },
            {
                "prompt": "Сколько дней в неделе?",
                "answer": "7|семь",
            },
            {
                "prompt": math_prompt,
                "answer": math_answer,
            },
        ]

        selected = random.choice(quiz_pool)
        payload = {
            "type": "simple_quiz",
            "title": "Простая капча",
            "difficulty": normalized_difficulty,
            "prompt": str(selected.get("prompt") or "Ответьте на простой вопрос."),
            "answer_hint": "Введите короткий ответ.",
        }

        return {
            "payload": payload,
            "answer": str(selected.get("answer") or ""),
        }

    def _fetch_antibot_row(self, user_id: int) -> Dict[str, Any]:
        """Прочитать строку анти-абуза или вернуть состояние по умолчанию."""
        self._ensure_antibot_captcha_table()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT user_id, first_link_at, link_count, rhythm_streak, last_free_fish_at,
                       penalty_until, active_token, active_payload, active_answer,
                       active_difficulty, active_created_at, active_expires_at, solved_at
                FROM anti_abuse_captcha
                WHERE user_id = ?
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    '''
                    INSERT INTO anti_abuse_captcha (user_id, link_count, rhythm_streak, updated_at)
                    VALUES (?, 0, 0, ?)
                    ''',
                    (user_id, self._to_utc_iso(datetime.now(timezone.utc))),
                )
                conn.commit()
                return {
                    "user_id": user_id,
                    "first_link_at": None,
                    "link_count": 0,
                    "rhythm_streak": 0,
                    "last_free_fish_at": None,
                    "penalty_until": None,
                    "active_token": None,
                    "active_payload": None,
                    "active_answer": None,
                    "active_difficulty": 1,
                    "active_created_at": None,
                    "active_expires_at": None,
                    "solved_at": None,
                }

            columns = [
                "user_id",
                "first_link_at",
                "link_count",
                "rhythm_streak",
                "last_free_fish_at",
                "penalty_until",
                "active_token",
                "active_payload",
                "active_answer",
                "active_difficulty",
                "active_created_at",
                "active_expires_at",
                "solved_at",
            ]
            return dict(zip(columns, row))

    def get_antibot_gate_status(self, user_id: int, penalty_hours: int = 6) -> Dict[str, Any]:
        """
        Текущее состояние анти-абуза.
        Если капча просрочена, автоматически включает штраф до 6 часов от первой ссылки.
        """
        row = self._fetch_antibot_row(user_id)
        now = datetime.now(timezone.utc)

        first_link_at = self._parse_utc_datetime(row.get("first_link_at"))
        penalty_until = self._parse_utc_datetime(row.get("penalty_until"))
        active_created_at = self._parse_utc_datetime(row.get("active_created_at"))
        active_expires_at = self._parse_utc_datetime(row.get("active_expires_at"))
        active_token = str(row.get("active_token") or "").strip() or None
        link_count = max(0, int(row.get("link_count") or 0))
        rhythm_streak = max(0, int(row.get("rhythm_streak") or 0))
        active_difficulty = max(1, int(row.get("active_difficulty") or 1))

        clear_active_payload = False
        should_update = False

        if first_link_at and now >= (first_link_at + timedelta(hours=penalty_hours)):
            first_link_at = None
            penalty_until = None
            link_count = 0
            rhythm_streak = 0
            active_token = None
            active_expires_at = None
            active_created_at = None
            active_difficulty = 1
            clear_active_payload = True
            should_update = True

        if active_token and active_expires_at and active_expires_at <= now:
            if not first_link_at:
                first_link_at = active_created_at or now
            link_count = 0
            penalty_until = None
            active_token = None
            active_expires_at = None
            active_created_at = None
            active_difficulty = 1
            clear_active_payload = True
            should_update = True

        if penalty_until and penalty_until <= now:
            penalty_until = None
            first_link_at = None
            link_count = 0
            active_token = None
            active_expires_at = None
            active_created_at = None
            active_difficulty = 1
            clear_active_payload = True
            should_update = True

        if should_update:
            with self._connect() as conn:
                cursor = conn.cursor()
                if clear_active_payload:
                    cursor.execute(
                        '''
                        UPDATE anti_abuse_captcha
                        SET first_link_at = ?,
                            link_count = ?,
                            rhythm_streak = ?,
                            penalty_until = ?,
                            active_token = ?,
                            active_payload = NULL,
                            active_answer = NULL,
                            active_difficulty = ?,
                            active_created_at = ?,
                            active_expires_at = ?,
                            solved_at = NULL,
                            updated_at = ?
                        WHERE user_id = ?
                        ''',
                        (
                            self._to_utc_iso(first_link_at) if first_link_at else None,
                            link_count,
                            rhythm_streak,
                            self._to_utc_iso(penalty_until) if penalty_until else None,
                            active_token,
                            active_difficulty,
                            self._to_utc_iso(active_created_at) if active_created_at else None,
                            self._to_utc_iso(active_expires_at) if active_expires_at else None,
                            self._to_utc_iso(now),
                            user_id,
                        ),
                    )
                else:
                    cursor.execute(
                        '''
                        UPDATE anti_abuse_captcha
                        SET first_link_at = ?,
                            link_count = ?,
                            rhythm_streak = ?,
                            penalty_until = ?,
                            active_token = ?,
                            active_difficulty = ?,
                            active_created_at = ?,
                            active_expires_at = ?,
                            updated_at = ?
                        WHERE user_id = ?
                        ''',
                        (
                            self._to_utc_iso(first_link_at) if first_link_at else None,
                            link_count,
                            rhythm_streak,
                            self._to_utc_iso(penalty_until) if penalty_until else None,
                            active_token,
                            active_difficulty,
                            self._to_utc_iso(active_created_at) if active_created_at else None,
                            self._to_utc_iso(active_expires_at) if active_expires_at else None,
                            self._to_utc_iso(now),
                            user_id,
                        ),
                    )
                conn.commit()

        penalty_active = bool(penalty_until and penalty_until > now)
        challenge_active = bool(active_token and active_expires_at and active_expires_at > now)

        return {
            "needs_captcha": penalty_active or challenge_active,
            "penalty_active": penalty_active,
            "penalty_until": self._to_utc_iso(penalty_until) if penalty_until else None,
            "first_link_at": self._to_utc_iso(first_link_at) if first_link_at else None,
            "challenge_active": challenge_active,
            "challenge_token": active_token,
            "challenge_expires_at": self._to_utc_iso(active_expires_at) if active_expires_at else None,
            "link_count": link_count,
            "rhythm_streak": rhythm_streak,
            "active_difficulty": active_difficulty,
        }

    def register_free_fish_attempt(
        self,
        user_id: int,
        attempt_time: Optional[datetime] = None,
        min_interval_seconds: int = 480,
        max_interval_seconds: int = 720,
        trigger_streak: int = 5,
    ) -> Dict[str, Any]:
        """
        Зафиксировать бесплатную попытку /fish и проверить подозрительный ритм.
        Триггер срабатывает при стабильных интервалах (по умолчанию 8-12 минут).
        """
        gate = self.get_antibot_gate_status(user_id)
        if gate.get("needs_captcha"):
            return {
                "trigger": False,
                "ignored": True,
                "rhythm_streak": int(gate.get("rhythm_streak") or 0),
                "delta_seconds": None,
            }

        now = attempt_time if isinstance(attempt_time, datetime) else datetime.now(timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)
        else:
            now = now.astimezone(timezone.utc)

        row = self._fetch_antibot_row(user_id)
        last_attempt = self._parse_utc_datetime(row.get("last_free_fish_at"))
        rhythm_streak = max(0, int(row.get("rhythm_streak") or 0))

        delta_seconds: Optional[int] = None
        if last_attempt:
            delta_seconds = int((now - last_attempt).total_seconds())
            in_rhythm = min_interval_seconds <= delta_seconds <= max_interval_seconds
            if in_rhythm:
                rhythm_streak += 1
            else:
                rhythm_streak = 0
        else:
            rhythm_streak = 0

        trigger = rhythm_streak >= max(1, int(trigger_streak or 1))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE anti_abuse_captcha
                SET last_free_fish_at = ?,
                    rhythm_streak = ?,
                    updated_at = ?
                WHERE user_id = ?
                ''',
                (
                    self._to_utc_iso(now),
                    rhythm_streak,
                    self._to_utc_iso(now),
                    user_id,
                ),
            )
            conn.commit()

        return {
            "trigger": bool(trigger),
            "ignored": False,
            "rhythm_streak": rhythm_streak,
            "delta_seconds": delta_seconds,
        }

    def issue_antibot_challenge(
        self,
        user_id: int,
        reason: str = "rhythm_detected",
        challenge_ttl_seconds: int = 180,
        penalty_hours: int = 6,
    ) -> Dict[str, Any]:
        """Создать/обновить активную капчу для пользователя и вернуть метаданные ссылки."""
        gate = self.get_antibot_gate_status(user_id, penalty_hours=penalty_hours)
        now = datetime.now(timezone.utc)

        first_link_at = self._parse_utc_datetime(gate.get("first_link_at"))
        penalty_until = self._parse_utc_datetime(gate.get("penalty_until"))
        link_count = max(0, int(gate.get("link_count") or 0))

        if not first_link_at:
            first_link_at = now
            link_count = 0
            penalty_until = None

        window_end = first_link_at + timedelta(hours=penalty_hours)
        if now >= window_end:
            first_link_at = now
            link_count = 0
            penalty_until = None

        link_count += 1
        difficulty = 1
        challenge_data = self._generate_wave_cipher_captcha(difficulty)
        token = secrets.token_urlsafe(18)
        expires_at = now + timedelta(seconds=max(15, int(challenge_ttl_seconds or 180)))

        payload_json = json.dumps(challenge_data["payload"], ensure_ascii=False)
        expected_answer = str(challenge_data["answer"])

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE anti_abuse_captcha
                SET first_link_at = ?,
                    link_count = ?,
                    active_token = ?,
                    active_payload = ?,
                    active_answer = ?,
                    active_difficulty = ?,
                    active_created_at = ?,
                    active_expires_at = ?,
                    solved_at = NULL,
                    updated_at = ?
                WHERE user_id = ?
                ''',
                (
                    self._to_utc_iso(first_link_at),
                    link_count,
                    token,
                    payload_json,
                    expected_answer,
                    difficulty,
                    self._to_utc_iso(now),
                    self._to_utc_iso(expires_at),
                    self._to_utc_iso(now),
                    user_id,
                ),
            )
            conn.commit()

        return {
            "ok": True,
            "reason": str(reason or "rhythm_detected"),
            "token": token,
            "difficulty": difficulty,
            "link_count": link_count,
            "expires_at": self._to_utc_iso(expires_at),
            "first_link_at": self._to_utc_iso(first_link_at),
            "penalty_until": self._to_utc_iso(penalty_until) if penalty_until else None,
            "payload": challenge_data["payload"],
        }

    def get_antibot_challenge_for_user(self, user_id: int, token: str) -> Dict[str, Any]:
        """Получить активную капчу пользователя по токену."""
        normalized_token = str(token or "").strip()
        if not normalized_token:
            return {"ok": False, "error": "token_required"}

        gate = self.get_antibot_gate_status(user_id)
        row = self._fetch_antibot_row(user_id)
        now = datetime.now(timezone.utc)

        active_token = str(row.get("active_token") or "").strip()
        if not active_token:
            return {
                "ok": False,
                "error": "challenge_not_found",
                "penalty_until": gate.get("penalty_until"),
            }

        if active_token != normalized_token:
            return {
                "ok": False,
                "error": "challenge_not_found",
                "penalty_until": gate.get("penalty_until"),
            }

        expires_at = self._parse_utc_datetime(row.get("active_expires_at"))
        if not expires_at or expires_at <= now:
            self.get_antibot_gate_status(user_id)
            gate = self.get_antibot_gate_status(user_id)
            return {
                "ok": False,
                "error": "challenge_expired",
                "penalty_until": gate.get("penalty_until"),
            }

        payload_raw = row.get("active_payload")
        payload_data: Dict[str, Any] = {}
        if payload_raw:
            try:
                payload_data = json.loads(str(payload_raw))
            except Exception:
                payload_data = {}

        remaining_seconds = max(0, int((expires_at - now).total_seconds()))
        return {
            "ok": True,
            "challenge": {
                "token": active_token,
                "difficulty": max(1, int(row.get("active_difficulty") or 1)),
                "expires_at": self._to_utc_iso(expires_at),
                "remaining_seconds": remaining_seconds,
                "link_count": max(0, int(row.get("link_count") or 0)),
                "payload": payload_data,
            },
            "penalty_active": bool(gate.get("penalty_active")),
            "penalty_until": gate.get("penalty_until"),
            "first_link_at": gate.get("first_link_at"),
        }

    def solve_antibot_challenge(self, user_id: int, token: str, answer: str) -> Dict[str, Any]:
        """Проверить ответ на капчу и обновить состояние анти-абуза."""
        normalized_token = str(token or "").strip()
        normalized_answer = self._normalize_captcha_answer(str(answer or ""))

        if not normalized_token:
            return {"ok": False, "error": "token_required"}
        if not normalized_answer:
            return {"ok": False, "error": "answer_required"}

        gate = self.get_antibot_gate_status(user_id)

        row = self._fetch_antibot_row(user_id)
        now = datetime.now(timezone.utc)

        active_token = str(row.get("active_token") or "").strip()
        expected_answer = str(row.get("active_answer") or "").strip()
        expires_at = self._parse_utc_datetime(row.get("active_expires_at"))

        if not active_token or active_token != normalized_token:
            if gate.get("penalty_active"):
                return {
                    "ok": False,
                    "error": "penalty_active",
                    "penalty_until": gate.get("penalty_until"),
                }
            return {"ok": False, "error": "challenge_not_found"}

        if not expires_at or expires_at <= now:
            self.get_antibot_gate_status(user_id)
            gate_after_expire = self.get_antibot_gate_status(user_id)
            return {
                "ok": False,
                "error": "challenge_expired",
                "penalty_until": gate_after_expire.get("penalty_until"),
            }

        expected_variants = [
            self._normalize_captcha_answer(item)
            for item in expected_answer.split("|")
            if str(item).strip()
        ]
        if not expected_variants:
            expected_variants = [self._normalize_captcha_answer(expected_answer)]

        if normalized_answer not in expected_variants:
            return {"ok": False, "error": "wrong_answer"}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE anti_abuse_captcha
                SET first_link_at = NULL,
                    link_count = 0,
                    rhythm_streak = 0,
                    penalty_until = NULL,
                    active_token = NULL,
                    active_payload = NULL,
                    active_answer = NULL,
                    active_difficulty = 1,
                    active_created_at = NULL,
                    active_expires_at = NULL,
                    solved_at = ?,
                    updated_at = ?
                WHERE user_id = ?
                ''',
                (self._to_utc_iso(now), self._to_utc_iso(now), user_id),
            )
            conn.commit()

        return {"ok": True}

    def _duel_day_key(self, now_dt: Optional[datetime] = None) -> str:
        base = now_dt if isinstance(now_dt, datetime) else datetime.now(timezone.utc)
        if base.tzinfo is None:
            base = base.replace(tzinfo=timezone.utc)
        else:
            base = base.astimezone(timezone.utc)
        return base.date().isoformat()

    def _normalize_duel_username(self, value: Optional[str]) -> Optional[str]:
        raw = str(value or '').strip()
        if not raw:
            return None
        if raw.startswith('@'):
            raw = raw[1:]
        return raw or None

    def get_duel_attempts_status(self, user_id: int, free_limit: int = 3) -> Dict[str, Any]:
        """Вернуть информацию о дневных бесплатных попытках приглашения в дуэль."""
        self._ensure_duel_tables()
        now_dt = datetime.now(timezone.utc)
        day_key = self._duel_day_key(now_dt)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT used_invites
                FROM duel_daily_attempts
                WHERE user_id = ? AND day_key = ?
                LIMIT 1
                ''',
                (int(user_id), day_key),
            )
            row = cursor.fetchone()

        used = int((row[0] if row else 0) or 0)
        used = max(0, used)
        left = max(0, int(free_limit) - used)
        return {
            'day_key': day_key,
            'used': used,
            'left': left,
            'free_limit': int(free_limit),
        }

    def get_duel_by_id(self, duel_id: int) -> Optional[Dict[str, Any]]:
        """Получить дуэль по id."""
        self._ensure_duel_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM duels
                WHERE id = ?
                LIMIT 1
                ''',
                (int(duel_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    def expire_duel_invitation_by_id(self, duel_id: int, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Протухание ожидающего приглашения с возвратом бесплатной попытки (если применимо)."""
        self._ensure_duel_tables()
        now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        else:
            now_dt = now_dt.astimezone(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if str(duel.get('status') or '') != 'pending':
                return {'ok': False, 'error': 'not_pending', 'duel': duel}

            expires_at = self._parse_utc_datetime(duel.get('invite_expires_at'))
            if expires_at and expires_at > now_dt:
                return {'ok': False, 'error': 'not_expired', 'duel': duel}

            refunded_flag = int(duel.get('free_attempt_refunded') or 0)
            attempt_type = str(duel.get('attempt_type') or '')
            attempt_day_key = str(duel.get('attempt_day_key') or '').strip()

            if attempt_type == 'free' and refunded_flag == 0 and attempt_day_key:
                cursor.execute(
                    '''
                    UPDATE duel_daily_attempts
                    SET used_invites = CASE WHEN used_invites > 0 THEN used_invites - 1 ELSE 0 END,
                        updated_at = ?
                    WHERE user_id = ? AND day_key = ?
                    ''',
                    (now_iso, int(duel.get('inviter_id') or 0), attempt_day_key),
                )
                refunded_flag = 1

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'expired',
                    finished_at = ?,
                    free_attempt_refunded = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'pending'
                ''',
                (now_iso, refunded_flag, now_iso, int(duel_id)),
            )
            conn.commit()

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            refreshed = cursor.fetchone()
            if not refreshed:
                return {'ok': False, 'error': 'duel_not_found'}
            refreshed_columns = [description[0] for description in cursor.description]
            refreshed_duel = dict(zip(refreshed_columns, refreshed))

        return {'ok': True, 'expired': True, 'duel': refreshed_duel}

    def expire_pending_duels(self, now: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Протухание всех ожидающих приглашений, чей таймаут истёк."""
        self._ensure_duel_tables()
        now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        else:
            now_dt = now_dt.astimezone(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id
                FROM duels
                WHERE status = 'pending'
                  AND invite_expires_at IS NOT NULL
                  AND invite_expires_at <= ?
                ''',
                (now_iso,),
            )
            ids = [int(row[0]) for row in cursor.fetchall()]

        expired_rows: List[Dict[str, Any]] = []
        for duel_id in ids:
            result = self.expire_duel_invitation_by_id(duel_id, now=now_dt)
            if result.get('ok') and result.get('expired') and result.get('duel'):
                expired_rows.append(result['duel'])

        return expired_rows

    def expire_active_duel_by_id(
        self,
        duel_id: int,
        now: Optional[datetime] = None,
        timeout_seconds: int = 3600,
    ) -> Dict[str, Any]:
        """Завершить активную дуэль по таймауту после принятия с возвратом бесплатной попытки пригласившему."""
        self._ensure_duel_tables()
        now_dt = now if isinstance(now, datetime) else datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        else:
            now_dt = now_dt.astimezone(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)
        timeout_td = timedelta(seconds=max(1, int(timeout_seconds or 60)))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if str(duel.get('status') or '') != 'active':
                return {'ok': False, 'error': 'not_active', 'duel': duel}

            accepted_at = self._parse_utc_datetime(duel.get('accepted_at'))
            if not accepted_at:
                accepted_at = self._parse_utc_datetime(duel.get('created_at')) or now_dt

            if now_dt < (accepted_at + timeout_td):
                return {'ok': False, 'error': 'not_timed_out', 'duel': duel}

            inviter_done = duel.get('inviter_weight') is not None
            target_done = duel.get('target_weight') is not None
            if inviter_done and target_done:
                return {
                    'ok': False,
                    'error': 'already_resolved',
                    'duel': duel,
                    'inviter_done': True,
                    'target_done': True,
                }

            refunded_flag = int(duel.get('free_attempt_refunded') or 0)
            attempt_type = str(duel.get('attempt_type') or '')
            attempt_day_key = str(duel.get('attempt_day_key') or '').strip()

            if attempt_type == 'free' and refunded_flag == 0 and attempt_day_key:
                cursor.execute(
                    '''
                    UPDATE duel_daily_attempts
                    SET used_invites = CASE WHEN used_invites > 0 THEN used_invites - 1 ELSE 0 END,
                        updated_at = ?
                    WHERE user_id = ? AND day_key = ?
                    ''',
                    (now_iso, int(duel.get('inviter_id') or 0), attempt_day_key),
                )
                refunded_flag = 1

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'expired',
                    finished_at = ?,
                    free_attempt_refunded = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'active'
                ''',
                (now_iso, refunded_flag, now_iso, int(duel_id)),
            )
            conn.commit()

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            refreshed = cursor.fetchone()
            if not refreshed:
                return {'ok': False, 'error': 'duel_not_found'}
            refreshed_columns = [description[0] for description in cursor.description]
            refreshed_duel = dict(zip(refreshed_columns, refreshed))

        return {
            'ok': True,
            'expired': True,
            'duel': refreshed_duel,
            'inviter_done': bool(inviter_done),
            'target_done': bool(target_done),
        }

    def get_active_duel_for_user(
        self,
        user_id: int,
        active_timeout_seconds: int = 3600,
    ) -> Optional[Dict[str, Any]]:
        """Получить активную/ожидающую дуэль пользователя во всех чатах."""
        self.expire_pending_duels()
        now_dt = datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        else:
            now_dt = now_dt.astimezone(timezone.utc)

        stale_active_duel_id: Optional[int] = None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM duels
                WHERE status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (int(user_id), int(user_id)),
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if str(duel.get('status') or '') == 'active':
                accepted_at = self._parse_utc_datetime(duel.get('accepted_at'))
                if not accepted_at:
                    accepted_at = self._parse_utc_datetime(duel.get('created_at'))
                if accepted_at and now_dt >= (accepted_at + timedelta(seconds=max(1, int(active_timeout_seconds or 60)))):
                    stale_active_duel_id = int(duel.get('id') or 0)
                else:
                    return duel
            else:
                return duel

        if stale_active_duel_id > 0:
            try:
                self.expire_active_duel_by_id(
                    duel_id=stale_active_duel_id,
                    now=now_dt,
                    timeout_seconds=active_timeout_seconds,
                )
            except Exception:
                # Best-effort cleanup for stale active duels if scheduler job was missed.
                pass

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM duels
                WHERE status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (int(user_id), int(user_id)),
            )
            refreshed_row = cursor.fetchone()
            if not refreshed_row:
                return None
            refreshed_columns = [description[0] for description in cursor.description]
            return dict(zip(refreshed_columns, refreshed_row))

    def create_duel_invitation(
        self,
        chat_id: int,
        inviter_id: int,
        target_id: int,
        inviter_username: Optional[str] = None,
        target_username: Optional[str] = None,
        attempt_type: str = 'free',
        invite_timeout_seconds: int = 60,
        free_limit: int = 3,
    ) -> Dict[str, Any]:
        """Создать приглашение в дуэль с проверкой лимитов и активных дуэлей."""
        self._ensure_duel_tables()
        self.expire_pending_duels()

        inviter_id = int(inviter_id)
        target_id = int(target_id)
        chat_id = int(chat_id)
        attempt_kind = str(attempt_type or 'free').strip().lower()
        if attempt_kind not in {'free', 'paid'}:
            attempt_kind = 'free'

        if inviter_id == target_id:
            return {'ok': False, 'error': 'self_duel'}

        now_dt = datetime.now(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)
        day_key = self._duel_day_key(now_dt)
        invite_expires_at = now_dt + timedelta(seconds=max(15, int(invite_timeout_seconds or 60)))
        invite_expires_iso = self._to_utc_iso(invite_expires_at)

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT id
                FROM duels
                WHERE status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                LIMIT 1
                ''',
                (inviter_id, inviter_id),
            )
            inviter_active = cursor.fetchone()
            if inviter_active:
                return {'ok': False, 'error': 'inviter_has_active_duel'}

            cursor.execute(
                '''
                SELECT id
                FROM duels
                WHERE status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                LIMIT 1
                ''',
                (target_id, target_id),
            )
            target_active = cursor.fetchone()
            if target_active:
                return {'ok': False, 'error': 'target_has_active_duel'}

            attempts_left_after = None
            if attempt_kind == 'free':
                cursor.execute(
                    '''
                    SELECT used_invites
                    FROM duel_daily_attempts
                    WHERE user_id = ? AND day_key = ?
                    LIMIT 1
                    ''',
                    (inviter_id, day_key),
                )
                attempt_row = cursor.fetchone()
                used = int((attempt_row[0] if attempt_row else 0) or 0)
                used = max(0, used)
                if used >= int(free_limit):
                    return {'ok': False, 'error': 'no_free_attempts', 'left': 0, 'used': used}

                new_used = used + 1
                if attempt_row:
                    cursor.execute(
                        '''
                        UPDATE duel_daily_attempts
                        SET used_invites = ?,
                            updated_at = ?
                        WHERE user_id = ? AND day_key = ?
                        ''',
                        (new_used, now_iso, inviter_id, day_key),
                    )
                else:
                    cursor.execute(
                        '''
                        INSERT INTO duel_daily_attempts (user_id, day_key, used_invites, updated_at)
                        VALUES (?, ?, ?, ?)
                        ''',
                        (inviter_id, day_key, new_used, now_iso),
                    )
                attempts_left_after = max(0, int(free_limit) - new_used)

            normalized_inviter_username = self._normalize_duel_username(inviter_username)
            normalized_target_username = self._normalize_duel_username(target_username)

            cursor.execute(
                '''
                INSERT INTO duels (
                    chat_id,
                    inviter_id,
                    target_id,
                    inviter_username,
                    target_username,
                    status,
                    attempt_type,
                    attempt_day_key,
                    invite_expires_at,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
                RETURNING *
                ''',
                (
                    chat_id,
                    inviter_id,
                    target_id,
                    normalized_inviter_username,
                    normalized_target_username,
                    attempt_kind,
                    day_key if attempt_kind == 'free' else None,
                    invite_expires_iso,
                    now_iso,
                    now_iso,
                ),
            )
            duel_row = cursor.fetchone()
            if not duel_row:
                conn.rollback()
                return {'ok': False, 'error': 'duel_create_failed'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, duel_row))
            conn.commit()

        return {
            'ok': True,
            'duel': duel,
            'attempts_left_after': attempts_left_after,
        }

    def accept_duel_invitation(self, duel_id: int, target_user_id: int) -> Dict[str, Any]:
        """Принять приглашение в дуэль (только приглашённый пользователь)."""
        self._ensure_duel_tables()
        self.expire_pending_duels()
        now_dt = datetime.now(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if int(duel.get('target_id') or 0) != int(target_user_id):
                return {'ok': False, 'error': 'not_target'}

            status = str(duel.get('status') or '')
            if status != 'pending':
                return {'ok': False, 'error': 'not_pending', 'duel': duel}

            expires_at = self._parse_utc_datetime(duel.get('invite_expires_at'))
            if expires_at and expires_at <= now_dt:
                expired_result = self.expire_duel_invitation_by_id(int(duel_id), now=now_dt)
                return {
                    'ok': False,
                    'error': 'expired',
                    'duel': expired_result.get('duel') if isinstance(expired_result, dict) else duel,
                }

            inviter_id = int(duel.get('inviter_id') or 0)
            target_id = int(duel.get('target_id') or 0)

            cursor.execute(
                '''
                SELECT id
                FROM duels
                WHERE id <> ?
                  AND status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                LIMIT 1
                ''',
                (int(duel_id), inviter_id, inviter_id),
            )
            if cursor.fetchone():
                return {'ok': False, 'error': 'inviter_has_active_duel'}

            cursor.execute(
                '''
                SELECT id
                FROM duels
                WHERE id <> ?
                  AND status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                LIMIT 1
                ''',
                (int(duel_id), target_id, target_id),
            )
            if cursor.fetchone():
                return {'ok': False, 'error': 'target_has_active_duel'}

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'active',
                    accepted_at = ?,
                    updated_at = ?
                WHERE id = ? AND status = 'pending'
                ''',
                (now_iso, now_iso, int(duel_id)),
            )
            if int(getattr(cursor, 'rowcount', 0) or 0) == 0:
                conn.rollback()
                return {'ok': False, 'error': 'not_pending'}

            conn.commit()

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            updated_row = cursor.fetchone()
            if not updated_row:
                return {'ok': False, 'error': 'duel_not_found'}
            updated_columns = [description[0] for description in cursor.description]
            updated_duel = dict(zip(updated_columns, updated_row))

        return {'ok': True, 'duel': updated_duel}

    def decline_duel_invitation(self, duel_id: int, target_user_id: int) -> Dict[str, Any]:
        """Отклонить приглашение в дуэль (только приглашённый пользователь)."""
        self._ensure_duel_tables()
        self.expire_pending_duels()
        now_dt = datetime.now(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if int(duel.get('target_id') or 0) != int(target_user_id):
                return {'ok': False, 'error': 'not_target'}

            if str(duel.get('status') or '') != 'pending':
                return {'ok': False, 'error': 'not_pending', 'duel': duel}

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'declined',
                    finished_at = ?,
                    updated_at = ?
                WHERE id = ?
                ''',
                (now_iso, now_iso, int(duel_id)),
            )
            conn.commit()

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            updated_row = cursor.fetchone()
            if not updated_row:
                return {'ok': False, 'error': 'duel_not_found'}
            updated_columns = [description[0] for description in cursor.description]
            updated_duel = dict(zip(updated_columns, updated_row))

        return {'ok': True, 'duel': updated_duel}

    def cancel_duel_for_user(self, user_id: int, chat_id: Optional[int] = None) -> Dict[str, Any]:
        """Отменить активную/ожидающую дуэль по команде участника."""
        self._ensure_duel_tables()
        self.expire_pending_duels()
        now_dt = datetime.now(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        normalized_user_id = int(user_id)
        normalized_chat_id = int(chat_id) if chat_id is not None else None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM duels
                WHERE status IN ('pending', 'active')
                  AND (inviter_id = ? OR target_id = ?)
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (normalized_user_id, normalized_user_id),
            )
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            duel_chat_id = int(duel.get('chat_id') or 0)
            if normalized_chat_id is not None and duel_chat_id != normalized_chat_id:
                return {'ok': False, 'error': 'duel_in_other_chat', 'duel': duel}

            inviter_id = int(duel.get('inviter_id') or 0)
            target_id = int(duel.get('target_id') or 0)
            if normalized_user_id not in {inviter_id, target_id}:
                return {'ok': False, 'error': 'not_participant', 'duel': duel}

            inviter_done = duel.get('inviter_weight') is not None
            target_done = duel.get('target_weight') is not None
            refunded_flag = int(duel.get('free_attempt_refunded') or 0)
            attempt_type = str(duel.get('attempt_type') or '')
            attempt_day_key = str(duel.get('attempt_day_key') or '').strip()
            refunded_now = False

            if (
                attempt_type == 'free'
                and refunded_flag == 0
                and attempt_day_key
                and not inviter_done
                and not target_done
            ):
                cursor.execute(
                    '''
                    UPDATE duel_daily_attempts
                    SET used_invites = CASE WHEN used_invites > 0 THEN used_invites - 1 ELSE 0 END,
                        updated_at = ?
                    WHERE user_id = ? AND day_key = ?
                    ''',
                    (now_iso, inviter_id, attempt_day_key),
                )
                refunded_flag = 1
                refunded_now = True

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'cancelled',
                    finished_at = ?,
                    free_attempt_refunded = ?,
                    updated_at = ?
                WHERE id = ? AND status IN ('pending', 'active')
                ''',
                (now_iso, refunded_flag, now_iso, int(duel.get('id') or 0)),
            )

            if int(getattr(cursor, 'rowcount', 0) or 0) == 0:
                conn.rollback()
                return {'ok': False, 'error': 'not_pending_or_active', 'duel': duel}

            conn.commit()

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel.get('id') or 0),))
            updated_row = cursor.fetchone()
            if not updated_row:
                return {'ok': False, 'error': 'duel_not_found'}
            updated_columns = [description[0] for description in cursor.description]
            updated_duel = dict(zip(updated_columns, updated_row))

        return {
            'ok': True,
            'duel': updated_duel,
            'refunded': bool(refunded_now),
            'inviter_done': bool(inviter_done),
            'target_done': bool(target_done),
        }

    def record_duel_catch(
        self,
        duel_id: int,
        user_id: int,
        fish_name: str,
        weight: float,
        length: float,
        catch_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Зафиксировать улов участника дуэли и, если оба походили, завершить дуэль."""
        self._ensure_duel_tables()
        now_dt = datetime.now(timezone.utc)
        now_iso = self._to_utc_iso(now_dt)

        try:
            normalized_weight = float(weight)
        except (TypeError, ValueError):
            normalized_weight = 0.0
        try:
            normalized_length = float(length)
        except (TypeError, ValueError):
            normalized_length = 0.0

        normalized_fish_name = str(fish_name or '').strip() or 'Неизвестная рыба'
        normalized_catch_id = int(catch_id) if catch_id is not None else None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'error': 'duel_not_found'}

            columns = [description[0] for description in cursor.description]
            duel = dict(zip(columns, row))

            if str(duel.get('status') or '') != 'active':
                return {'ok': False, 'error': 'duel_not_active', 'duel': duel}

            inviter_id = int(duel.get('inviter_id') or 0)
            target_id = int(duel.get('target_id') or 0)

            if int(user_id) == inviter_id:
                if duel.get('inviter_weight') is not None:
                    return {'ok': False, 'error': 'already_submitted', 'duel': duel}
                cursor.execute(
                    '''
                    UPDATE duels
                    SET inviter_catch_id = ?,
                        inviter_fish_name = ?,
                        inviter_weight = ?,
                        inviter_length = ?,
                        updated_at = ?
                    WHERE id = ?
                    ''',
                    (normalized_catch_id, normalized_fish_name, normalized_weight, normalized_length, now_iso, int(duel_id)),
                )
            elif int(user_id) == target_id:
                if duel.get('target_weight') is not None:
                    return {'ok': False, 'error': 'already_submitted', 'duel': duel}
                cursor.execute(
                    '''
                    UPDATE duels
                    SET target_catch_id = ?,
                        target_fish_name = ?,
                        target_weight = ?,
                        target_length = ?,
                        updated_at = ?
                    WHERE id = ?
                    ''',
                    (normalized_catch_id, normalized_fish_name, normalized_weight, normalized_length, now_iso, int(duel_id)),
                )
            else:
                return {'ok': False, 'error': 'not_participant', 'duel': duel}

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            updated_row = cursor.fetchone()
            if not updated_row:
                conn.rollback()
                return {'ok': False, 'error': 'duel_not_found'}
            updated_columns = [description[0] for description in cursor.description]
            updated_duel = dict(zip(updated_columns, updated_row))

            inviter_weight = updated_duel.get('inviter_weight')
            target_weight = updated_duel.get('target_weight')

            if inviter_weight is None or target_weight is None:
                conn.commit()
                return {'ok': True, 'completed': False, 'duel': updated_duel}

            inviter_weight_val = float(inviter_weight or 0)
            target_weight_val = float(target_weight or 0)
            inviter_length_val = float(updated_duel.get('inviter_length') or 0)
            target_length_val = float(updated_duel.get('target_length') or 0)

            winner_id: Optional[int] = None
            loser_id: Optional[int] = None
            draw = False

            if inviter_weight_val > target_weight_val:
                winner_id = inviter_id
                loser_id = target_id
            elif target_weight_val > inviter_weight_val:
                winner_id = target_id
                loser_id = inviter_id
            elif inviter_length_val > target_length_val:
                winner_id = inviter_id
                loser_id = target_id
            elif target_length_val > inviter_length_val:
                winner_id = target_id
                loser_id = inviter_id
            else:
                draw = True

            cursor.execute(
                '''
                UPDATE duels
                SET status = 'finished',
                    finished_at = ?,
                    winner_id = ?,
                    loser_id = ?,
                    updated_at = ?
                WHERE id = ?
                ''',
                (now_iso, winner_id, loser_id, now_iso, int(duel_id)),
            )

            cursor.execute('SELECT * FROM duels WHERE id = ? LIMIT 1', (int(duel_id),))
            final_row = cursor.fetchone()
            if not final_row:
                conn.rollback()
                return {'ok': False, 'error': 'duel_not_found'}
            final_columns = [description[0] for description in cursor.description]
            final_duel = dict(zip(final_columns, final_row))
            conn.commit()

        return {
            'ok': True,
            'completed': True,
            'draw': draw,
            'duel': final_duel,
        }

    def get_latest_unsold_catch(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Последний непроданный улов пользователя (сначала в текущем чате)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, user_id, chat_id, fish_name, weight, length, location, sold, caught_at
                FROM caught_fish
                WHERE user_id = ? AND sold = 0 AND chat_id = ?
                ORDER BY id DESC
                LIMIT 1
                ''',
                (int(user_id), int(chat_id)),
            )
            row = cursor.fetchone()
            if not row:
                cursor.execute(
                    '''
                    SELECT id, user_id, chat_id, fish_name, weight, length, location, sold, caught_at
                    FROM caught_fish
                    WHERE user_id = ? AND sold = 0
                    ORDER BY id DESC
                    LIMIT 1
                    ''',
                    (int(user_id),),
                )
                row = cursor.fetchone()

            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    def move_caught_fish_to_user(self, fish_id: int, from_user_id: int, to_user_id: int, to_chat_id: int) -> bool:
        """Передать конкретный улов другому пользователю."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE caught_fish
                SET user_id = ?,
                    chat_id = ?,
                    sold = 0
                WHERE id = ? AND user_id = ?
                ''',
                (int(to_user_id), int(to_chat_id), int(fish_id), int(from_user_id)),
            )
            moved = int(getattr(cursor, 'rowcount', 0) or 0) > 0
            conn.commit()
            return moved

    def _ensure_boat_tables(self):
        """Создать таблицы для лодок и участников лодки, если их еще нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Таблица лодок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boats (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    capacity INTEGER NOT NULL,
                    max_weight REAL NOT NULL,
                    current_weight REAL DEFAULT 0,
                    durability INTEGER DEFAULT 0,
                    max_durability INTEGER DEFAULT 0,
                    cooldown_until TIMESTAMP,
                    is_active INTEGER DEFAULT 0
                )
            ''')
            # Таблица участников лодки
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boat_members (
                    id INTEGER PRIMARY KEY,
                    boat_id INTEGER NOT NULL,
                    user_id BIGINT NOT NULL,
                    is_owner INTEGER DEFAULT 0,
                    FOREIGN KEY(boat_id) REFERENCES boats(id)
                )
            ''')
            conn.commit()

    def _ensure_boat_catch_table(self):
        """Создать таблицу общего улова лодки, если её еще нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS boat_catch (
                    id INTEGER PRIMARY KEY,
                    boat_id INTEGER NOT NULL,
                    user_id BIGINT NOT NULL,
                    fish_id BIGINT,
                    item_name TEXT NOT NULL,
                    weight REAL NOT NULL DEFAULT 0,
                    chat_id BIGINT,
                    location TEXT,
                    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(boat_id) REFERENCES boats(id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boat_catch_boat
                ON boat_catch (boat_id, id DESC)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_boat_catch_user
                ON boat_catch (user_id, boat_id)
            ''')
            # Ensure fish_id is nullable: older Postgres schemas may have NOT NULL
            try:
                cursor.execute('''
                    DO $$
                    BEGIN
                        ALTER TABLE boat_catch ALTER COLUMN fish_id DROP NOT NULL;
                    EXCEPTION
                        WHEN OTHERS THEN
                            NULL;
                    END $$;
                ''')
            except Exception:
                pass
            conn.commit()

    def add_fish_to_boat(
        self,
        user_id: int,
        fish_id: int,
        weight: float,
        chat_id: int,
        location: Optional[str] = None,
    ) -> bool:
        """Добавить рыбу в общий садок активной лодки."""
        self._ensure_boat_tables()
        self._ensure_boat_catch_table()
        boat = self.get_active_boat_by_user(user_id)
        if not boat:
            return False

        item_name = None
        try:
            fish = self.get_fish_by_id(fish_id)
            if fish:
                item_name = str(fish.get('name') or '')
        except Exception:
            item_name = None

        if not item_name:
            item_name = f"fish_{int(fish_id)}"

        try:
            current_weight = float(boat.get('current_weight') or 0.0)
        except Exception:
            current_weight = 0.0

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO boat_catch (boat_id, user_id, fish_id, item_name, weight, chat_id, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(boat.get('id') or 0),
                    int(user_id),
                    int(fish_id),
                    item_name,
                    float(weight or 0.0),
                    int(chat_id) if chat_id is not None else None,
                    location,
                ),
            )
            cursor.execute(
                'UPDATE boats SET current_weight = ? WHERE id = ?',
                (current_weight + float(weight or 0.0), int(boat.get('id') or 0)),
            )
            conn.commit()
            return True

    def add_boat_catch(
        self,
        boat_id: int,
        item_name: str,
        weight: float,
        chat_id: int,
        location: Optional[str] = None,
        user_id: Optional[int] = None,
        fish_id: Optional[int] = None,
    ) -> bool:
        """Добавить запись в общий садок конкретной лодки."""
        self._ensure_boat_tables()
        self._ensure_boat_catch_table()

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, user_id, current_weight FROM boats WHERE id = ?', (int(boat_id),))
            boat_row = cursor.fetchone()
            if not boat_row:
                return False

            owner_id = int(boat_row[1]) if boat_row[1] is not None else int(user_id or 0)
            author_id = int(user_id) if user_id is not None else owner_id
            current_weight = float(boat_row[2] or 0.0)

            cursor.execute(
                '''
                INSERT INTO boat_catch (boat_id, user_id, fish_id, item_name, weight, chat_id, location)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    int(boat_id),
                    author_id,
                    int(fish_id) if fish_id is not None else None,
                    str(item_name or '').strip() or 'Неизвестный улов',
                    float(weight or 0.0),
                    int(chat_id) if chat_id is not None else None,
                    location,
                ),
            )
            cursor.execute(
                'UPDATE boats SET current_weight = ? WHERE id = ?',
                (current_weight + float(weight or 0.0), int(boat_id)),
            )
            conn.commit()
            return True

    def can_start_boat_trip(self, user_id: int) -> tuple[bool, int]:
        """Проверка, можно ли начать плавание: учитывает активность и КД после возврата."""
        self._ensure_boat_tables()
        boat = self.get_user_boat(user_id)
        if not boat:
            return True, 0

        if int(boat.get('is_active') or 0) == 1:
            return False, 0

        now = datetime.now(timezone.utc)
        cooldown_until = None

        raw_boat_cd = boat.get('cooldown_until')
        if raw_boat_cd:
            try:
                cooldown_until = datetime.fromisoformat(str(raw_boat_cd).replace('Z', '+00:00'))
                if cooldown_until.tzinfo is None:
                    cooldown_until = cooldown_until.replace(tzinfo=timezone.utc)
            except Exception:
                cooldown_until = None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT last_boat_return_time
                FROM players
                WHERE user_id = ?
                  AND last_boat_return_time IS NOT NULL
                ORDER BY last_boat_return_time DESC
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()

        if row and row[0]:
            try:
                returned_at = datetime.fromisoformat(str(row[0]).replace('Z', '+00:00'))
                if returned_at.tzinfo is None:
                    returned_at = returned_at.replace(tzinfo=timezone.utc)
                players_cd_until = returned_at + timedelta(hours=12)
                if cooldown_until is None or players_cd_until > cooldown_until:
                    cooldown_until = players_cd_until
            except Exception:
                pass

        if cooldown_until and cooldown_until > now:
            remaining = int((cooldown_until - now).total_seconds())
            return False, max(1, remaining)

        return True, 0

    def start_boat_trip(self, user_id: int) -> bool:
        """Запустить плавание: активирует лодку пользователя."""
        self._ensure_boat_tables()
        can_start, _ = self.can_start_boat_trip(user_id)
        if not can_start:
            return False

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id
                FROM boats
                WHERE user_id = ?
                ORDER BY CASE WHEN type = 'paid' THEN 0 ELSE 1 END, id DESC
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()

            if row:
                boat_id = int(row[0])
            else:
                cursor.execute(
                    '''
                    INSERT INTO boats (user_id, type, name, capacity, max_weight, durability, max_durability, is_active)
                    VALUES (?, 'free', 'Бесплатная лодка', 1, 500, 100, 100, 0)
                    RETURNING id
                    ''',
                    (int(user_id),),
                )
                boat_id = int(cursor.fetchone()[0])

            cursor.execute(
                'INSERT INTO boat_members (boat_id, user_id, is_owner) VALUES (?, ?, 1) ON CONFLICT DO NOTHING',
                (boat_id, int(user_id)),
            )
            cursor.execute('UPDATE boats SET is_active = 1 WHERE id = ?', (boat_id,))
            conn.commit()
            return True

    def check_boat_weight_warning(self, user_id: int) -> Optional[float]:
        """Сколько веса осталось у активной лодки пользователя."""
        boat = self.get_active_boat_by_user(user_id)
        if not boat:
            return None
        try:
            left = float(boat.get('max_weight') or 0.0) - float(boat.get('current_weight') or 0.0)
            return left
        except Exception:
            return None

    def check_boat_crash(self, user_id: int) -> bool:
        """Проверить перегруз лодки и завершить плавание при крушении."""
        boat = self.get_active_boat_by_user(user_id)
        if not boat:
            return False

        try:
            overloaded = float(boat.get('current_weight') or 0.0) > float(boat.get('max_weight') or 0.0)
        except Exception:
            overloaded = False

        if not overloaded:
            return False

        owner_id = int(boat.get('user_id') or user_id)
        cooldown_until = (datetime.now(timezone.utc) + timedelta(hours=12)).isoformat()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM boat_catch WHERE boat_id = ?', (int(boat.get('id') or 0),))
            cursor.execute('DELETE FROM boat_members WHERE boat_id = ? AND is_owner = 0', (int(boat.get('id') or 0),))
            cursor.execute(
                '''
                UPDATE boats
                SET is_active = 0,
                    current_weight = 0,
                    durability = 0,
                    cooldown_until = ?
                WHERE id = ?
                ''',
                (cooldown_until, int(boat.get('id') or 0)),
            )
            cursor.execute(
                'UPDATE players SET last_boat_return_time = ? WHERE user_id = ?',
                (datetime.now(timezone.utc).isoformat(), owner_id),
            )
            conn.commit()
        return True

    def sink_active_boat_by_storm(self, user_id: int, cooldown_hours: int = 18) -> Dict[str, Any]:
        """Потопить активную лодку (шторм): завершить плавание и обнулить улов."""
        boat = self.get_active_boat_by_user(user_id)
        if not boat:
            return {'applied': False}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*), COALESCE(SUM(weight), 0) FROM boat_catch WHERE boat_id = ?', (int(boat.get('id') or 0),))
            row = cursor.fetchone()
            lost_count = int(row[0] or 0) if row else 0
            lost_weight = float(row[1] or 0.0) if row else 0.0

            cursor.execute('DELETE FROM boat_catch WHERE boat_id = ?', (int(boat.get('id') or 0),))
            cursor.execute('DELETE FROM boat_members WHERE boat_id = ? AND is_owner = 0', (int(boat.get('id') or 0),))

            cooldown_until_dt = datetime.now(timezone.utc) + timedelta(hours=max(1, int(cooldown_hours or 18)))
            cooldown_until = cooldown_until_dt.isoformat()
            cursor.execute(
                '''
                UPDATE boats
                SET is_active = 0,
                    current_weight = 0,
                    cooldown_until = ?
                WHERE id = ?
                ''',
                (cooldown_until, int(boat.get('id') or 0)),
            )
            cursor.execute(
                'UPDATE players SET last_boat_return_time = ? WHERE user_id = ?',
                (datetime.now(timezone.utc).isoformat(), int(boat.get('user_id') or user_id)),
            )
            conn.commit()

        return {
            'applied': True,
            'boat_id': int(boat.get('id') or 0),
            'lost_count': lost_count,
            'lost_weight': lost_weight,
            'cooldown_until': cooldown_until,
        }

    def __init__(self):
        self._pool = None
        self._db_url = None

    def _get_db_url(self):
        if self._db_url:
            return self._db_url
        
        url = os.getenv('DATABASE_URL')
        if not url:
            # Fallback to individual env vars
            host = os.getenv('DB_HOST', 'localhost')
            port = os.getenv('DB_PORT', '5432')
            name = os.getenv('DB_NAME', 'fishbot')
            user = os.getenv('DB_USER', 'postgres')
            pw = os.getenv('DB_PASSWORD', 'password')
            url = f"postgresql://{user}:{pw}@{host}:{port}/{name}"
        
        self._db_url = url
        return url

    def _connect(self):
        if self._pool is None:
            import psycopg2.pool
            try:
                self._pool = psycopg2.pool.ThreadedConnectionPool(
                    1, 20, 
                    dsn=self._get_db_url(),
                    connect_timeout=5,
                    options='-c statement_timeout=30000'
                )
                logger.info("Database connection pool initialized")
            except Exception as e:
                logger.error(f"Failed to initialize connection pool: {e}")
                # Fallback to direct connection if pool fails
                raw_conn = psycopg2.connect(self._get_db_url(), connect_timeout=5)
                return PostgresConnWrapper(raw_conn)

        try:
            raw_conn = self._pool.getconn()
            # Wrap the connection to return it to the pool on __exit__
            class PooledConnectionWrapper(PostgresConnWrapper):
                def __init__(self, conn, pool):
                    super().__init__(conn)
                    self._pool_ref = pool
                
                def close(self):
                    # Instead of closing the raw connection, return it to the pool
                    if self._pool_ref and self._conn:
                        conn = self._conn
                        pool = self._pool_ref
                        self._conn = None
                        self._pool_ref = None
                        try:
                            pool.putconn(conn)
                        except Exception:
                            pass

                def __exit__(self, exc_type, exc, tb):
                    # Commit/rollback and then return to pool without closing raw connection.
                    try:
                        if exc_type:
                            self._conn.rollback()
                        else:
                            self._conn.commit()
                    except Exception:
                        pass
                    self.close()
                    return False

            return PooledConnectionWrapper(raw_conn, self._pool)
        except Exception as e:
            logger.error(f"Error getting connection from pool: {e}")
            import psycopg2
            raw_conn = psycopg2.connect(self._get_db_url(), connect_timeout=5)
            return PostgresConnWrapper(raw_conn)

    def _get_temp_rod_uses(self, rod_name: str) -> Optional[int]:
        rod_range = TEMP_ROD_RANGES.get(rod_name)
        if not rod_range:
            return None
        return random.randint(rod_range[0], rod_range[1])
    
    def init_db(self):
        """Инициализация базы данных"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Таблица системных флагов (для ивентов и настроек)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_flags (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            ''')

            # Таблица игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS players (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT NOT NULL,
                    coins INTEGER DEFAULT 100,
                    stars INTEGER DEFAULT 0,
                    tickets INTEGER DEFAULT 0,
                    diamonds INTEGER DEFAULT 0,
                    xp INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 0,
                    current_rod TEXT DEFAULT 'Бамбуковая удочка',
                    current_bait TEXT DEFAULT 'Черви',
                    current_location TEXT DEFAULT 'Городской пруд',
                    last_fish_time TEXT,
                    last_population_action_time TEXT,
                    last_boat_return_time TEXT,
                    last_dynamite_use_time TEXT,
                    dynamite_ban_until TEXT,
                    dynamite_upgrade_level INTEGER DEFAULT 1,
                    is_banned INTEGER DEFAULT 0,
                    ban_until TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица удочек
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS rods (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    price INTEGER NOT NULL,
                    durability INTEGER NOT NULL,
                    max_durability INTEGER NOT NULL,
                    fish_bonus INTEGER DEFAULT 0,
                    max_weight INTEGER DEFAULT 999
                )
            ''')
            
            # Таблица состояния удочек игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_rods (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    rod_name TEXT NOT NULL,
                    current_durability INTEGER NOT NULL,
                    max_durability INTEGER NOT NULL,
                    last_repair_time TEXT,
                    recovery_start_time TEXT,
                    FOREIGN KEY (user_id) REFERENCES players (user_id),
                    FOREIGN KEY (rod_name) REFERENCES rods (name),
                    UNIQUE(user_id, rod_name)
                )
            ''')
            
            # Таблица рыбы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS fish (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    rarity TEXT NOT NULL,
                    min_weight REAL NOT NULL,
                    max_weight REAL NOT NULL,
                    min_length REAL NOT NULL,
                    max_length REAL NOT NULL,
                    price INTEGER NOT NULL,
                    locations TEXT NOT NULL,
                    seasons TEXT NOT NULL,
                    suitable_baits TEXT DEFAULT 'Все',
                    max_rod_weight INTEGER DEFAULT 999,
                    required_level INTEGER DEFAULT 0,
                    sticker_id TEXT
                )
            ''')
            
            # Таблица пойманной рыбы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS caught_fish (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT DEFAULT 0,
                    fish_name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    length REAL DEFAULT 0,
                    location TEXT NOT NULL,
                    sold INTEGER DEFAULT 0,
                    caught_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    sold_at TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')
            # Ensure `chat_id` column exists
            try:
                cursor.execute("ALTER TABLE caught_fish ADD COLUMN IF NOT EXISTS chat_id BIGINT DEFAULT 0")
            except Exception:
                try:
                    cursor.execute("ALTER TABLE caught_fish ADD COLUMN chat_id BIGINT DEFAULT 0")
                except:
                    pass

            # Таблица трофеев игроков (отдельно от обычного инвентаря/лавки)
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_caught_fish_user_chat_sold
                ON caught_fish (user_id, chat_id, sold)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_caught_fish_user_sold
                ON caught_fish (user_id, sold)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_trophies (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    fish_name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    length REAL DEFAULT 0,
                    location TEXT,
                    image_file TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_trophies_user
                ON player_trophies (user_id)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_trophies_active
                ON player_trophies (user_id, is_active)
            ''')

            # Таблица выдачи билетов: одна запись на один билет.
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_awards (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_ref TEXT,
                    amount INTEGER NOT NULL DEFAULT 0,
                    jackpot_amount INTEGER NOT NULL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ticket_awards_user_created
                ON ticket_awards (user_id, created_at)
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ticket_items (
                    id SERIAL PRIMARY KEY,
                    ticket_code TEXT UNIQUE,
                    award_id INTEGER NOT NULL,
                    user_id BIGINT NOT NULL,
                    username TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_ref TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (award_id) REFERENCES ticket_awards (id),
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ticket_items_user_created
                ON ticket_items (user_id, created_at)
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_ticket_items_code
                ON ticket_items (ticket_code)
            ''')

            # Backfill legacy `players.tickets` balances into the new per-ticket ledger once.
            try:
                cursor.execute('SELECT COUNT(*) FROM ticket_items')
                ticket_items_count = int(cursor.fetchone()[0] or 0)
            except Exception:
                ticket_items_count = 0

            if ticket_items_count == 0:
                cursor.execute(
                    '''
                    SELECT user_id, COALESCE(MAX(username), 'Неизвестно') AS username, MAX(COALESCE(tickets, 0)) AS tickets
                    FROM players
                    GROUP BY user_id
                    HAVING MAX(COALESCE(tickets, 0)) > 0
                    ORDER BY user_id ASC
                    '''
                )
                legacy_ticket_rows = cursor.fetchall() or []
                for user_id, username, tickets in legacy_ticket_rows:
                    tickets_count = int(tickets or 0)
                    if tickets_count <= 0:
                        continue
                    cursor.execute(
                        '''
                        INSERT INTO ticket_awards (user_id, username, source_type, source_ref, amount, jackpot_amount)
                        VALUES (?, ?, ?, ?, ?, ?)
                        RETURNING id
                        ''',
                        (int(user_id), str(username or 'Неизвестно'), 'legacy_backfill', 'players.tickets', tickets_count, 0),
                    )
                    award_row = cursor.fetchone()
                    award_id = int(award_row[0]) if award_row else None
                    if not award_id:
                        continue
                    for ticket_index in range(1, tickets_count + 1):
                        ticket_code = f"b{award_id}-{ticket_index}"
                        cursor.execute(
                            '''
                            INSERT INTO ticket_items (ticket_code, award_id, user_id, username, source_type, source_ref)
                            VALUES (?, ?, ?, ?, ?, ?)
                            ''',
                            (ticket_code, award_id, int(user_id), str(username or 'Неизвестно'), 'legacy_backfill', 'players.tickets'),
                        )
            
            # Таблица локаций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS locations (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    fish_population INTEGER NOT NULL,
                    current_players INTEGER DEFAULT 0,
                    max_players INTEGER NOT NULL
                )
            ''')
            
            # Таблица наживок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS baits (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    price INTEGER NOT NULL,
                    fish_bonus INTEGER DEFAULT 0,
                    suitable_for TEXT DEFAULT 'Все'
                )
            ''')
            
            # Таблица мусора
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS trash (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    weight REAL NOT NULL,
                    price INTEGER NOT NULL,
                    locations TEXT NOT NULL,
                    sticker_id TEXT
                )
            ''')
            
            # Таблица инвентаря наживок
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_baits (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    bait_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 0,
                    FOREIGN KEY (user_id) REFERENCES players (user_id),
                    FOREIGN KEY (bait_name) REFERENCES baits (name),
                    UNIQUE(user_id, bait_name)
                )
            ''')
            
            # Таблица транзакций Telegram Stars
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS star_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    telegram_payment_charge_id TEXT NOT NULL UNIQUE,
                    total_amount INTEGER NOT NULL,
                    chat_id INTEGER,
                    chat_title TEXT,
                    refund_status TEXT DEFAULT 'none',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES players (user_id)
                )
            ''')

            # Таблица погоды по локациям
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS weather (
                    id INTEGER PRIMARY KEY,
                    location TEXT UNIQUE NOT NULL,
                    condition TEXT DEFAULT 'Ясно',
                    temperature INTEGER DEFAULT 20,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (location) REFERENCES locations (name)
                )
            ''')
            
            # Таблица сетей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS nets (
                    id INTEGER PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    price INTEGER NOT NULL,
                    fish_count INTEGER NOT NULL,
                    cooldown_hours INTEGER NOT NULL,
                    max_uses INTEGER DEFAULT -1,
                    description TEXT
                )
            ''')
            
            # Таблица сетей игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_nets (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    net_name TEXT NOT NULL,
                    uses_left INTEGER DEFAULT -1,
                    last_use_time TEXT,
                    FOREIGN KEY (user_id) REFERENCES players (user_id),
                    FOREIGN KEY (net_name) REFERENCES nets (name),
                    UNIQUE(user_id, net_name)
                )
            ''')

            # Таблица одежды игроков (перманентные баффы)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_clothing (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    item_key TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    bonus_percent REAL NOT NULL DEFAULT 0,
                    purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, item_key)
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_clothing_user
                ON player_clothing (user_id)
            ''')
            cursor.execute('''
                CREATE UNIQUE INDEX IF NOT EXISTS player_clothing_user_item_key
                ON player_clothing (user_id, item_key)
            ''')
            
            # Таблица настроек чатов для реферальной системы
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chat_configs (
                    chat_id INTEGER PRIMARY KEY,
                    admin_user_id INTEGER NOT NULL,
                    is_configured INTEGER DEFAULT 1,
                    admin_ref_link TEXT,
                    chat_invite_link TEXT,
                    chat_title TEXT,
                    stars_total INTEGER DEFAULT 0,
                    configured_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица реф-ссылок пользователей (из Telegram Affiliate)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS user_ref_links (
                    user_id INTEGER PRIMARY KEY,
                    ref_link TEXT NOT NULL,
                    chat_invite_link TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Доступ к реф-статистике по чатам (кому какой чат разрешено смотреть)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ref_access (
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')

            # История подтвержденных выводов звёзд
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS star_withdrawals (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT,
                    amount INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Таблица системных флагов/миграций
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_flags (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')

            # Таблица сокровищ игроков
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_treasures (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT DEFAULT -1,
                    treasure_name TEXT NOT NULL,
                    quantity INTEGER DEFAULT 1,
                    obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id, treasure_name)
                )
            ''')

            # RAF-ивенты (розыгрыши по редкости улова)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raf_events (
                    id SERIAL PRIMARY KEY,
                    creator_user_id BIGINT NOT NULL,
                    creator_username TEXT,
                    title TEXT NOT NULL,
                    target_chat_id BIGINT NOT NULL,
                    source_message_link TEXT,
                    duration_hours INTEGER,
                    status TEXT DEFAULT 'draft',
                    payment_charge_id TEXT,
                    starts_at TIMESTAMP,
                    ends_at TIMESTAMP,
                    activated_at TIMESTAMP,
                    start_message_id BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS raf_event_prizes (
                    id SERIAL PRIMARY KEY,
                    event_id BIGINT NOT NULL,
                    prize_order INTEGER DEFAULT 1,
                    prize_text TEXT NOT NULL,
                    rarity_key TEXT NOT NULL,
                    chance_percent REAL NOT NULL,
                    is_claimed INTEGER DEFAULT 0,
                    winner_user_id BIGINT,
                    winner_username TEXT,
                    won_at TIMESTAMP,
                    won_location TEXT,
                    trigger_source TEXT,
                    FOREIGN KEY (event_id) REFERENCES raf_events(id)
                )
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_raf_events_chat_status
                ON raf_events (target_chat_id, status)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_raf_prizes_event_claimed
                ON raf_event_prizes (event_id, is_claimed)
            ''')
            
            # Initialize boat-related tables
            self._ensure_boat_tables()
            self._ensure_boat_catch_table()
            self._ensure_boat_invites_table()
            self._ensure_user_effects_table()
            self._ensure_antibot_captcha_table()
            self._ensure_duel_tables()
            self._ensure_extended_gameplay_tables()
            self._ensure_webapp_ui_tables()

            conn.commit()
        
        # Ensure integer PK columns have sequences/defaults (Postgres)
        try:
            ensure_all_serial_pks(conn)
        except Exception:
            logger.exception('ensure_all_serial_pks call failed during init_db')
            try:
                conn.rollback()
            except Exception:
                pass

        # Миграции - добавляем колонки если их нет
        self._run_migrations()
        
        # Заполняем начальными данными
        self._fill_default_data()
    
    def _run_migrations(self):
        """Выполнение миграций для обновления схемы БД"""
        with self._connect() as conn:
            cursor = conn.cursor()

            def get_columns(table_name: str):
                cursor.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
                    (table_name,)
                )
                return [r[0] for r in cursor.fetchall()]

            # Проверяем наличие колонок в таблице players (Postgres-friendly)
            columns = get_columns('players')

            if 'ref' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN ref INTEGER')
                conn.commit()

            if 'ref_link' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN ref_link TEXT')
                conn.commit()

            if 'chat_id' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN chat_id BIGINT')
                conn.commit()

            # Ensure chat_configs has columns for tracking title and total stars
            chat_conf_cols = get_columns('chat_configs')
            if 'stars_total' not in chat_conf_cols:
                try:
                    cursor.execute('ALTER TABLE chat_configs ADD COLUMN stars_total INTEGER DEFAULT 0')
                    conn.commit()
                except Exception:
                    pass
            if 'chat_title' not in chat_conf_cols:
                try:
                    cursor.execute('ALTER TABLE chat_configs ADD COLUMN chat_title TEXT')
                    conn.commit()
                except Exception:
                    pass

            if 'xp' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN xp INTEGER DEFAULT 0')
                conn.commit()

            if 'level' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN level INTEGER DEFAULT 0')
                conn.commit()

            # CRITICAL: Migrate players table to use composite primary key (user_id, chat_id)
            cursor.execute(
                """
                SELECT kcu.column_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_name = %s
                """,
                ('players',)
            )
            pk_cols = [r[0] for r in cursor.fetchall()]

            if pk_cols == ['user_id']:
                # Need to recreate table with composite key
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS players_new (
                        user_id BIGINT NOT NULL,
                        chat_id BIGINT NOT NULL,
                        username TEXT NOT NULL,
                        coins INTEGER DEFAULT 100,
                        stars INTEGER DEFAULT 0,
                        xp INTEGER DEFAULT 0,
                        level INTEGER DEFAULT 0,
                        current_rod TEXT DEFAULT 'Бамбуковая удочка',
                        current_bait TEXT DEFAULT 'Черви',
                        current_location TEXT DEFAULT 'Городской пруд',
                        last_fish_time TEXT,
                        is_banned INTEGER DEFAULT 0,
                        ban_until TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        ref INTEGER,
                        ref_link TEXT,
                        last_net_use_time TEXT,
                        PRIMARY KEY (user_id, chat_id)
                    )
                ''')

                # Copy data from old table, normalizing NULL chat_id to -1
                cursor.execute('''
                    INSERT INTO players_new (user_id, chat_id, username, coins, stars, xp, level, current_rod, current_bait, current_location, last_fish_time, is_banned, ban_until, created_at, ref, ref_link, last_net_use_time)
                    SELECT user_id, COALESCE(chat_id, -1), username, coins, stars, COALESCE(xp, 0), COALESCE(level, 0), current_rod, current_bait, current_location, last_fish_time, is_banned, ban_until, created_at, ref, ref_link, last_net_use_time
                    FROM players
                    ON CONFLICT (user_id, chat_id) DO NOTHING
                ''')

                # Attempt to replace the old players table only if nothing
                # references it via foreign key constraints. If other objects
                # depend on `players` skip the destructive replacement to
                # avoid dropping dependent objects and noisy stack traces.
                try:
                    # Check for any foreign-key constraints referencing players
                    cursor.execute(
                        "SELECT COUNT(*) FROM pg_constraint WHERE confrelid = (SELECT oid FROM pg_class WHERE relname = %s AND relnamespace = 'public'::regnamespace)",
                        ('players',)
                    )
                    # fetchone() returns a tuple like (count,); use the first value
                    ref_count_row = cursor.fetchone()
                    ref_count = ref_count_row[0] if ref_count_row else 0
                except Exception:
                    # Fallback: if we cannot reliably detect references, avoid DROP
                    ref_count = 1

                if ref_count:
                    logger.warning("Could not replace players table (dependent objects exist). Skipping composite-PK migration.")
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    try:
                        cursor.execute('DROP TABLE IF EXISTS players_new')
                        conn.commit()
                    except Exception:
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                else:
                    try:
                        cursor.execute('DROP TABLE players')
                        cursor.execute('ALTER TABLE players_new RENAME TO players')
                        conn.commit()
                    except Exception as e:
                        logger.warning("Could not replace players table (%s). Skipping composite-PK migration.", e)
                        try:
                            conn.rollback()
                        except Exception:
                            pass
                        try:
                            cursor.execute('DROP TABLE IF EXISTS players_new')
                            conn.commit()
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass

            # refresh columns list after potential schema change
            columns = get_columns('players')

            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_trophies (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    fish_name TEXT NOT NULL,
                    weight REAL NOT NULL,
                    length REAL DEFAULT 0,
                    location TEXT,
                    image_file TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_player_trophies_user_created
                ON player_trophies (user_id, created_at)
            ''')
            conn.commit()

            if 'last_net_use_time' not in columns:
                cursor.execute('ALTER TABLE players ADD COLUMN last_net_use_time TEXT')
                conn.commit()

            # Helper to add a column if missing
            def ensure_column(table: str, col: str, col_def: str):
                cols = get_columns(table)
                if col not in cols:
                    cursor.execute(f'ALTER TABLE {table} ADD COLUMN {col} {col_def}')
                    conn.commit()

            ensure_column('trash', 'sticker_id', 'TEXT')
            ensure_column('caught_fish', 'length', 'REAL DEFAULT 0')
            ensure_column('caught_fish', 'sold', 'INTEGER DEFAULT 0')
            ensure_column('caught_fish', 'sold_at', 'TIMESTAMP')
            ensure_column('fish', 'required_level', 'INTEGER DEFAULT 0')
            ensure_column('star_transactions', 'chat_id', 'INTEGER')
            ensure_column('star_transactions', 'chat_title', 'TEXT')
            ensure_column('player_rods', 'chat_id', 'INTEGER')
            ensure_column('player_nets', 'chat_id', 'INTEGER')
            ensure_column('chat_configs', 'admin_ref_link', 'TEXT')
            ensure_column('chat_configs', 'chat_invite_link', 'TEXT')
            ensure_column('user_ref_links', 'chat_invite_link', 'TEXT')
            ensure_column('caught_fish', 'chat_id', 'INTEGER')
            ensure_column('players', 'consecutive_casts_at_location', 'INTEGER DEFAULT 0')
            ensure_column('players', 'last_fishing_location', 'TEXT')
            ensure_column('players', 'population_penalty', 'REAL DEFAULT 0.0')
            ensure_column('players', 'penalty_recovery_casts', 'INTEGER DEFAULT 0')
            ensure_column('players', 'last_population_action_time', 'TEXT')
            ensure_column('players', 'consecutive_dynamite_at_location', 'INTEGER DEFAULT 0')
            ensure_column('players', 'last_dynamite_location', 'TEXT')
            ensure_column('players', 'dynamite_penalty', 'REAL DEFAULT 0.0')
            ensure_column('players', 'dynamite_recovery_explosions', 'INTEGER DEFAULT 0')
            ensure_column('players', 'last_dynamite_use_time', 'TEXT')
            ensure_column('players', 'last_boat_return_time', 'TEXT')
            ensure_column('players', 'diamonds', 'INTEGER DEFAULT 0')
            ensure_column('players', 'tickets', 'INTEGER DEFAULT 0')
            ensure_column('players', 'dynamite_ban_until', 'TEXT')
            ensure_column('players', 'dynamite_upgrade_level', 'INTEGER DEFAULT 1')
            ensure_column('raf_events', 'creator_username', 'TEXT')
            ensure_column('player_trophies', 'length', 'REAL DEFAULT 0')
            ensure_column('player_trophies', 'location', 'TEXT')
            ensure_column('player_trophies', 'image_file', 'TEXT')
            ensure_column('player_trophies', 'is_active', 'INTEGER DEFAULT 0')
            ensure_column('player_trophies', 'created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

            # Ensure unique index for ON CONFLICT targets that expect (user_id, chat_id)
            try:
                cols = get_columns('players')
                if 'chat_id' in cols:
                    cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS players_user_chat_unique ON players (user_id, chat_id)")
                    conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            # Ensure integer PK columns have a sequence/default on Postgres (e.g., rods.id)
            # Also ensure user/chat identifier columns are 64-bit on Postgres to avoid integer out of range
            def ensure_bigint_column(table_name: str, column_name: str):
                try:
                    cursor.execute(
                        "SELECT data_type FROM information_schema.columns WHERE table_name = %s AND column_name = %s AND table_schema = 'public'",
                        (table_name, column_name)
                    )
                    row = cursor.fetchone()
                    if row and row[0] != 'bigint':
                        try:
                            # Direct cast INTEGER -> BIGINT is always safe and lossless.
                            # Avoids the old '^[0-9]+$' regex which incorrectly converted
                            # negative Telegram group chat IDs (e.g. -1001234567890) to NULL.
                            cursor.execute(f'ALTER TABLE {table_name} ALTER COLUMN {column_name} TYPE BIGINT USING {column_name}::bigint')
                            conn.commit()
                        except Exception:
                            try:
                                conn.rollback()
                            except Exception:
                                pass
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            # Convert known user/chat id columns to BIGINT to support large Telegram IDs
            bigint_targets = [
                ('players', 'user_id'),
                ('players', 'chat_id'),
                ('player_rods', 'user_id'),
                ('player_rods', 'chat_id'),
                ('player_baits', 'user_id'),
                ('caught_fish', 'user_id'),
                ('caught_fish', 'chat_id'),
                ('player_nets', 'user_id'),
                ('player_nets', 'chat_id'),
                ('star_transactions', 'user_id'),
                ('star_transactions', 'chat_id'),
                ('chat_configs', 'chat_id'),
                ('chat_configs', 'admin_user_id'),
                ('user_ref_links', 'user_id'),
                ('player_trophies', 'user_id')
            ]
            for tbl, col in bigint_targets:
                ensure_bigint_column(tbl, col)

            # Use module-level helper `ensure_serial_pk(conn, table, id_col)`
            try:
                ensure_serial_pk(conn, 'rods', 'id')
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            # Force caught_fish.chat_id to BIGINT unconditionally.
            # Telegram supergroup IDs like -1001234567890 exceed 32-bit INTEGER range.
            # ALTER TABLE ... TYPE BIGINT is a no-op if column is already BIGINT.
            for _tbl, _col in [
                ('caught_fish', 'chat_id'),
                ('players', 'chat_id'),
                ('players', 'user_id'),
                ('player_rods', 'chat_id'),
                ('player_rods', 'user_id'),
                ('player_nets', 'chat_id'),
                ('player_nets', 'user_id'),
                ('star_transactions', 'chat_id'),
                ('star_transactions', 'user_id'),
            ]:
                try:
                    cursor.execute(
                        f'ALTER TABLE {_tbl} ALTER COLUMN {_col} TYPE BIGINT USING {_col}::bigint'
                    )
                    conn.commit()
                    logger.info("Ensured %s.%s is BIGINT", _tbl, _col)
                except Exception as _e:
                    logger.warning("ALTER %s.%s BIGINT skipped: %s", _tbl, _col, _e)
                    try:
                        conn.rollback()
                    except Exception:
                        pass

            # Populate chat_id in player_rods and player_nets and caught_fish
            # Use p.chat_id directly — the old regex '^[0-9]+$' incorrectly excluded
            # negative Telegram group chat IDs, setting them to NULL.
            cursor.execute('''
                UPDATE player_rods
                SET chat_id = (
                    SELECT p.chat_id
                    FROM players p
                    WHERE p.user_id = player_rods.user_id AND p.chat_id IS NOT NULL AND p.chat_id != 0
                    ORDER BY p.chat_id
                    LIMIT 1
                )
                WHERE chat_id IS NULL OR chat_id = 0
            ''')
            conn.commit()

            cursor.execute('''
                UPDATE player_nets
                SET chat_id = (
                    SELECT p.chat_id
                    FROM players p
                    WHERE p.user_id = player_nets.user_id AND p.chat_id IS NOT NULL AND p.chat_id != 0
                    ORDER BY p.chat_id
                    LIMIT 1
                )
                WHERE chat_id IS NULL OR chat_id = 0
            ''')
            conn.commit()

            cursor.execute('''
                UPDATE caught_fish
                SET chat_id = (
                    SELECT p.chat_id
                    FROM players p
                    WHERE p.user_id = caught_fish.user_id AND p.chat_id IS NOT NULL AND p.chat_id != 0
                    ORDER BY p.chat_id
                    LIMIT 1
                )
                WHERE chat_id IS NULL OR chat_id = 0
            ''')
            conn.commit()

            # Инициализация погоды для локаций
            cursor.execute('SELECT name FROM locations')
            locations = cursor.fetchall()

            from weather import weather_system
            for location in locations:
                loc_name = location[0]
                cursor.execute('SELECT 1 FROM weather WHERE location = %s', (loc_name,))
                if not cursor.fetchone():
                    condition, temp = weather_system.generate_weather(loc_name)
                    cursor.execute(
                        'INSERT INTO weather (location, condition, temperature) VALUES (%s, %s, %s)',
                        (loc_name, condition, temp),
                    )
                # Ensure a global players row exists (user_id = -1, chat_id = -1)
                try:
                    cursor.execute(
                        "INSERT INTO players (user_id, chat_id, username, coins, stars, xp, level) VALUES (%s, %s, %s, %s, %s, %s, %s) ON CONFLICT (user_id, chat_id) DO NOTHING",
                        (-1, -1, 'GLOBAL', 0, 0, 0, 0),
                    )
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass

                # Ensure a global base net exists (user_id = -1, chat_id = -1)
                try:
                    cursor.execute(
                        "INSERT INTO player_nets (user_id, net_name, uses_left, chat_id) VALUES (%s, %s, %s, %s) ON CONFLICT (user_id, net_name) DO NOTHING",
                        (-1, 'Базовая сеть', -1, -1),
                    )
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
            
            # ===== МИГРАЦИЯ: переименование рыб (убраны подписи в скобках) =====
            # Рыбы, пойманные до переименования, теряли стоимость — исправляем имена в caught_fish.
            _fish_renames = [
                ("Бестер (гибрид)", "Бестер"),
                ("Бестер (Гибрид) (Крупный)", "Бестер"),
                ("Ишхан (Форель)", "Ишхан"),
                ("Валаамка (Сиг)", "Валаамка"),
                ("Белуга (Монстр)", "Белуга"),
                ("Сом (Гигант)", "Сом"),
                ("Калуга (Гигант)", "Калуга"),
                ("Лещ (Крупный)", "Лещ"),
                ("Судак (Хищник)", "Судак"),
                ("Налим (Ночной)", "Налим"),
                ("Нельма (Крупная)", "Нельма"),
                ("Веслонос (Редкая)", "Веслонос"),
                ("Плотва (Частая)", "Плотва"),
                ("Уклейка (Мелочь)", "Уклейка"),
                ("Ёрш (Сорная)", "Ёрш"),
                ("Ряпушка (Мелочь)", "Ряпушка"),
                ("Колюшка (Крошечная)", "Колюшка"),
                ("Тигровая акула (Монстр)", "Тигровая акула"),
                ("Акула-молот (Гигант)", "Акула-молот"),
                ("Парусник (Быстрая)", "Парусник"),
                ("Палтус синекорый (Дно)", "Палтус синекорый"),
                ("Конгер (Морской угорь)", "Конгер"),
                ("Лаврак (Сибас)", "Лаврак"),
                ("Зубан (Дентекс)", "Зубан"),
                ("Серриола (Амберджек)", "Серриола"),
                ("Пеламида (Бонито)", "Пеламида"),
                ("Пилорыл (Редкая)", "Пилорыл"),
                ("Рыба-луна (Экзотика)", "Рыба-луна"),
                ("Сагрина (Зеленушка)", "Сагрина"),
                ("Скорпена (Ёрш)", "Скорпена"),
                ("Сариола (Желтохвост)", "Сариола"),
                ("Анчоус (Мелочь)", "Анчоус"),
                ("Шпрот (Мелочь)", "Шпрот"),
                ("Луна-рыба (Опах)", "Луна-рыба"),
                ("Морской петух (Монстр)", "Морской петух"),
            ]
            for old_name, new_name in _fish_renames:
                try:
                    cursor.execute(
                        "UPDATE caught_fish SET fish_name = %s WHERE fish_name = %s",
                        (new_name, old_name)
                    )
                except Exception:
                    try:
                        cursor.execute(
                            "UPDATE caught_fish SET fish_name = ? WHERE fish_name = ?",
                            (new_name, old_name)
                        )
                    except Exception:
                        pass

            # Migrate echosounder to be per-user (chat_id=0) instead of per-chat
            try:
                cursor.execute(
                    '''
                    INSERT INTO player_echosounder (user_id, chat_id, expires_at)
                    SELECT user_id, 0, MAX(expires_at)
                    FROM player_echosounder
                    WHERE chat_id != 0
                    GROUP BY user_id
                    ON CONFLICT (user_id, chat_id) DO UPDATE
                        SET expires_at = EXCLUDED.expires_at
                    '''
                )
                cursor.execute("DELETE FROM player_echosounder WHERE chat_id != 0")
            except Exception:
                pass

            # Ensure tournaments table exists and has all required columns
            try:
                cursor.execute(
                    '''CREATE TABLE IF NOT EXISTS tournaments (
                        id SERIAL PRIMARY KEY,
                        chat_id BIGINT,
                        created_by BIGINT,
                        title TEXT NOT NULL,
                        tournament_type TEXT DEFAULT 'total_weight',
                        starts_at TIMESTAMP NOT NULL,
                        ends_at TIMESTAMP NOT NULL,
                        target_fish TEXT,
                        prize_pool INTEGER DEFAULT 50,
                        target_location TEXT,
                        prize_places INTEGER DEFAULT 10,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )'''
                )
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS prize_pool INTEGER DEFAULT 50")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS target_location TEXT")
            except Exception:
                pass
            try:
                cursor.execute("ALTER TABLE tournaments ADD COLUMN IF NOT EXISTS prize_places INTEGER DEFAULT 10")
            except Exception:
                pass

            # Ensure /ref auxiliary tables exist on old deployments
            try:
                cursor.execute(
                    '''CREATE TABLE IF NOT EXISTS ref_access (
                        user_id BIGINT NOT NULL,
                        chat_id BIGINT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, chat_id)
                    )'''
                )
            except Exception:
                pass
            try:
                cursor.execute(
                    '''CREATE TABLE IF NOT EXISTS star_withdrawals (
                        id INTEGER PRIMARY KEY,
                        user_id BIGINT NOT NULL,
                        chat_id BIGINT,
                        amount INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )'''
                )
            except Exception:
                pass

            conn.commit()
    
    def _fill_default_data(self):
        """Заполнение базы данных начальными данными"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Добавление удочек с информацией о максимальном весе
            # Формат: (name, price, durability, max_durability, fish_bonus, max_weight)
            rods_data = [
                ("Бамбуковая удочка", 0, 100, 100, 0, 30),            # стартовая удочка, макс вес 30 кг
                ("Углепластиковая удочка", 1500, 150, 150, 5, 60),    # макс вес 60 кг
                ("Карбоновая удочка", 4500, 200, 200, 10, 120),        # макс вес 120 кг
                ("Золотая удочка", 15000, 300, 300, 20, 350),          # макс вес 350 кг
                ("Удачливая удочка", 25000, 150, 150, 15, 650),        # макс вес 650 кг, ломка 140-160 уловов
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO rods (name, price, durability, max_durability, fish_bonus, max_weight)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', rods_data)

            # Принудительное обновление max_weight для уже существующих удочек
            rods_weight_updates = [
                (30, "Бамбуковая удочка"),
                (60, "Углепластиковая удочка"),
                (120, "Карбоновая удочка"),
                (350, "Золотая удочка"),
                (650, "Удачливая удочка"),
            ]
            for max_w, rod_name in rods_weight_updates:
                cursor.execute('UPDATE rods SET max_weight = ? WHERE name = ?', (max_w, rod_name))
            
            # Добавление локаций
            locations_data = [
                ("Городской пруд", 100, 0, 5),
                ("Река", 150, 0, 10),
                ("Озеро", 200, 0, 15),
                ("Море", 300, 0, 20),
            ]

            # Ensure `locations.id` has a sequence/default on Postgres so inserts without id work
            try:
                cursor.execute(
                    "SELECT column_default FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
                    ('locations', 'id'),
                )
                row = cursor.fetchone()
                if row and not row[0]:
                    seq_name = 'locations_id_seq'
                    cursor.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name}")
                    cursor.execute(f"ALTER TABLE locations ALTER COLUMN id SET DEFAULT nextval('{seq_name}')")
                    cursor.execute("SELECT COALESCE(MAX(id), 1) FROM locations")
                    max_id = cursor.fetchone()[0] or 1
                    cursor.execute("SELECT setval(%s, %s)", (seq_name, max_id))
                    conn.commit()
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            cursor.executemany('''
                INSERT OR IGNORE INTO locations (name, fish_population, current_players, max_players)
                VALUES (?, ?, ?, ?)
            ''', locations_data)
            
            # Добавление наживок
            bait_price_factor = 0.85
            base_baits_data = [
                ("Черви", 20, 0, "Все"),
                ("Опарыш", 30, 2, "Все"),
                ("Мотыль", 30, 2, "Все"),
                ("Хлеб", 15, 0, "Все"),
                ("Мякиш хлеба", 20, 0, "Все"),
                ("Тесто", 20, 0, "Все"),
                ("Манка", 25, 0, "Все"),
                ("Каша", 25, 0, "Все"),
                ("Кукуруза", 30, 1, "Все"),
                ("Горох", 30, 1, "Все"),
                ("Бойлы", 80, 5, "Все"),
                ("Картофель", 25, 0, "Все"),
                ("Технопланктон", 120, 6, "Все"),
                ("Зелень", 20, 0, "Все"),
                ("Камыш", 20, 0, "Все"),
                ("Огурец", 25, 0, "Все"),
                ("Паста", 35, 1, "Все"),
                ("Творожное тесто", 35, 1, "Все"),
                ("Креветка", 60, 3, "Все"),
                ("Морской червь", 70, 3, "Все"),
                ("Кусочки рыбы", 60, 3, "Все"),
                ("Сало", 30, 0, "Все"),
                ("Живец", 80, 6, "Все"),
                ("Крупный живец", 120, 8, "Все"),
                ("Кальмар", 90, 5, "Все"),
                ("Сардина", 70, 4, "Все"),
                ("Сельдь", 70, 4, "Все"),
                ("Моллюск", 80, 4, "Все"),
                ("Пилькер", 110, 7, "Все"),
                ("Блесна", 60, 5, "Все"),
                ("Узкая блесна", 70, 6, "Все"),
                ("Маленькая блесна", 50, 4, "Все"),
                ("Воблер", 80, 6, "Все"),
                ("Мушка", 40, 2, "Все"),
                ("Муха", 25, 1, "Все"),
                ("Кузнечик", 30, 1, "Все"),
                ("Майский жук", 40, 2, "Все"),
                ("Лягушонок", 90, 6, "Все"),
                ("Выползок", 60, 4, "Все"),
                ("Пучок червей", 70, 4, "Все"),
                ("Личинка", 30, 1, "Все"),
                ("Личинка короеда", 60, 4, "Все"),
                ("Мышь", 120, 8, "Все"),
                ("Икра", 90, 6, "Все"),
                ("Мормыш", 70, 5, "Все"),
                ("Спрут", 140, 9, "Все"),
                ("Туша рыбы", 160, 10, "Все"),
                ("Крупный кусок мяса", 140, 9, "Все"),
                ("Печень", 90, 6, "Все"),
                ("Кусок мяса", 110, 7, "Все"),
            ]

            baits_data = [
                (name, max(1, int(round(price * bait_price_factor))), bonus, suitable)
                for name, price, bonus, suitable in base_baits_data
            ]
            # Ensure `baits.id` has a sequence/default on Postgres so inserts without id work
            try:
                ensure_serial_pk(conn, 'baits', 'id')
            except Exception:
                try:
                    conn.rollback()
                except Exception:
                    pass

            cursor.executemany('''
                INSERT OR REPLACE INTO baits (name, price, fish_bonus, suitable_for)
                VALUES (?, ?, ?, ?)
            ''', baits_data)
            
            # Добавление рыб с расширенной информацией
            # Формат: (имя, редкость, min_вес_кг, max_вес_кг, min_длина_см, max_длина_см, цена, локации, сезоны, наживка, макс_вес_удочки, стикер)
            fish_data = [
                # ===== ПРУД =====
                ("Карась", "Обычная", 0.2, 1.2, 15, 35, 15, "Городской пруд", "Все", "Хлеб,Манка,Черви,Опарыш,Тесто,Кукуруза,Мотыль,Горох,Каша", 6, None),
                ("Ротан", "Обычная", 0.1, 0.6, 12, 30, 12, "Городской пруд", "Все", "Сало,Черви,Кусочки рыбы,Опарыш,Мотыль,Личинка", 5, None),
                ("Верховка", "Обычная", 0.02, 0.1, 6, 12, 5, "Городской пруд", "Лето", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 3, None),
                ("Вьюн", "Обычная", 0.05, 0.3, 15, 25, 8, "Городской пруд", "Лето", "Черви,Мотыль,Личинка,Опарыш", 4, None),
                ("Горчак", "Обычная", 0.05, 0.25, 10, 18, 7, "Городской пруд", "Лето", "Хлеб,Тесто,Манка,Опарыш", 4, None),
                ("Золотой карась", "Редкая", 0.3, 1.5, 20, 40, 40, "Городской пруд", "Весна,Лето", "Черви,Тесто,Хлеб,Опарыш,Кукуруза,Горох,Манка,Каша", 8, None),
                ("Карп", "Редкая", 2.0, 12.0, 40, 90, 80, "Городской пруд", "Лето,Осень", "Кукуруза,Бойлы,Картофель,Горох,Черви,Каша,Тесто,Хлеб,Пучок червей", 25, None),
                ("Толстолобик", "Редкая", 3.0, 15.0, 50, 100, 90, "Городской пруд", "Лето", "Технопланктон,Камыш,Зелень,Хлеб,Тесто,Каша", 30, None),
                ("Прудовая форель", "Редкая", 1.0, 4.0, 30, 60, 70, "Городской пруд", "Осень,Зима", "Паста,Кукуруза,Живец,Блесна,Икра,Черви,Опарыш,Мушка", 12, None),
                ("Буффало", "Редкая", 2.0, 8.0, 40, 80, 85, "Городской пруд", "Лето", "Тесто,Кукуруза,Каша,Бойлы,Черви,Горох,Картофель", 20, None),
                ("Черный амур", "Легендарная", 7.0, 25.0, 60, 120, 250, "Городской пруд", "Лето", "Моллюск,Кукуруза,Горох,Камыш,Зелень,Тесто,Каша", 35, None),
                ("Карп Кои", "Легендарная", 3.0, 12.0, 40, 80, 220, "Городской пруд", "Лето", "Бойлы,Кукуруза,Тесто,Хлеб,Горох,Картофель,Каша,Пучок червей", 25, None),
                ("Змееголов", "Легендарная", 4.0, 15.0, 50, 100, 260, "Городской пруд", "Лето", "Лягушонок,Живец,Кусок мяса,Блесна,Воблер,Крупный живец,Кусочки рыбы", 30, None),
                
                # ===== ПРУД (новые виды) =====
                ("Канальный сомик", "Редкая", 0.3, 2.5, 25, 55, 45, "Городской пруд", "Весна,Лето,Осень", "Кусочки рыбы,Выползок,Черви,Печень,Пучок червей", 8, None),
                ("Амурский чебачок", "Обычная", 0.01, 0.05, 5, 10, 3, "Городской пруд", "Весна,Лето,Осень", "Мотыль,Опарыш,Тесто,Хлеб", 3, None),
                ("Солнечный окунь", "Обычная", 0.05, 0.3, 8, 18, 8, "Городской пруд", "Весна,Лето,Осень", "Черви,Муха,Мотыль,Опарыш", 4, None),
                ("Шиповка", "Обычная", 0.01, 0.03, 4, 8, 4, "Городской пруд", "Все", "Мотыль,Мормыш,Черви", 3, None),
                ("Бестер", "Легендарная", 1.0, 8.0, 40, 100, 200, "Городской пруд", "Все", "Сельдь,Выползок,Кусочки рыбы,Кусок мяса,Живец", 20, None),
                ("Колюшка", "Обычная", 0.005, 0.02, 3, 7, 2, "Городской пруд", "Все", "Мотыль,Икра,Опарыш", 3, None),
                ("Веслонос", "Легендарная", 2.0, 10.0, 50, 120, 350, "Городской пруд", "Весна,Лето,Осень", "Каша,Опарыш,Мотыль,Тесто", 30, None),
                ("Бычок-песочник", "Обычная", 0.01, 0.08, 5, 12, 5, "Городской пруд", "Все", "Черви,Кусочки рыбы,Мотыль,Опарыш", 4, None),
                ("Гольян", "Обычная", 0.01, 0.04, 4, 9, 3, "Городской пруд", "Весна,Лето,Осень", "Муха,Мотыль,Хлеб,Манка,Опарыш", 3, None),
                ("Аллигаторовый панцирник", "Мифическая", 10.0, 80.0, 80, 250, 850, "Городской пруд", "Лето", "Крупный живец,Лягушонок,Кусок мяса,Блесна,Воблер", 60, None),

                # ===== РЕКА =====
                ("Плотва", "Обычная", 0.05, 0.4, 12, 28, 10, "Река", "Все", "Опарыш,Тесто,Мотыль,Черви,Хлеб,Манка,Кукуруза,Горох", 5, None),
                ("Окунь", "Обычная", 0.1, 0.8, 15, 30, 20, "Река,Озеро", "Все", "Мотыль,Черви,Живец,Блесна,Опарыш,Маленькая блесна,Воблер,Кусочки рыбы", 6, None),
                ("Голавль", "Обычная", 0.2, 1.0, 20, 40, 18, "Река", "Весна,Лето", "Кузнечик,Майский жук,Хлеб,Блесна,Черви,Воблер,Опарыш,Муха", 7, None),
                ("Уклейка", "Обычная", 0.02, 0.15, 8, 18, 8, "Река", "Лето", "Муха,Опарыш,Тесто,Хлеб,Мотыль,Манка", 3, None),
                ("Лещ", "Обычная", 0.5, 2.5, 25, 50, 25, "Река,Озеро", "Лето,Осень", "Горох,Пучок червей,Кукуруза,Опарыш,Каша,Черви,Мотыль,Тесто", 10, None),
                ("Ёрш", "Обычная", 0.05, 0.2, 10, 18, 8, "Река", "Зима,Весна", "Черви,Мотыль,Опарыш,Личинка", 4, None),
                ("Жерех", "Редкая", 1.0, 4.0, 35, 60, 50, "Река", "Весна,Лето", "Блесна,Живец,Кузнечик,Воблер,Узкая блесна,Кусочки рыбы", 14, None),
                ("Судак", "Редкая", 1.0, 5.0, 35, 70, 55, "Река", "Осень,Зима", "Живец,Узкая блесна,Воблер,Пучок червей,Блесна,Кусочки рыбы", 12, None),
                ("Язь", "Редкая", 0.6, 2.5, 25, 45, 40, "Река", "Весна,Осень", "Кукуруза,Горох,Черви,Хлеб,Кузнечик,Опарыш,Тесто,Каша", 10, None),
                ("Налим", "Редкая", 0.5, 3.0, 30, 60, 45, "Река", "Зима", "Лягушонок,Пучок червей,Кусочки рыбы,Печень,Черви,Живец", 12, None),
                ("Хариус", "Редкая", 0.4, 1.5, 25, 40, 40, "Река", "Лето", "Мушка,Опарыш,Черви,Маленькая блесна,Муха,Мотыль", 10, None),
                ("Сом", "Легендарная", 5.0, 40.0, 80, 200, 200, "Река", "Лето", "Печень,Крупный живец,Выползок,Лягушонок,Кусочки рыбы,Живец,Кусок мяса", 40, None),
                ("Стерлядь", "Легендарная", 1.0, 6.0, 40, 80, 220, "Река", "Весна,Лето", "Личинка короеда,Черви,Опарыш,Мотыль,Икра", 20, None),
                ("Таймень", "Легендарная", 5.0, 20.0, 60, 120, 250, "Река", "Осень", "Блесна,Воблер,Мышь,Крупный живец,Живец,Кусочки рыбы", 30, None),
                ("Белуга", "Легендарная", 30.0, 120.0, 120, 250, 400, "Река", "Весна", "Кусочки рыбы,Крупный живец,Моллюск,Живец,Сельдь,Выползок,Кусок мяса", 60, None),

                # ===== РЕКА (новые виды) =====
                ("Щука", "Редкая", 1.0, 10.0, 40, 120, 60, "Река", "Все", "Блесна,Воблер,Живец,Лягушонок,Узкая блесна,Кусочки рыбы", 18, None),
                ("Линь", "Редкая", 0.2, 2.0, 15, 45, 30, "Река", "Весна,Лето", "Выползок,Черви,Опарыш,Тесто,Мотыль,Кукуруза,Горох", 8, None),
                ("Усач", "Редкая", 0.5, 3.0, 25, 60, 55, "Река", "Весна,Лето,Осень", "Личинка короеда,Моллюск,Выползок,Каша,Черви", 12, None),
                ("Чехонь", "Обычная", 0.1, 0.7, 18, 40, 15, "Река", "Весна,Лето,Осень", "Мушка,Опарыш,Мотыль,Маленькая блесна,Муха", 6, None),
                ("Берш", "Редкая", 0.2, 1.2, 20, 45, 40, "Река", "Все", "Кусочки рыбы,Маленькая блесна,Черви,Живец,Блесна", 8, None),
                ("Пескарь", "Обычная", 0.01, 0.05, 5, 12, 5, "Река", "Все", "Мотыль,Черви,Опарыш,Манка", 3, None),
                ("Густера", "Обычная", 0.05, 0.4, 10, 30, 10, "Река", "Все", "Каша,Горох,Мотыль,Опарыш,Черви", 5, None),
                ("Елец", "Обычная", 0.01, 0.08, 7, 16, 6, "Река", "Все", "Мушка,Личинка короеда,Мотыль,Хлеб,Опарыш", 4, None),
                ("Рыбец", "Редкая", 0.3, 2.0, 20, 45, 45, "Река", "Все", "Моллюск,Опарыш,Мотыль,Личинка короеда,Черви", 10, None),
                ("Подуст", "Обычная", 0.2, 1.0, 15, 35, 12, "Река", "Весна,Лето,Осень", "Каша,Мотыль,Опарыш,Черви,Тесто", 6, None),
                ("Синец", "Обычная", 0.1, 0.7, 15, 35, 10, "Река", "Все", "Мотыль,Опарыш,Каша,Тесто,Черви", 5, None),
                ("Белоглазка", "Обычная", 0.05, 0.3, 10, 25, 8, "Река", "Все", "Каша,Опарыш,Черви,Кукуруза,Тесто", 5, None),
                ("Угорь", "Редкая", 0.2, 2.0, 30, 100, 50, "Река", "Лето,Осень", "Выползок,Кусочки рыбы,Живец,Лягушонок,Кусок мяса", 12, None),
                ("Красноперка", "Обычная", 0.05, 0.5, 10, 25, 10, "Река", "Весна,Лето,Осень", "Кукуруза,Мушка,Хлеб,Тесто,Опарыш", 5, None),
                ("Форель ручьевая", "Редкая", 0.2, 1.5, 20, 50, 55, "Река", "Все", "Мушка,Маленькая блесна,Кузнечик,Мотыль,Опарыш", 10, None),
                ("Ленок", "Редкая", 0.5, 3.0, 30, 70, 90, "Река", "Весна,Лето,Осень", "Мышь,Блесна,Мушка,Личинка короеда,Воблер", 14, None),
                ("Нельма", "Легендарная", 2.0, 15.0, 50, 130, 300, "Река", "Все", "Крупный живец,Блесна,Воблер,Кусочки рыбы,Живец", 35, None),
                ("Муксун", "Редкая", 0.5, 3.0, 30, 70, 60, "Река", "Весна,Осень,Зима", "Мушка,Мотыль,Моллюск,Мормыш,Икра", 12, None),
                ("Чир", "Редкая", 0.5, 2.5, 25, 60, 55, "Река", "Весна,Осень,Зима", "Моллюск,Личинка короеда,Мотыль,Мормыш", 12, None),
                ("Сиг", "Редкая", 0.3, 2.0, 20, 55, 45, "Река", "Весна,Осень,Зима", "Мушка,Икра,Маленькая блесна,Мотыль,Мормыш", 10, None),
                ("Осетр русский", "Легендарная", 5.0, 40.0, 70, 200, 400, "Река", "Все", "Моллюск,Пучок червей,Выползок,Кусочки рыбы,Кусок мяса", 50, None),
                ("Севрюга", "Легендарная", 3.0, 25.0, 60, 180, 220, "Река,Море", "Весна,Осень", "Кусочки рыбы,Моллюск,Выползок,Кусок мяса", 40, None),
                ("Шип", "Легендарная", 2.0, 12.0, 40, 120, 180, "Река,Море", "Весна,Осень", "Пучок червей,Моллюск,Личинка короеда,Черви", 30, None),
                ("Бычок-кругляк", "Обычная", 0.01, 0.08, 5, 12, 5, "Река", "Все", "Черви,Кусочки рыбы,Мотыль,Опарыш", 4, None),
                ("Верхогляд", "Редкая", 0.5, 3.0, 30, 70, 120, "Река", "Весна,Лето,Осень", "Живец,Воблер,Блесна,Кусочки рыбы", 18, None),
                ("Ауха", "Редкая", 0.5, 2.0, 25, 60, 110, "Река", "Лето,Осень", "Живец,Блесна,Воблер,Кусочки рыбы", 16, None),
                ("Калуга", "Мифическая", 20.0, 200.0, 100, 400, 800, "Река", "Весна,Лето,Осень", "Крупный живец,Кусочки рыбы,Печень,Кусок мяса,Сельдь", 70, None),
                ("Шемая", "Редкая", 0.1, 1.0, 15, 35, 50, "Река", "Весна,Лето,Осень", "Мушка,Опарыш,Мотыль,Черви", 8, None),
                ("Вырезуб", "Редкая", 0.5, 3.0, 25, 60, 55, "Река", "Весна,Лето,Осень", "Моллюск,Выползок,Кукуруза,Черви", 12, None),
                ("Минога", "Редкая", 0.01, 0.2, 10, 40, 30, "Река", "Все", "Мотыль,Черви,Личинка,Опарыш", 5, None),
                ("Голец арктический", "Редкая", 0.5, 3.0, 25, 60, 100, "Река", "Весна,Осень,Зима", "Икра,Блесна,Мормыш,Мушка", 14, None),
                ("Байкальский омуль", "Редкая", 0.3, 1.5, 20, 50, 70, "Река", "Весна,Осень,Зима", "Мормыш,Муха,Икра,Мотыль", 12, None),
                ("Ряпушка", "Обычная", 0.01, 0.05, 5, 12, 5, "Река", "Все", "Мотыль,Опарыш,Муха,Черви", 3, None),
                ("Корюшка", "Редкая", 0.01, 0.1, 7, 15, 15, "Река", "Весна,Зима", "Кусочки рыбы,Мотыль,Опарыш", 5, None),
                ("Сибирский осетр", "Легендарная", 5.0, 50.0, 70, 200, 420, "Река", "Все", "Моллюск,Выползок,Кусочки рыбы,Пучок червей,Живец", 50, None),
                ("Кумжа", "Редкая", 1.0, 7.0, 30, 80, 180, "Река", "Весна,Лето,Осень,Зима", "Воблер,Блесна,Муха,Мушка,Живец", 18, None),
                ("Палия", "Редкая", 1.0, 8.0, 40, 90, 180, "Река", "Весна,Осень,Зима", "Блесна,Живец,Икра,Мотыль", 18, None),
                ("Подкаменщик", "Обычная", 0.05, 0.3, 8, 20, 6, "Река", "Все", "Мотыль,Черви,Опарыш,Кусочки рыбы", 4, None),
                ("Чебак", "Обычная", 0.05, 0.3, 10, 22, 7, "Река", "Все", "Опарыш,Тесто,Хлеб,Мотыль,Манка", 4, None),
                ("Голубой сом", "Легендарная", 10.0, 80.0, 80, 200, 350, "Река", "Лето,Осень", "Крупный живец,Выползок,Печень,Кусок мяса,Сельдь", 50, None),
                ("Мальма", "Редкая", 0.5, 3.0, 25, 65, 60, "Река", "Весна,Осень,Зима", "Блесна,Мушка,Живец,Икра,Мотыль", 12, None),
                ("Ишхан", "Легендарная", 1.0, 8.0, 35, 80, 280, "Река", "Весна,Лето,Осень,Зима", "Блесна,Мушка,Живец,Икра,Воблер", 25, None),
                ("Зеркальный карп", "Редкая", 2.0, 15.0, 40, 90, 80, "Река", "Весна,Лето,Осень", "Кукуруза,Горох,Каша,Тесто,Бойлы,Картофель", 18, None),
                ("Пестрый толстолобик", "Редкая", 3.0, 15.0, 50, 110, 90, "Река", "Лето", "Технопланктон,Каша,Хлеб,Тесто,Зелень", 25, None),
                ("Валаамка", "Редкая", 0.5, 3.0, 25, 60, 130, "Озеро", "Осень,Зима", "Мормыш,Мотыль,Маленькая блесна,Икра", 18, None),

                # ===== ОЗЕРО =====
                ("Красноперка", "Обычная", 0.1, 0.5, 15, 25, 10, "Озеро", "Лето", "Тесто,Хлеб,Муха,Опарыш,Черви,Манка,Кукуруза,Мотыль", 5, None),
                ("Густера", "Обычная", 0.15, 0.8, 18, 30, 12, "Озеро", "Лето", "Опарыш,Мотыль,Каша,Черви,Тесто,Горох", 6, None),
                ("Щука", "Обычная", 1.0, 6.0, 40, 80, 30, "Река,Озеро", "Весна,Осень", "Живец,Блесна,Воблер,Лягушонок,Кусочки рыбы,Узкая блесна", 18, None),
                ("Синец", "Обычная", 0.2, 0.8, 20, 35, 12, "Озеро", "Лето", "Черви,Опарыш,Мотыль,Тесто,Каша", 6, None),
                ("Подлещик", "Обычная", 0.2, 1.0, 20, 40, 15, "Озеро", "Весна,Лето", "Мотыль,Опарыш,Каша,Тесто,Черви,Горох,Кукуруза", 8, None),
                ("Пескарь", "Обычная", 0.05, 0.3, 12, 22, 7, "Озеро", "Все", "Черви,Мотыль,Хлеб,Опарыш,Манка", 5, None),
                ("Чехонь", "Редкая", 0.3, 1.2, 25, 40, 30, "Озеро", "Весна,Лето", "Опарыш,Муха,Тесто,Кузнечик,Мотыль,Черви", 8, None),
                ("Линь", "Редкая", 0.5, 2.0, 30, 50, 35, "Озеро", "Лето", "Черви,Творожное тесто,Опарыш,Мотыль,Кукуруза,Горох", 10, None),
                ("Сиг", "Редкая", 0.8, 3.0, 35, 60, 45, "Озеро", "Осень,Зима", "Икра,Мормыш,Мотыль,Маленькая блесна,Опарыш,Черви", 12, None),
                ("Белый амур", "Редкая", 2.0, 10.0, 50, 90, 60, "Озеро", "Лето", "Камыш,Кукуруза,Горох,Огурец,Зелень,Тесто", 20, None),
                ("Пелядь", "Редкая", 0.8, 3.0, 35, 60, 45, "Озеро", "Зима", "Мормыш,Мотыль,Икра,Опарыш", 12, None),
                ("Форель озерная", "Легендарная", 1.5, 6.0, 40, 70, 200, "Озеро", "Весна,Осень", "Воблер,Блесна,Живец,Икра,Кузнечик,Мушка,Опарыш,Черви,Маленькая блесна", 16, None),
                ("Угорь", "Легендарная", 1.0, 5.0, 50, 80, 180, "Озеро", "Лето", "Выползок,Живец,Кусочки рыбы,Пучок червей,Лягушонок,Кусок мяса", 18, None),
                ("Осетр", "Легендарная", 3.0, 25.0, 70, 140, 260, "Озеро", "Лето,Осень", "Сельдь,Кусочки рыбы,Моллюск,Выползок,Крупный живец,Живец,Икра", 35, None),

                # ===== ОЗЕРО (новые виды) =====
                ("Белуга", "Мифическая", 100.0, 500.0, 150, 450, 1100, "Озеро", "Весна,Осень", "Сельдь,Кусочки рыбы,Живец,Крупный живец", 80, None),
                ("Сом", "Легендарная", 20.0, 150.0, 100, 350, 500, "Озеро,Река", "Лето,Осень", "Выползок,Живец,Кусочки рыбы,Сельдь,Кусок мяса", 60, None),
                ("Калуга", "Мифическая", 50.0, 500.0, 150, 450, 1000, "Озеро,Река", "Весна,Лето,Осень", "Живец,Кусочки рыбы,Выползок,Сельдь", 80, None),
                ("Лещ", "Редкая", 2.0, 7.0, 40, 70, 80, "Озеро", "Все", "Каша,Горох,Кукуруза,Мотыль,Пучок червей,Опарыш", 18, None),
                ("Судак", "Редкая", 2.0, 12.0, 40, 100, 90, "Озеро", "Все", "Воблер,Блесна,Живец,Узкая блесна,Кусочки рыбы", 20, None),
                ("Налим", "Редкая", 1.0, 8.0, 40, 100, 85, "Озеро", "Весна,Осень,Зима", "Кусочки рыбы,Живец,Выползок,Пучок червей", 18, None),
                ("Радужная форель", "Редкая", 0.5, 5.0, 30, 70, 80, "Озеро", "Все", "Икра,Муха,Воблер,Блесна,Живец,Мушка", 14, None),
                ("Плотва", "Обычная", 0.05, 0.5, 10, 25, 8, "Озеро", "Все", "Тесто,Хлеб,Опарыш,Мотыль,Манка", 4, None),
                ("Карп зеркальный", "Редкая", 2.0, 15.0, 40, 90, 85, "Озеро", "Весна,Лето,Осень", "Кукуруза,Горох,Каша,Тесто,Бойлы", 20, None),
                ("Язь", "Редкая", 0.5, 3.0, 25, 60, 45, "Озеро", "Весна,Лето,Осень", "Горох,Кукуруза,Муха,Хлеб,Черви,Опарыш", 10, None),
                ("Голавль", "Редкая", 0.5, 2.5, 20, 50, 40, "Озеро", "Весна,Лето,Осень", "Муха,Хлеб,Кукуруза,Блесна,Кузнечик", 10, None),
                ("Уклейка", "Обычная", 0.01, 0.03, 5, 10, 3, "Озеро", "Весна,Лето,Осень", "Муха,Опарыш,Хлеб,Манка", 3, None),
                ("Ёрш", "Обычная", 0.01, 0.05, 5, 12, 3, "Озеро", "Все", "Мотыль,Черви,Мормыш,Опарыш", 3, None),
                ("Толстолобик пестрый", "Редкая", 3.0, 15.0, 50, 120, 180, "Озеро,Река", "Лето,Осень", "Огурец,Камыш,Каша,Тесто,Хлеб", 30, None),
                ("Арктический голец", "Редкая", 0.5, 3.0, 25, 60, 120, "Озеро", "Весна,Осень,Зима", "Икра,Блесна,Мормыш,Мотыль", 18, None),
                ("Омуль", "Редкая", 0.3, 2.0, 20, 55, 60, "Озеро", "Все", "Мормыш,Муха,Икра,Мотыль,Опарыш", 12, None),
                ("Нельма", "Легендарная", 5.0, 20.0, 60, 130, 320, "Озеро", "Весна,Осень,Зима", "Блесна,Воблер,Живец,Кусочки рыбы", 40, None),
                ("Веслонос", "Легендарная", 2.0, 10.0, 50, 120, 320, "Озеро", "Весна,Лето,Осень", "Каша,Тесто,Мотыль,Опарыш", 30, None),
                ("Кумжа", "Редкая", 1.0, 7.0, 30, 80, 170, "Озеро", "Весна,Лето,Осень,Зима", "Воблер,Блесна,Муха,Мушка,Живец", 18, None),
                ("Палия", "Редкая", 1.0, 8.0, 40, 90, 170, "Озеро", "Весна,Осень,Зима", "Блесна,Живец,Икра,Мотыль", 18, None),
                ("Ряпушка", "Обычная", 0.01, 0.05, 5, 12, 4, "Озеро", "Все", "Мотыль,Опарыш,Муха,Черви", 3, None),
                ("Корюшка", "Редкая", 0.01, 0.1, 7, 15, 15, "Озеро,Городской пруд", "Весна,Зима", "Кусочки рыбы,Мотыль,Опарыш", 5, None),
                ("Берш", "Редкая", 0.2, 1.2, 20, 45, 40, "Озеро", "Все", "Живец,Блесна,Черви,Кусочки рыбы", 8, None),
                ("Белоглазка", "Обычная", 0.05, 0.3, 10, 25, 7, "Озеро", "Все", "Каша,Опарыш,Черви,Тесто", 4, None),
                ("Хариус", "Редкая", 0.2, 1.5, 20, 50, 45, "Озеро", "Весна,Лето,Осень,Зима", "Муха,Блесна,Икра,Мотыль,Мушка", 10, None),
                ("Колюшка", "Обычная", 0.005, 0.02, 3, 7, 2, "Озеро", "Все", "Мотыль,Икра,Опарыш", 3, None),
                ("Американский сомик", "Редкая", 0.3, 2.5, 25, 55, 45, "Озеро", "Весна,Лето,Осень", "Выползок,Кусочки рыбы,Хлеб,Черви", 8, None),
                ("Озерный гольян", "Обычная", 0.01, 0.04, 4, 9, 3, "Озеро", "Весна,Лето,Осень", "Мотыль,Муха,Хлеб,Манка", 3, None),
                ("Бестер", "Легендарная", 3.0, 15.0, 50, 130, 260, "Озеро", "Все", "Сельдь,Выползок,Кусочки рыбы,Живец,Кусок мяса", 35, None),

                # ===== МОРЕ =====
                ("Сельдь", "Обычная", 0.2, 0.8, 20, 35, 15, "Море", "Все", "Креветка,Опарыш,Морской червь,Кусочки рыбы,Блесна", 6, None),
                ("Ставрида", "Обычная", 0.3, 1.0, 25, 40, 18, "Море", "Лето,Осень", "Блесна,Креветка,Кусочки рыбы,Пилькер,Воблер", 8, None),
                ("Бычок", "Обычная", 0.05, 0.3, 10, 20, 10, "Море", "Весна,Лето", "Черви,Кусочки рыбы,Креветка,Сало,Морской червь", 6, None),
                ("Камбала", "Обычная", 0.5, 3.0, 30, 50, 20, "Море", "Осень,Зима", "Морской червь,Кусочки рыбы,Моллюск,Креветка,Сельдь", 10, None),
                ("Морской окунь", "Обычная", 0.4, 1.5, 25, 40, 22, "Море", "Весна,Лето", "Живец,Креветка,Блесна,Воблер,Кусочки рыбы", 10, None),
                ("Кефаль", "Обычная", 0.4, 1.2, 30, 45, 20, "Море,Река", "Лето", "Мякиш хлеба,Морской червь,Тесто,Хлеб,Креветка", 8, None),
                ("Барабулька", "Редкая", 0.2, 0.8, 20, 30, 35, "Море", "Лето", "Морской червь,Креветка,Опарыш,Кусочки рыбы", 8, None),
                ("Скумбрия", "Редкая", 0.6, 2.5, 30, 50, 50, "Море", "Лето,Осень", "Блесна,Пилькер,Живец,Кальмар,Кусочки рыбы,Креветка", 14, None),
                ("Тунец", "Редкая", 5.0, 30.0, 80, 150, 180, "Море", "Лето", "Воблер,Сардина,Живец,Кальмар,Кусочки рыбы,Блесна,Пилькер", 35, None),
                ("Дорадо", "Редкая", 1.0, 6.0, 40, 70, 90, "Море", "Лето", "Кальмар,Креветка,Кусочки рыбы,Живец,Сардина", 18, None),
                ("Мурена", "Редкая", 2.0, 10.0, 60, 120, 120, "Море", "Лето", "Крупный кусок мяса,Кусочки рыбы,Кальмар,Живец,Кусок мяса", 25, None),
                ("Сарган", "Редкая", 0.5, 2.0, 30, 60, 60, "Море", "Осень", "Опарыш,Кусочки рыбы,Креветка,Блесна,Морской червь", 12, None),
                ("Рыба-меч", "Легендарная", 20.0, 110.0, 120, 250, 500, "Море", "Лето,Осень", "Крупный живец,Кальмар,Туша рыбы,Воблер,Сардина,Живец", 60, None),
                ("Марлин", "Легендарная", 20.0, 120.0, 140, 300, 600, "Море", "Осень", "Воблер,Спрут,Крупный живец,Кальмар,Туша рыбы,Живец", 60, None),
                ("Белая акула", "Легендарная", 50.0, 300.0, 200, 500, 900, "Море", "Лето", "Туша рыбы,Крупный живец,Кусок мяса,Крупный кусок мяса,Кальмар,Спрут", 80, None),

                # ===== МОРЕ (новые виды) =====
                ("Тигровая акула", "Мифическая", 100.0, 700.0, 200, 550, 1500, "Море", "Лето,Осень,Зима", "Туша рыбы,Крупный кусок мяса,Спрут,Кальмар", 80, None),
                ("Акула-молот", "Мифическая", 80.0, 400.0, 150, 600, 1200, "Море", "Весна,Лето,Осень", "Крупный живец,Кальмар,Туша рыбы,Спрут", 80, None),
                ("Акула Мако", "Легендарная", 50.0, 300.0, 150, 400, 750, "Море", "Весна,Лето,Осень,Зима", "Сардина,Пилькер,Крупный живец,Кальмар", 65, None),
                ("Лисья акула", "Легендарная", 40.0, 250.0, 150, 500, 650, "Море", "Весна,Лето,Осень,Зима", "Живец,Кальмар,Блесна,Пилькер", 60, None),
                ("Парусник", "Легендарная", 15.0, 100.0, 100, 340, 600, "Море", "Весна,Лето,Осень", "Воблер,Пилькер,Сардина,Спрут,Кальмар", 55, None),
                ("Ваху", "Редкая", 5.0, 50.0, 60, 200, 200, "Море", "Весна,Лето,Осень", "Пилькер,Воблер,Кусочки рыбы,Сардина", 30, None),
                ("Барракуда", "Редкая", 3.0, 30.0, 50, 180, 150, "Море", "Все", "Воблер,Блесна,Живец,Кусочки рыбы,Пилькер", 25, None),
                ("Палтус синекорый", "Легендарная", 20.0, 200.0, 80, 250, 600, "Море", "Осень,Зима", "Моллюск,Кусочки рыбы,Кальмар,Сельдь", 55, None),
                ("Скат-хвостокол", "Редкая", 5.0, 60.0, 40, 180, 160, "Море", "Все", "Морской червь,Моллюск,Кусочки рыбы,Кальмар", 25, None),
                ("Морской чёрт", "Мифическая", 5.0, 40.0, 40, 180, 300, "Море", "Все", "Кальмар,Живец,Кусочки рыбы,Крупный живец", 40, None),
                ("Конгер", "Редкая", 5.0, 50.0, 80, 300, 320, "Море", "Все", "Крупный кусок мяса,Кальмар,Живец,Кусок мяса", 40, None),
                ("Луфарь", "Обычная", 1.0, 15.0, 30, 100, 35, "Море", "Весна,Лето,Осень", "Пилькер,Блесна,Сардина,Живец", 18, None),
                ("Лаврак", "Обычная", 1.0, 12.0, 30, 100, 40, "Море", "Все", "Креветка,Воблер,Морской червь,Блесна", 18, None),
                ("Зубан", "Редкая", 2.0, 15.0, 40, 100, 120, "Море", "Все", "Кальмар,Живец,Пилькер,Кусочки рыбы", 25, None),
                ("Групер гигантский", "Мифическая", 50.0, 200.0, 100, 250, 950, "Море", "Лето,Осень", "Крупный живец,Спрут,Кусок мяса,Кальмар", 75, None),
                ("Серриола", "Редкая", 5.0, 80.0, 60, 190, 200, "Море", "Все", "Живец,Пилькер,Кальмар,Воблер", 30, None),
                ("Пеламида", "Обычная", 1.0, 10.0, 35, 90, 40, "Море", "Все", "Блесна,Сардина,Воблер,Живец,Пилькер", 18, None),
                ("Пилорыл", "Мифическая", 100.0, 400.0, 200, 700, 1300, "Море", "Лето,Осень", "Моллюск,Кусочки рыбы,Кальмар,Крупный кусок мяса", 80, None),
                ("Рыба-луна", "Мифическая", 200.0, 1500.0, 100, 330, 2000, "Море", "Лето,Осень", "Спрут,Кальмар,Моллюск,Медуза", 80, None),
                ("Сагрина", "Обычная", 0.1, 0.5, 10, 25, 10, "Море", "Весна,Лето,Осень", "Креветка,Тесто,Мякиш хлеба,Морской червь", 5, None),
                ("Морской петух", "Мифическая", 30.0, 180.0, 70, 230, 900, "Море", "Все", "Крупный живец,Туша рыбы,Кальмар,Морской червь", 75, None),
                ("Скорпена", "Редкая", 0.2, 2.0, 15, 40, 55, "Море", "Все", "Кусочки рыбы,Креветка,Живец,Морской червь", 12, None),
                ("Лихия", "Редкая", 3.0, 25.0, 40, 110, 150, "Море", "Весна,Лето,Осень", "Воблер,Живец,Сардина,Пилькер", 25, None),
                ("Сариола", "Редкая", 5.0, 40.0, 50, 150, 160, "Море", "Все", "Пилькер,Кальмар,Блесна,Живец", 25, None),
                ("Морской дракон", "Редкая", 0.1, 1.0, 10, 40, 55, "Море", "Все", "Морской червь,Опарыш,Креветка,Мотыль", 10, None),
                ("Анчоус", "Обычная", 0.01, 0.03, 5, 10, 4, "Море", "Все", "Опарыш,Тесто,Мякиш хлеба,Морской червь", 3, None),
                ("Шпрот", "Обычная", 0.01, 0.03, 5, 10, 4, "Море", "Все", "Мякиш хлеба,Тесто,Опарыш,Креветка", 3, None),
                ("Луна-рыба", "Легендарная", 30.0, 150.0, 60, 180, 550, "Море", "Лето,Осень", "Кальмар,Спрут,Сардина,Живец", 55, None),
                ("Каменный окунь", "Редкая", 0.2, 3.0, 15, 50, 60, "Море", "Все", "Креветка,Морской червь,Сало,Кусочки рыбы", 12, None),
                ("Морская лисица", "Редкая", 5.0, 60.0, 40, 180, 350, "Море", "Все", "Кусочки рыбы,Сало,Моллюск,Кальмар", 45, None),
                ("Морской черт", "Мифическая", 15.0, 100.0, 60, 200, 850, "Море", "Все", "Крупный живец,Туша рыбы,Кальмар,Спрут,Кусок мяса", 75, None),

                # ===== АКВАРИУМНЫЕ РЫБЫ =====
                ("Гуппи розовый", "Аквариумная", 0.01, 0.03, 2, 4, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Гуппи синий", "Аквариумная", 0.01, 0.03, 2, 4, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Скалярия мраморная", "Аквариумная", 0.1, 0.3, 5, 10, 20, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 3, None),
                ("Скалярия золотая", "Аквариумная", 0.1, 0.3, 5, 10, 20, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 3, None),
                ("Данио розовый", "Аквариумная", 0.01, 0.05, 2, 5, 8, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Данио леопардовый", "Аквариумная", 0.01, 0.05, 2, 5, 8, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Моллинезия черная", "Аквариумная", 0.05, 0.2, 3, 7, 12, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Моллинезия далматин", "Аквариумная", 0.05, 0.2, 3, 7, 12, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Петушок синий", "Аквариумная", 0.02, 0.08, 3, 6, 15, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Петушок мультиколор", "Аквариумная", 0.02, 0.08, 3, 6, 15, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Неон синий", "Аквариумная", 0.01, 0.03, 2, 4, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Неон красный", "Аквариумная", 0.01, 0.03, 2, 4, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Тернеция белая", "Аквариумная", 0.01, 0.04, 2, 5, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Тернеция голубая", "Аквариумная", 0.01, 0.04, 2, 5, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Барбус суматранский", "Аквариумная", 0.02, 0.08, 3, 6, 12, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Барбус зеленый", "Аквариумная", 0.02, 0.08, 3, 6, 12, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Гурами мраморный", "Аквариумная", 0.05, 0.15, 4, 8, 14, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотынет", 2, None),
                ("Гурами золотой", "Аквариумная", 0.05, 0.15, 4, 8, 14, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Пецилия красная", "Аквариумная", 0.01, 0.05, 2, 5, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),
                ("Пецилия желтая", "Аквариумная", 0.01, 0.05, 2, 5, 10, "Река,Озеро", "Все", "Манка,Тесто,Хлеб,Опарыш,Мотыль", 2, None),

                # ===== АНОМАЛИЯ =====
                ("Рыба-трамп", "Аномалия", 0.5, 2.0, 20, 40, 100, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
                ("Сакабамбаспис", "Аномалия", 0.3, 1.5, 15, 35, 90, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
                ("Плащеносная акула", "Аномалия", 1.0, 5.0, 30, 80, 120, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
                ("Рыба-капля", "Аномалия", 0.7, 3.0, 25, 50, 110, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
                ("Баррелей", "Аномалия", 0.2, 1.0, 10, 25, 80, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
                ("Черный живоглот", "Аномалия", 0.8, 4.0, 20, 45, 130, "Море", "Все", "Черви,Живец,Опарыш,Мотыль,Кусочки рыбы,Блесна,Воблер", 5, None),
            ]

            from fish_stickers import FISH_INFO

            bait_name_map = {name.lower(): name for name, _, _, _ in base_baits_data}

            def normalize_seasons(seasons_value: str) -> str:
                if not seasons_value:
                    return "Все"
                if "Круглый год" in seasons_value:
                    return "Все"
                parts = [s.strip() for s in seasons_value.split(',') if s.strip()]
                return ','.join(parts) if parts else "Все"

            def normalize_baits(nutrition_value: str) -> str:
                if not nutrition_value:
                    return "Все"
                raw_parts: List[str] = [p.strip() for p in nutrition_value.split(',') if p.strip()]
                normalized: List[str] = []
                for part in raw_parts:
                    lower = part.lower()
                    if lower in bait_name_map:
                        normalized.append(bait_name_map[lower])
                    else:
                        normalized.append(part[:1].upper() + part[1:])
                return ','.join(normalized) if normalized else "Все"

            normalized_fish_data = []
            for entry in fish_data:
                (name, rarity, min_weight, max_weight, min_length, max_length, price,
                 locations, seasons, suitable_baits, max_rod_weight, sticker_id) = entry
                required_level = 0
                info = FISH_INFO.get(name)
                if info:
                    # Сезоны берём из database.py (корректны по локации);
                    # FISH_INFO переопределял бы их одинаково для всех локаций
                    # из-за дублирующихся ключей (реки/озёра с одним именем).
                    suitable_baits = normalize_baits(info.get("nutrition", ""))
                normalized_fish_data.append((
                    name, rarity, min_weight, max_weight, min_length, max_length, price,
                    locations, seasons, suitable_baits, max_rod_weight, required_level, sticker_id
                ))
            fish_data = normalized_fish_data
            
            cursor.execute('DELETE FROM fish')
            cursor.executemany('''
                INSERT OR REPLACE INTO fish (name, rarity, min_weight, max_weight, min_length, max_length, price, locations, seasons, suitable_baits, max_rod_weight, required_level, sticker_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', fish_data)
            # Никакой рыбе не нужно набирать уровень — сбрасываем required_level в 0 для всех существующих записей
            cursor.execute('UPDATE fish SET required_level = 0')
            
            # Добавление мусора для реки
            trash_data = [
                ("Коряга", 0.5, 2, "Все", None),
                ("Старая шина", 2.0, 1, "Все", None),
                ("Консервная банка", 0.1, 1, "Все", None),
                ("Ботинок", 0.3, 2, "Все", None),
                ("Пластиковая бутылка", 0.05, 0, "Все", None),
                ("Ржавый крючок", 0.02, 5, "Все", None),
                ("Кусок трубы", 1.5, 3, "Все", None),
                ("Поломанная удочка", 1.0, 10, "Все", None),
                ("Рыболовная сетка", 0.8, 5, "Все", None),
                ("Деревянная доска", 2.5, 4, "Все", None),
                ("Старый якорь", 3.0, 15, "Все", None),
                ("Веревка", 0.3, 1, "Все", None),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO trash (name, weight, price, locations, sticker_id)
                VALUES (?, ?, ?, ?, ?)
            ''', trash_data)

            # Обновляем locations всех мусорных предметов до Все (чтобы они попадали в сеть на любой локации)
            cursor.execute("UPDATE trash SET locations = 'Все' WHERE locations = 'Река'")
            
            # Добавление сетей
            # Формат: (name, price, fish_count, cooldown_hours, max_uses, description)
            nets_data = [
                ("Базовая сеть", 0, 5, 24, -1, "Бесплатная сеть, можно использовать раз в 24 часа. Вытаскивает 5 рыб."),
                ("Прочная сеть", 300, 8, 24, 7, "Сеть на 7 использований. Можно использовать раз в 24 часа. Вытаскивает 8 рыб."),
                ("Быстрая сеть", 500, 5, 12, 14, "Сеть на 14 использований. Можно использовать раз в 12 часов. Вытаскивает 5 рыб."),
            ]
            
            cursor.executemany('''
                INSERT OR IGNORE INTO nets (name, price, fish_count, cooldown_hours, max_uses, description)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', nets_data)

            # Исправление перепутанных полей в caught_fish (локация/длина)
            cursor.execute('''
                UPDATE caught_fish
                SET location = CAST(length AS TEXT), length = 0
                WHERE location NOT IN (SELECT name FROM locations)
                  AND CAST(length AS TEXT) IN (SELECT name FROM locations)
            ''')

            # Одноразовый сброс рефералов (2026-02-06)
            cursor.execute("SELECT value FROM system_flags WHERE key = 'ref_reset_20260206'")
            if not cursor.fetchone():
                cursor.execute('UPDATE players SET ref = NULL')
                cursor.execute(
                    "INSERT INTO system_flags (key, value) VALUES (?, ?)",
                    ('ref_reset_20260206', '1')
                )

            # Одноразовая очистка реф-ссылок (2026-02-06)
            cursor.execute("SELECT value FROM system_flags WHERE key = 'ref_links_cleanup_20260206'")
            if not cursor.fetchone():
                cursor.execute('UPDATE players SET ref = NULL, ref_link = NULL')
                cursor.execute('DELETE FROM chat_configs')
                cursor.execute('DELETE FROM user_ref_links')
                cursor.execute(
                    "INSERT INTO system_flags (key, value) VALUES (?, ?)",
                    ('ref_links_cleanup_20260206', '1')
                )

            # Одноразовая миграция временных удочек (2026-02-10)
            cursor.execute("SELECT value FROM system_flags WHERE key = 'temp_rods_migrated_20260210'")
            if not cursor.fetchone():
                rod_names = list(TEMP_ROD_RANGES.keys())
                cursor.execute(
                    f"SELECT id, rod_name FROM player_rods WHERE rod_name IN ({','.join(['?'] * len(rod_names))})",
                    rod_names
                )
                rows = cursor.fetchall()
                for rod_id, rod_name in rows:
                    uses = self._get_temp_rod_uses(rod_name)
                    if uses is None:
                        continue
                    cursor.execute(
                        '''
                        UPDATE player_rods
                        SET current_durability = ?, max_durability = ?, recovery_start_time = NULL, last_repair_time = NULL
                        WHERE id = ?
                        ''',
                        (uses, uses, rod_id)
                    )
                cursor.execute(
                    "INSERT INTO system_flags (key, value) VALUES (?, ?)",
                    ('temp_rods_migrated_20260210', '1')
                )

            # Одноразовая миграция опыта и уровней (2026-02-08)
            cursor.execute("SELECT value FROM system_flags WHERE key = 'xp_levels_migrated_20260208'")
            if not cursor.fetchone():
                cursor.execute('''
                    SELECT cf.user_id,
                           cf.weight,
                           COALESCE(f.rarity, 'Мусор') AS rarity,
                           COALESCE(f.min_weight, 0) AS min_weight,
                           COALESCE(f.max_weight, 0) AS max_weight,
                           CASE WHEN f.name IS NULL THEN 1 ELSE 0 END AS is_trash
                    FROM caught_fish cf
                    LEFT JOIN fish f ON TRIM(cf.fish_name) = f.name
                    WHERE cf.sold = 1
                ''')
                rows = cursor.fetchall()

                xp_by_user: Dict[int, int] = {}
                for user_id, weight, rarity, min_weight, max_weight, is_trash in rows:
                    item = {
                        'weight': weight,
                        'rarity': rarity,
                        'min_weight': min_weight,
                        'max_weight': max_weight,
                        'is_trash': bool(is_trash),
                    }
                    xp_value = self.calculate_item_xp(item)
                    xp_by_user[user_id] = xp_by_user.get(user_id, 0) + xp_value

                for user_id, xp_value in xp_by_user.items():
                    cursor.execute(
                        'SELECT COALESCE(xp, 0) FROM players WHERE user_id = ? ORDER BY created_at DESC LIMIT 1',
                        (user_id,)
                    )
                    row = cursor.fetchone()
                    current_xp = row[0] if row else 0
                    new_xp = max(current_xp, xp_value)
                    new_level = self.get_level_from_xp(new_xp)
                    cursor.execute(
                        'UPDATE players SET xp = ?, level = ? WHERE user_id = ?',
                        (new_xp, new_level, user_id)
                    )

                cursor.execute(
                    "INSERT INTO system_flags (key, value) VALUES (?, ?)",
                    ('xp_levels_migrated_20260208', '1')
                )
            
            conn.commit()
            
            # Миграция существующих игроков - добавляем недостающие поля
            cursor.execute('''
                UPDATE players SET 
                    current_location = COALESCE(current_location, 'Городской пруд'),
                    current_bait = COALESCE(current_bait, 'Черви'),
                    current_rod = COALESCE(NULLIF(current_rod, ''), 'Бамбуковая удочка')
                WHERE current_location IS NULL
                   OR current_bait IS NULL
                   OR current_rod IS NULL
                   OR current_rod = ''
            ''')
            conn.commit()
    
    def get_player(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить данные игрока (единый профиль на все чаты)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # If players table contains chat-specific rows, prefer the row for this chat_id.
            cursor.execute("PRAGMA table_info(players)")
            cols = [c[1] for c in cursor.fetchall()]
            if 'chat_id' in cols:
                # Prefer a global profile row (chat_id IS NULL or < 1) which stores shared data
                cursor.execute('SELECT * FROM players WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) LIMIT 1', (user_id,))
                row = cursor.fetchone()
                if not row:
                    # No global profile yet — fallback to a per-chat row for compatibility
                    cursor.execute('SELECT * FROM players WHERE user_id = ? AND chat_id = ? LIMIT 1', (user_id, chat_id))
                    row = cursor.fetchone()
            else:
                cursor.execute('SELECT * FROM players WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user_id,))
                row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                player: Dict[str, Any] = dict(zip(columns, row))

                # Debug: log which chat_id row was returned and its last_fish_time
                try:
                    returned_chat = player.get('chat_id')
                    logger.debug("get_player: returned row for user=%s requested_chat=%s returned_chat=%s last_fish=%s",
                                 user_id, chat_id, returned_chat, player.get('last_fish_time'))
                except Exception:
                    logger.debug("get_player: returned row for user=%s requested_chat=%s (no chat column)", user_id, chat_id)

                # Обеспечиваем наличие полей по умолчанию
                if not player.get('current_location'):
                    player['current_location'] = 'Городской пруд'
                if not player.get('current_bait'):
                    player['current_bait'] = 'Черви'
                if not player.get('current_rod'):
                    player['current_rod'] = 'Бамбуковая удочка'
                    cursor.execute('''
                        UPDATE players SET current_rod = ?
                        WHERE user_id = ?
                    ''', (player['current_rod'], user_id))
                    conn.commit()

                if player.get('xp') is None:
                    player['xp'] = 0
                if player.get('level') is None:
                    player['level'] = 0
                if player.get('tickets') is None:
                    player['tickets'] = 0

                return player
            return None

    def has_any_player_profile(self, user_id: int) -> bool:
        """Проверить, есть ли профиль пользователя в любом чате"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM players WHERE user_id = ? LIMIT 1', (user_id,))
            return cursor.fetchone() is not None

    def has_any_referral(self, user_id: int) -> bool:
        """Проверить, является ли пользователь рефералом в любом чате"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM players WHERE user_id = ? AND ref IS NOT NULL LIMIT 1', (user_id,))
            return cursor.fetchone() is not None
    
    def create_player(self, user_id: int, username: str, chat_id: int) -> Optional[Dict[str, Union[str, int]]]:
        """Создать нового игрока (один профиль на все чаты)"""
        # If a profile for this exact (user_id, chat_id) exists, return it
        existing = self.get_player(user_id, chat_id)
        if existing:
            return existing

        # Try to copy values from any existing user profile to initialize a per-chat profile
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM players WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user_id,))
            row = cursor.fetchone()
            if row:
                cols = [description[0] for description in cursor.description]
                template = dict(zip(cols, row))
                coins = template.get('coins', 100)
                stars = template.get('stars', 0)
                tickets = template.get('tickets', 0)
                diamonds = template.get('diamonds', 0)
                xp = template.get('xp', 0)
                level = template.get('level', 0)
                dynamite_upgrade_level = template.get('dynamite_upgrade_level', 1)
                current_rod = template.get('current_rod', BAMBOO_ROD)
                current_bait = template.get('current_bait', 'Черви')
                current_location = template.get('current_location', 'Городской пруд')
            else:
                coins = 100
                stars = 0
                tickets = 0
                diamonds = 0
                xp = 0
                level = 0
                dynamite_upgrade_level = 1
                current_rod = BAMBOO_ROD
                current_bait = 'Черви'
                current_location = 'Городской пруд'

            # Create a GLOBAL profile row (chat_id = -1) to store shared player data
            cursor.execute('''
                INSERT INTO players (user_id, username, coins, stars, tickets, diamonds, xp, level, current_rod, current_bait, current_location, chat_id, dynamite_upgrade_level)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, -1, ?)
            ''', (user_id, username, coins, stars, tickets, diamonds, xp, level, current_rod, current_bait, current_location, dynamite_upgrade_level))
            conn.commit()

            # Инициализируем удочку и сеть для игрока в этом чате
            self.init_player_rod(user_id, current_rod, chat_id)
            self.init_player_net(user_id, 'Базовая сеть', chat_id)

            return self.get_player(user_id, chat_id)
    
    def update_player(self, user_id: int, chat_id: int, **kwargs: Dict[str, Union[str, int, float]]):
        """Обновить данные игрока (единый профиль на все чаты)"""
        if not kwargs:
            return

        # Allow only specific fields to be updated to avoid SQL injection
        allowed_fields = {
            'username', 'coins', 'stars', 'xp', 'level', 'current_rod', 'current_bait',
            'current_location', 'last_fish_time', 'last_boat_return_time', 'last_dynamite_use_time', 'dynamite_ban_until', 'is_banned', 'ban_until', 'ref', 'ref_link', 'last_net_use_time', 'diamonds', 'tickets', 'dynamite_upgrade_level'
        }

        # Prevent passing chat_id as a kwarg (it is a positional arg here)
        if 'chat_id' in kwargs:
            kwargs.pop('chat_id', None)

        update_keys = [k for k in kwargs.keys() if k in allowed_fields]
        if not update_keys:
            return

        set_clause = ', '.join([f"{k} = ?" for k in update_keys])
        values: List[Union[str, int, float]] = [kwargs[k] for k in update_keys]

        # Decide whether to include chat_id in WHERE depending on DB schema
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(players)")
            columns = [col[1] for col in cursor.fetchall()]
            uses_chat = 'chat_id' in columns

            if uses_chat:
                # Prefer updating the GLOBAL profile row (chat_id IS NULL or <1)
                sql = f'UPDATE players SET {set_clause} WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)'
                params = values + [user_id]
                cursor.execute(sql, params)
                if cursor.rowcount == 0:
                    # No global row — fall back to updating per-chat row
                    sql = f'UPDATE players SET {set_clause} WHERE user_id = ? AND chat_id = ?'
                    params = values + [user_id, chat_id]
            else:
                sql = f'UPDATE players SET {set_clause} WHERE user_id = ?'
                params = values + [user_id]

            # Defensive check -- ensure parameter count matches placeholders
            if sql.count('?') != len(params):
                # Log and adapt: try to trim trailing None values if any
                logger.error("Binding mismatch preparing UPDATE players: %s params=%s", sql, params)
                # Attempt best-effort: trim params to match
                if len(params) > sql.count('?'):
                    params = params[:sql.count('?')]
            cursor.execute(sql, params)
            conn.commit()
            # Log update result for debugging cooldown issues
            try:
                logger.debug("update_player: user=%s chat=%s sql=%s params=%s rows=%s",
                             user_id, chat_id, sql, params, cursor.rowcount)
            except Exception:
                logger.debug("update_player executed")

    def add_diamonds(self, user_id: int, chat_id: int, amount: int = 1):
        """Увеличить количество бриллиантов у игрока на amount (без отрицательных значений)"""
        try:
            amount = int(amount)
        except Exception:
            return
        if amount == 0:
            return

        player = self.get_player(user_id, chat_id)
        current = int(player.get('diamonds', 0)) if player else 0
        new = current + amount
        # Use update_player which respects global/per-chat rows
        try:
            self.update_player(user_id, chat_id, diamonds=new)
        except Exception:
            logger.exception('add_diamonds failed for user=%s chat=%s amount=%s', user_id, chat_id, amount)

    def subtract_diamonds(self, user_id: int, chat_id: int, amount: int = 1):
        """Уменьшить количество бриллиантов у игрока на amount; не допускает отрицательных значений"""
        try:
            amount = int(amount)
        except Exception:
            return
        if amount == 0:
            return

        player = self.get_player(user_id, chat_id)
        current = int(player.get('diamonds', 0)) if player else 0
        new = max(0, current - amount)
        try:
            self.update_player(user_id, chat_id, diamonds=new)
        except Exception:
            logger.exception('subtract_diamonds failed for user=%s chat=%s amount=%s', user_id, chat_id, amount)

    def get_dynamite_upgrade_level(self, user_id: int, chat_id: int) -> int:
        """Получить уровень апгрейда динамита: 1=динамит, 2=граната, 3=бомба."""
        player = self.get_player(user_id, chat_id)
        level_raw = player.get('dynamite_upgrade_level', 1) if player else 1

        try:
            level = int(level_raw)
        except Exception:
            level = 1

        if level < 1:
            level = 1
        if level > 3:
            level = 3

        return level

    def set_dynamite_upgrade_level(self, user_id: int, chat_id: int, level: int) -> int:
        """Установить уровень апгрейда динамита и вернуть применённое значение."""
        try:
            normalized = int(level)
        except Exception:
            normalized = 1

        normalized = max(1, min(3, normalized))
        self.update_player(user_id, chat_id, dynamite_upgrade_level=normalized)
        return normalized

    def get_player_clothing(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить список купленной одежды игрока."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT item_key, display_name, bonus_percent, purchased_at
                FROM player_clothing
                WHERE user_id = ?
                ORDER BY bonus_percent DESC, purchased_at ASC
                ''',
                (user_id,),
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def has_clothing_item(self, user_id: int, item_key: str) -> bool:
        """Проверить, куплен ли предмет одежды."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM player_clothing WHERE user_id = ? AND item_key = ? LIMIT 1',
                (user_id, str(item_key or '').strip().lower()),
            )
            return cursor.fetchone() is not None

    def get_clothing_bonus_percent(self, user_id: int) -> float:
        """Суммарный перманентный бонус от одежды в процентах."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COALESCE(SUM(bonus_percent), 0) FROM player_clothing WHERE user_id = ?',
                (user_id,),
            )
            row = cursor.fetchone()
            return float((row[0] if row else 0.0) or 0.0)

    def purchase_clothing_item(
        self,
        user_id: int,
        chat_id: int,
        item_key: str,
        display_name: str,
        bonus_percent: float,
        cost_diamonds: int,
    ) -> Dict[str, Any]:
        """Купить предмет одежды за бриллианты (атомарно)."""
        normalized_key = str(item_key or '').strip().lower()
        if not normalized_key:
            return {"ok": False, "reason": "invalid_item"}

        try:
            normalized_cost = max(0, int(cost_diamonds))
        except Exception:
            normalized_cost = 0

        try:
            normalized_bonus = max(0.0, float(bonus_percent))
        except Exception:
            normalized_bonus = 0.0

        try:
            with self._connect() as conn:
                cursor = conn.cursor()

                cursor.execute(
                    'SELECT 1 FROM player_clothing WHERE user_id = ? AND item_key = ? LIMIT 1',
                    (user_id, normalized_key),
                )
                if cursor.fetchone():
                    return {"ok": False, "reason": "already_owned"}

                cursor.execute("PRAGMA table_info(players)")
                columns = [col[1] for col in cursor.fetchall()]
                uses_chat = 'chat_id' in columns

                if uses_chat:
                    cursor.execute(
                        '''
                        SELECT diamonds
                        FROM players
                        WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)
                        ORDER BY created_at DESC
                        LIMIT 1
                        ''',
                        (user_id,),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        cursor.execute(
                            '''
                            SELECT diamonds
                            FROM players
                            WHERE user_id = ? AND chat_id = ?
                            ORDER BY created_at DESC
                            LIMIT 1
                            ''',
                            (user_id, chat_id),
                        )
                        row = cursor.fetchone()
                else:
                    cursor.execute(
                        '''
                        SELECT diamonds
                        FROM players
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT 1
                        ''',
                        (user_id,),
                    )
                    row = cursor.fetchone()

                if row is None:
                    return {"ok": False, "reason": "no_player"}

                current_diamonds = int((row[0] if row[0] is not None else 0) or 0)
                if current_diamonds < normalized_cost:
                    return {
                        "ok": False,
                        "reason": "not_enough_diamonds",
                        "diamonds": current_diamonds,
                        "cost": normalized_cost,
                    }

                new_diamonds = current_diamonds - normalized_cost

                cursor.execute(
                    '''
                    INSERT INTO player_clothing (user_id, item_key, display_name, bonus_percent)
                    VALUES (?, ?, ?, ?)
                    ''',
                    (user_id, normalized_key, str(display_name or normalized_key), normalized_bonus),
                )

                if uses_chat:
                    cursor.execute(
                        'UPDATE players SET diamonds = ? WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)',
                        (new_diamonds, user_id),
                    )
                    if cursor.rowcount == 0:
                        cursor.execute(
                            'UPDATE players SET diamonds = ? WHERE user_id = ? AND chat_id = ?',
                            (new_diamonds, user_id, chat_id),
                        )
                    if cursor.rowcount == 0:
                        raise RuntimeError('Failed to update player diamonds for clothing purchase')
                else:
                    cursor.execute(
                        'UPDATE players SET diamonds = ? WHERE user_id = ?',
                        (new_diamonds, user_id),
                    )
                    if cursor.rowcount == 0:
                        raise RuntimeError('Failed to update player diamonds for clothing purchase')

                cursor.execute(
                    'SELECT COALESCE(SUM(bonus_percent), 0) FROM player_clothing WHERE user_id = ?',
                    (user_id,),
                )
                total_row = cursor.fetchone()
                total_bonus = float((total_row[0] if total_row else 0.0) or 0.0)

                conn.commit()
                return {
                    "ok": True,
                    "reason": "purchased",
                    "new_diamonds": new_diamonds,
                    "cost": normalized_cost,
                    "item_bonus_percent": normalized_bonus,
                    "total_bonus_percent": total_bonus,
                }
        except Exception:
            logger.exception('purchase_clothing_item failed for user=%s item=%s', user_id, normalized_key)
            try:
                if self.has_clothing_item(user_id, normalized_key):
                    return {"ok": False, "reason": "already_owned"}
            except Exception:
                pass
            return {"ok": False, "reason": "db_error"}

    def get_fish_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Получить данные рыбы по её имени."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM fish WHERE name = ? LIMIT 1", (name,))
            row = cursor.fetchone()
            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))
            return None

    def get_fish_by_location(self, location: str, season: str = "Лето", min_level: Optional[int] = None) -> List[Dict[str, Union[str, int, float]]]:
        """Получить список рыб для локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM fish 
                WHERE locations LIKE ? AND (seasons LIKE ? OR seasons LIKE '%Все%')
            '''
            params: List[Union[str, int]] = [f"%{location}%", f"%{season}%"]
            # min_level игнорируется: никакой рыбе не нужно уровень
            query += " ORDER BY rarity"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_fish_by_location_any_season(self, location: str, min_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить список рыб для локации без учета сезона"""
        with self._connect() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT * FROM fish 
                WHERE locations LIKE ?
            '''
            params: List[Union[str, int]] = [f"%{location}%"]
            # min_level игнорируется: никакой рыбе не нужно уровень
            query += " ORDER BY rarity"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def get_random_fish(self, location: str, season: str = "Лето", bait_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Получить случайную рыбу для локации с учетом наживки"""
        fish_list = self.get_fish_by_location(location, season)
        if not fish_list:
            return None

        if bait_name:
            fish_list = [fish for fish in fish_list if self.check_bait_suitable_for_fish(bait_name, fish['name'])]
            if not fish_list:
                return None
        
        # Взвешенный случайный выбор с учетом редкости
        weights = self.calculate_weights(fish_list)

        import random
        return random.choices(fish_list, weights=weights)[0]

    def get_fish_for_location(self, location: str, season: str = "Лето", min_level: Optional[int] = None) -> List[Dict[str, Any]]:
        """Совместимость со старым API game_logic: вернуть рыбу по локации."""
        return self.get_fish_by_location(location, season, min_level=min_level)
    
    def add_caught_fish(self, user_id: int, chat_id: int, fish_name: str, weight: float, location: str, length: float = 0):
        """Добавить пойманную рыбу"""
        normalized_name = fish_name.strip() if isinstance(fish_name, str) else fish_name
        # Normalize fish_name to canonical name from `fish` table when possible
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                # Try exact match on trimmed lowercase name
                cur.execute("SELECT name FROM fish WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) LIMIT 1", (normalized_name,))
                r = cur.fetchone()
                if r:
                    normalized_name = r[0]
        except Exception:
            # If normalization fails, continue with provided name
            pass
        try:
            chat_id_to_store = int(chat_id) if chat_id else 0
        except (TypeError, ValueError):
            chat_id_to_store = 0

        logger.info(
            "add_caught_fish INPUT: user_id=%s chat_id=%s (raw=%s, type=%s) fish=%s weight=%s length=%s location=%s",
            user_id, chat_id_to_store, chat_id, type(chat_id).__name__,
            normalized_name, weight, length, location
        )

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO caught_fish (user_id, chat_id, fish_name, weight, length, location)'
                ' VALUES (%s, %s, %s, %s, %s, %s)'
                ' RETURNING id, user_id, chat_id, fish_name, weight, length, location, caught_at',
                (user_id, chat_id_to_store, normalized_name, float(weight), float(length), location)
            )
            saved = cursor.fetchone()

        if saved:
            logger.info(
                "add_caught_fish SAVED IN DB: id=%s user_id=%s chat_id=%s fish=%s weight=%s length=%s location=%s caught_at=%s",
                saved[0], saved[1], saved[2], saved[3], saved[4], saved[5], saved[6], saved[7]
            )
            return {
                'id': saved[0],
                'user_id': saved[1],
                'chat_id': saved[2],
                'fish_name': saved[3],
                'weight': saved[4],
                'length': saved[5],
                'location': saved[6],
                'caught_at': saved[7],
            }
        else:
            logger.warning(
                "add_caught_fish: INSERT returned no row — possible constraint violation. user_id=%s chat_id=%s fish=%s",
                user_id, chat_id_to_store, normalized_name
            )
            return None

    def add_caught_fish_owner_manual(
        self,
        user_id: int,
        fish_name: str,
        location: str,
        weight: float,
        length: float,
        caught_at: Optional[datetime] = None,
    ) -> Optional[Dict[str, Any]]:
        """Ручная owner-вставка в caught_fish: chat_id=-1, sold=0, caught_at задаётся явно."""
        normalized_name = fish_name.strip() if isinstance(fish_name, str) else fish_name
        normalized_location = location.strip() if isinstance(location, str) else location

        # Normalize fish_name to canonical name from `fish` table when possible.
        try:
            with self._connect() as conn:
                cur = conn.cursor()
                cur.execute("SELECT name FROM fish WHERE LOWER(TRIM(name)) = LOWER(TRIM(?)) LIMIT 1", (normalized_name,))
                row = cur.fetchone()
                if row and row[0]:
                    normalized_name = row[0]
        except Exception:
            pass

        try:
            uid = int(user_id)
        except (TypeError, ValueError):
            logger.warning("add_caught_fish_owner_manual: invalid user_id=%s", user_id)
            return None

        chat_id_to_store = -1

        try:
            weight_value = float(weight)
            length_value = float(length)
        except (TypeError, ValueError):
            logger.warning("add_caught_fish_owner_manual: invalid weight/length: weight=%s length=%s", weight, length)
            return None

        event_time = caught_at or datetime.utcnow()
        caught_at_value = event_time.isoformat() if isinstance(event_time, datetime) else str(event_time)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'INSERT INTO caught_fish (user_id, chat_id, fish_name, weight, length, location, caught_at, sold) '
                'VALUES (%s, %s, %s, %s, %s, %s, %s, 0) '
                'RETURNING id, user_id, chat_id, fish_name, weight, length, location, caught_at, sold',
                (uid, chat_id_to_store, normalized_name, weight_value, length_value, normalized_location, caught_at_value)
            )
            saved = cursor.fetchone()

        if not saved:
            logger.warning(
                "add_caught_fish_owner_manual: insert returned no row user_id=%s fish=%s",
                uid,
                normalized_name,
            )
            return None

        logger.info(
            "add_caught_fish_owner_manual saved: id=%s user_id=%s chat_id=%s fish=%s weight=%s length=%s location=%s caught_at=%s sold=%s",
            saved[0], saved[1], saved[2], saved[3], saved[4], saved[5], saved[6], saved[7], saved[8]
        )

        return {
            'id': saved[0],
            'user_id': saved[1],
            'chat_id': saved[2],
            'fish_name': saved[3],
            'weight': saved[4],
            'length': saved[5],
            'location': saved[6],
            'caught_at': saved[7],
            'sold': saved[8],
        }
    
    def remove_caught_fish(self, fish_id: int):
        """Удалить пойманную рыбу по ID"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM caught_fish WHERE id = ?', (fish_id,))
            conn.commit()

    def _resolve_fish_image_file(self, fish_name: str) -> str:
        default_image = 'fishdef.webp'
        if not fish_name:
            return default_image

        try:
            from fish_stickers import FISH_STICKERS
            image_file = FISH_STICKERS.get(str(fish_name).strip())
            if image_file:
                return str(image_file)
        except Exception:
            pass

        return default_image

    def get_player_trophies(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить все трофеи игрока."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, user_id, fish_name, weight, length, location, image_file, is_active, created_at
                FROM player_trophies
                WHERE user_id = ?
                ORDER BY is_active DESC, created_at DESC, id DESC
                ''',
                (int(user_id),)
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_active_trophy(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить активный трофей игрока (или последний, если активный не выбран)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, user_id, fish_name, weight, length, location, image_file, is_active, created_at
                FROM player_trophies
                WHERE user_id = ? AND COALESCE(is_active, 0) = 1
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (int(user_id),)
            )
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))

            cursor.execute(
                '''
                SELECT id, user_id, fish_name, weight, length, location, image_file, is_active, created_at
                FROM player_trophies
                WHERE user_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                ''',
                (int(user_id),)
            )
            row = cursor.fetchone()
            if not row:
                return None

            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    def set_active_trophy(self, user_id: int, trophy_id: int) -> bool:
        """Установить активный трофей игрока."""
        uid = int(user_id)
        tid = int(trophy_id)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT 1 FROM player_trophies WHERE id = ? AND user_id = ? LIMIT 1',
                (tid, uid)
            )
            if not cursor.fetchone():
                return False

            cursor.execute('UPDATE player_trophies SET is_active = 0 WHERE user_id = ?', (uid,))
            cursor.execute('UPDATE player_trophies SET is_active = 1 WHERE id = ? AND user_id = ?', (tid, uid))
            conn.commit()
            return True

    def create_trophy_from_catch(self, user_id: int, chat_id: int, caught_fish_id: int, cost_coins: int = 10000) -> Dict[str, Any]:
        """Создать трофей из пойманной рыбы: списать монеты, удалить рыбу из инвентаря, сохранить трофей."""
        uid = int(user_id)
        cid = int(chat_id)
        fid = int(caught_fish_id)
        cost = max(0, int(cost_coins))

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT coins
                FROM players
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)
                LIMIT 1
                ''',
                (uid,)
            )
            player_row = cursor.fetchone()
            use_global_player_row = bool(player_row)

            if not player_row:
                cursor.execute(
                    'SELECT coins FROM players WHERE user_id = ? AND chat_id = ? LIMIT 1',
                    (uid, cid)
                )
                player_row = cursor.fetchone()

            if not player_row:
                return {'ok': False, 'error': 'profile_not_found'}

            current_coins = int(player_row[0] or 0)
            if current_coins < cost:
                return {
                    'ok': False,
                    'error': 'insufficient_coins',
                    'balance': current_coins,
                    'required': cost,
                }

            cursor.execute(
                '''
                SELECT id, fish_name, weight, length, location
                FROM caught_fish
                WHERE id = ? AND user_id = ? AND COALESCE(sold, 0) = 0
                LIMIT 1
                ''',
                (fid, uid)
            )
            fish_row = cursor.fetchone()

            if not fish_row:
                return {'ok': False, 'error': 'fish_not_found'}

            fish_name = str(fish_row[1] or '').strip()
            fish_weight = float(fish_row[2] or 0)
            fish_length = float(fish_row[3] or 0)
            fish_location = str(fish_row[4] or '').strip()
            image_file = self._resolve_fish_image_file(fish_name)

            cursor.execute('SELECT 1 FROM player_trophies WHERE user_id = ? LIMIT 1', (uid,))
            has_any_trophy = bool(cursor.fetchone())
            should_be_active = 0 if has_any_trophy else 1

            cursor.execute(
                '''
                INSERT INTO player_trophies (
                    user_id, fish_name, weight, length, location, image_file, is_active, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                RETURNING id, user_id, fish_name, weight, length, location, image_file, is_active, created_at
                ''',
                (uid, fish_name, fish_weight, fish_length, fish_location, image_file, should_be_active)
            )
            trophy_row = cursor.fetchone()

            cursor.execute('DELETE FROM caught_fish WHERE id = ? AND user_id = ?', (fid, uid))

            new_balance = current_coins - cost
            if use_global_player_row:
                cursor.execute(
                    '''
                    UPDATE players
                    SET coins = ?
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)
                    ''',
                    (new_balance, uid)
                )
                if getattr(cursor, 'rowcount', 0) == 0:
                    cursor.execute(
                        'UPDATE players SET coins = ? WHERE user_id = ? AND chat_id = ?',
                        (new_balance, uid, cid)
                    )
            else:
                cursor.execute(
                    'UPDATE players SET coins = ? WHERE user_id = ? AND chat_id = ?',
                    (new_balance, uid, cid)
                )

            conn.commit()

            if not trophy_row:
                return {'ok': False, 'error': 'trophy_insert_failed'}

            columns = ['id', 'user_id', 'fish_name', 'weight', 'length', 'location', 'image_file', 'is_active', 'created_at']
            trophy = dict(zip(columns, trophy_row))
            return {
                'ok': True,
                'trophy': trophy,
                'new_balance': new_balance,
                'cost': cost,
            }

    def rollback_reward_after_raf_win(self, user_id: int, chat_id: int, result: Dict[str, Any]) -> Dict[str, Any]:
        """Откатывает улов/награды, если вместо улова выпал RAF-приз."""
        info: Dict[str, Any] = {
            'boat_catch_removed': False,
            'caught_fish_removed': False,
            'coins_reverted': 0,
            'treasure_removed': False,
        }

        fish_data = result.get('fish') or {}
        trash_data = result.get('trash') or {}
        is_trash = bool(result.get('is_trash'))

        item_name = ''
        item_weight = 0.0
        if is_trash:
            item_name = str(trash_data.get('name') or '').strip()
            try:
                item_weight = float(trash_data.get('weight') or 0)
            except (TypeError, ValueError):
                item_weight = 0.0
        elif result.get('success') and fish_data:
            item_name = str(fish_data.get('name') or '').strip()
            try:
                item_weight = float(result.get('weight') or 0)
            except (TypeError, ValueError):
                item_weight = 0.0

        location = str(result.get('location') or '').strip()
        is_on_boat = bool(result.get('is_on_boat')) or self.is_user_on_boat_trip(int(user_id))

        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                if is_on_boat and item_name:
                    cursor.execute(
                        '''
                        SELECT bc.id, bc.boat_id, COALESCE(bc.weight, 0)
                        FROM boat_catch bc
                        JOIN boat_members bm ON bm.boat_id = bc.boat_id
                        WHERE bm.user_id = ?
                          AND COALESCE(bc.user_id, 0) = ?
                          AND LOWER(TRIM(COALESCE(bc.item_name, ''))) = LOWER(TRIM(?))
                          AND (? = '' OR LOWER(TRIM(COALESCE(bc.location, ''))) = LOWER(TRIM(?)))
                        ORDER BY bc.id DESC
                        LIMIT 1
                        ''',
                        (int(user_id), int(user_id), item_name, location, location),
                    )
                    boat_row = cursor.fetchone()
                    if boat_row:
                        boat_catch_id = int(boat_row[0])
                        boat_id = int(boat_row[1])
                        removed_weight = float(boat_row[2] or item_weight or 0)
                        cursor.execute('DELETE FROM boat_catch WHERE id = ?', (boat_catch_id,))
                        cursor.execute(
                            '''
                            UPDATE boats
                            SET current_weight = CASE WHEN current_weight - ? > 0 THEN current_weight - ? ELSE 0 END
                            WHERE id = ?
                            ''',
                            (removed_weight, removed_weight, boat_id),
                        )
                        info['boat_catch_removed'] = True

                if (not is_on_boat) and result.get('success') and fish_data and item_name:
                    cursor.execute(
                        '''
                        SELECT id
                        FROM caught_fish
                        WHERE user_id = ?
                          AND chat_id = ?
                          AND COALESCE(sold, 0) = 0
                          AND LOWER(TRIM(COALESCE(fish_name, ''))) = LOWER(TRIM(?))
                          AND (? = '' OR LOWER(TRIM(COALESCE(location, ''))) = LOWER(TRIM(?)))
                        ORDER BY id DESC
                        LIMIT 1
                        ''',
                        (int(user_id), int(chat_id), item_name, location, location),
                    )
                    fish_row = cursor.fetchone()
                    if fish_row:
                        cursor.execute('DELETE FROM caught_fish WHERE id = ?', (int(fish_row[0]),))
                        info['caught_fish_removed'] = True

                coins_to_revert = 0
                if not is_on_boat:
                    if is_trash:
                        try:
                            coins_to_revert = int(round(float(result.get('earned') or trash_data.get('price') or 0)))
                        except (TypeError, ValueError):
                            coins_to_revert = 0
                    elif result.get('success') and fish_data and bool(result.get('guaranteed')):
                        try:
                            coins_to_revert = int(round(float(result.get('earned') or 0)))
                        except (TypeError, ValueError):
                            coins_to_revert = 0

                if coins_to_revert > 0:
                    cursor.execute(
                        '''
                        UPDATE players
                        SET coins = CASE WHEN COALESCE(coins, 0) - ? > 0 THEN COALESCE(coins, 0) - ? ELSE 0 END
                        WHERE user_id = ? AND chat_id = ?
                        ''',
                        (coins_to_revert, coins_to_revert, int(user_id), int(chat_id)),
                    )
                    info['coins_reverted'] = coins_to_revert

                treasure_name = str(result.get('treasure_name') or '').strip()
                if treasure_name:
                    cursor.execute(
                        '''
                        UPDATE player_treasures
                        SET quantity = CASE WHEN quantity - 1 > 0 THEN quantity - 1 ELSE 0 END
                        WHERE user_id = ?
                          AND chat_id = ?
                          AND treasure_name = ?
                          AND quantity > 0
                        ''',
                        (int(user_id), int(chat_id), treasure_name),
                    )
                    info['treasure_removed'] = bool(getattr(cursor, 'rowcount', 0))

                conn.commit()
            except Exception:
                logger.exception("rollback_reward_after_raf_win failed for user=%s chat=%s", user_id, chat_id)
                try:
                    conn.rollback()
                except Exception:
                    pass

        return info
    
    def mark_fish_as_sold(self, fish_ids: List[int]):
        """Пометить рыбу как проданную"""
        if not fish_ids:
            return

        # Some DB drivers (SQLite) have a limit on the number of bound parameters
        # allowed in a single statement. To be robust when selling many items at
        # once, perform the update in chunks.
        chunk_size = 500
        with self._connect() as conn:
            cursor = conn.cursor()
            total_updated = 0
            sales_to_record: List[Dict[str, Any]] = []
            for i in range(0, len(fish_ids), chunk_size):
                chunk = fish_ids[i:i + chunk_size]
                placeholders = ','.join('?' * len(chunk))

                # Для динамических цен учитываем только реальную рыбу (не мусор).
                cursor.execute(
                    f'''
                    SELECT cf.fish_name, COALESCE(cf.weight, 0)
                    FROM caught_fish cf
                    JOIN fish f ON LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(f.name))
                    WHERE cf.id IN ({placeholders}) AND COALESCE(cf.sold, 0) = 0
                    ''',
                    chunk,
                )
                pre_sale_rows = cursor.fetchall() or []

                cursor.execute(f'''
                    UPDATE caught_fish 
                    SET sold = 1, sold_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders})
                ''', chunk)
                try:
                    updated = cursor.rowcount if hasattr(cursor, 'rowcount') else -1
                except Exception:
                    updated = -1
                if isinstance(updated, int) and updated > 0:
                    total_updated += updated
                    for fish_name, fish_weight in pre_sale_rows:
                        sales_to_record.append({
                            'fish_name': str(fish_name or ''),
                            'weight': float(fish_weight or 0.0),
                        })
                logger.info("mark_fish_as_sold: chunk %s-%s updated %s rows", i, i+len(chunk)-1, updated)

            if sales_to_record:
                for sale in sales_to_record:
                    cursor.execute(
                        '''
                        INSERT INTO fish_sales_history (fish_name, weight, sold_at)
                        VALUES (?, ?, CURRENT_TIMESTAMP)
                        ''',
                        (sale['fish_name'], sale['weight']),
                    )

                day_key = datetime.utcnow().date().isoformat()
                cursor.execute(
                    '''
                    SELECT id, fish_name, sold_weight, target_weight
                    FROM daily_fish_market
                    WHERE market_day = ?
                    LIMIT 1
                    ''',
                    (day_key,),
                )
                market_row = cursor.fetchone()
                if market_row:
                    market_id = int(market_row[0])
                    market_fish_name = self._normalize_item_name(market_row[1])
                    sold_weight = float(market_row[2] or 0.0)
                    target_weight = float(market_row[3] or 0.0)

                    sold_add = 0.0
                    for sale in sales_to_record:
                        if self._normalize_item_name(sale['fish_name']) == market_fish_name:
                            sold_add += float(sale['weight'] or 0.0)

                    if sold_add > 0:
                        new_sold_weight = min(target_weight, sold_weight + sold_add)
                        cursor.execute(
                            '''
                            UPDATE daily_fish_market
                            SET sold_weight = ?
                            WHERE id = ?
                            ''',
                            (new_sold_weight, market_id),
                        )

            conn.commit()
            logger.info("mark_fish_as_sold: total ids=%s total_updated=%s", len(fish_ids), total_updated)
    
    def get_player_stats(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Получить статистику игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Общая статистика
            cursor.execute('''
                SELECT COUNT(*) as total_fish, 
                       SUM(weight) as total_weight,
                       COUNT(DISTINCT fish_name) as unique_fish
                FROM caught_fish cf
                JOIN fish f ON TRIM(cf.fish_name) = f.name
                WHERE cf.user_id = ?
            ''', (user_id,))
            
            stats = cursor.fetchone()

            cursor.execute('''
                SELECT COALESCE(SUM(cf.weight), 0) as trash_weight
                FROM caught_fish cf
                LEFT JOIN fish f ON TRIM(cf.fish_name) = f.name
                WHERE cf.user_id = ? AND f.name IS NULL
            ''', (user_id,))
            trash_weight_row = cursor.fetchone()
            trash_weight = trash_weight_row[0] if trash_weight_row else 0

            cursor.execute('''
                SELECT COUNT(*), COALESCE(SUM(cf.weight), 0)
                FROM caught_fish cf
                JOIN fish f ON TRIM(cf.fish_name) = f.name
                WHERE cf.user_id = ? AND cf.sold = 1
            ''', (user_id,))
            sold_row = cursor.fetchone()
            sold_count = sold_row[0] if sold_row else 0
            sold_weight = sold_row[1] if sold_row else 0
            
            # Самая большая рыба
            cursor.execute('''
                SELECT fish_name, weight FROM caught_fish 
                                WHERE user_id = ?
                                    AND TRIM(fish_name) IN (SELECT name FROM fish)
                                ORDER BY weight DESC LIMIT 1
                        ''', (user_id,))
            
            biggest = cursor.fetchone()
            
            return {
                'total_fish': stats[0] or 0,
                'total_weight': stats[1] or 0,
                'unique_fish': stats[2] or 0,
                'biggest_fish': biggest[0] if biggest else None,
                'biggest_weight': biggest[1] if biggest else 0,
                'trash_weight': trash_weight or 0,
                'sold_fish_count': sold_count or 0,
                'sold_fish_weight': sold_weight or 0
            }

    def get_total_fish_species(self) -> int:
        """Возвращает общее количество видов рыб в каталоге."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM fish')
            row = cursor.fetchone()
            return row[0] if row else 0

    def get_rod(self, rod_name: str) -> Optional[Dict[str, Any]]:
        """Получить информацию об удочке"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rods WHERE name = ?', (rod_name,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
    
    def get_rod_by_id(self, rod_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию об удочке по ID"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rods WHERE id = ?', (rod_id,))
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
    
    def get_location(self, location_name: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM locations WHERE name = ?', (location_name,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def update_location_players(self, location_name: str, delta: int):
        """Обновить количество игроков на локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE locations SET current_players = current_players + ? 
                WHERE name = ?
            ''', (delta, location_name))
            conn.commit()
    
    def update_player_location(self, user_id: int, chat_id: int, location_name: str):
        """Обновить локацию игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players SET current_location = ? WHERE user_id = ?
            ''', (location_name, user_id))
            conn.commit()
    
    def update_player_bait(self, user_id: int, chat_id: int, bait_name: str):
        """Обновить наживку игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players SET current_bait = ? WHERE user_id = ?
            ''', (bait_name, user_id))
            conn.commit()
    
    def buy_rod(self, user_id: int, chat_id: int, rod_name: str) -> bool:
        """Купить удочку"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Проверяем баланс и текущую удочку
            cursor.execute('''
                SELECT p.coins, r.price FROM players p
                JOIN rods r ON r.name = ?
                WHERE p.user_id = ?
            ''', (rod_name, user_id))
            
            result = cursor.fetchone()
            if not result:
                return False
            
            player_coins, rod_price = result
            
            if player_coins < rod_price:
                return False
            
            # Списываем монеты и обновляем удочку
            cursor.execute('''
                UPDATE players 
                SET coins = coins - ?, current_rod = ?
                WHERE user_id = ?
            ''', (rod_price, rod_name, user_id))
            
            conn.commit()
            self.init_player_rod(user_id, rod_name, chat_id)
            return True
    
    def clear_cooldown(self, user_id: int, chat_id: int) -> bool:
        """Очистить кулдаун рыбалки (старый метод для совместимости)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Очистка кулдауна
            cursor.execute('''
                UPDATE players 
                SET last_fish_time = NULL
                WHERE user_id = ?
            ''', (user_id,))
            
            conn.commit()
            return True
    
    def get_caught_fish(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Получить всю пойманную рыбу пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Do NOT mutate DB when reading caught_fish (was assigning missing chat_id to current chat)
            # Previously this code updated rows with NULL/invalid chat_id to the current chat_id here,
            # which caused old catches to be retroactively reassigned when a user viewed `/stats`.
            # Keep reads side-effect free; use tools/fix_caught_fish_chatid.py or admin commands
            # to perform any explicit normalization instead.
            #
            # JOIN uses LOWER(TRIM(...)) for case-insensitive matching so that fish stored with
            # minor casing differences still resolve correctly from the fish/trash catalogs.
            # trash_name is included to distinguish actual trash (t.name IS NOT NULL) from a
            # failed JOIN with the fish table (both f.name and t.name are NULL).
            cursor.execute('''
                SELECT cf.*, 
                       COALESCE(f.name, t.name) AS name,
                       COALESCE(f.rarity, 'Мусор') AS rarity,
                       COALESCE(f.price, t.price, 0) AS price,
                       f.min_weight AS min_weight,
                       f.max_weight AS max_weight,
                       f.min_length AS min_length,
                       f.max_length AS max_length,
                       CASE WHEN f.name IS NULL THEN 1 ELSE 0 END AS is_trash,
                       t.name AS trash_name
                FROM caught_fish cf
                LEFT JOIN fish f ON LOWER(TRIM(cf.fish_name)) = LOWER(f.name)
                LEFT JOIN trash t ON LOWER(TRIM(cf.fish_name)) = LOWER(t.name)
                WHERE cf.user_id = ? AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                ORDER BY cf.weight DESC
            ''', (user_id, chat_id))
            
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            results = [dict(zip(columns, row)) for row in rows]

            # Collect items where the JOIN failed (is_trash=1 meaning f.name IS NULL,
            # AND trash_name IS NULL meaning not in trash table either).
            # These are real fish whose names don't match due to encoding/case differences.
            # We do a single batch secondary lookup to recover their catalog data.
            orphan_indices = [
                i for i, item in enumerate(results)
                if item.get('is_trash') and item.get('trash_name') is None
            ]
            if orphan_indices:
                orphan_names = [results[i].get('fish_name', '') for i in orphan_indices]
                try:
                    placeholders = ','.join(['?' for _ in orphan_names])
                    cursor.execute(
                        f"SELECT name, rarity, price, min_weight, max_weight, min_length, max_length "
                        f"FROM fish WHERE LOWER(name) IN ({placeholders})",
                        [n.lower().strip() for n in orphan_names]
                    )
                    lookup_rows = cursor.fetchall()
                    fish_by_lower = {}
                    for row in lookup_rows:
                        fish_by_lower[str(row[0]).lower()] = {
                            'rarity': row[1], 'price': row[2],
                            'min_weight': row[3], 'max_weight': row[4],
                            'min_length': row[5], 'max_length': row[6],
                        }
                    for i in orphan_indices:
                        item = results[i]
                        key = str(item.get('fish_name', '')).lower().strip()
                        fish_row = fish_by_lower.get(key)
                        if fish_row:
                            item.update(fish_row)
                            item['is_trash'] = 0
                            item['name'] = item.get('fish_name', '')
                except Exception:
                    logger.exception("get_caught_fish: secondary orphan lookup failed")

            for item in results:
                # Only skip price recalculation for genuine trash items (in the trash catalog).
                # Fish with is_trash=1 but no trash_name match were not found in either catalog;
                # they still get a price so they don't show as 0 coins in the shop.
                if item.get('is_trash') and item.get('trash_name') is not None:
                    continue
                item['price'] = self.calculate_fish_price(item, item.get('weight', 0), item.get('length', 0))

            return results

    def get_inventory_summary(self, user_id: int, chat_id: int) -> Dict[str, Any]:
        """Return compact inventory counters for the main inventory menu."""
        summary: Dict[str, Any] = {
            'location_counts': {},
            'regular_count': 0,
            'trash_count': 0,
            'total_treasures': 0,
            'trophy_count': 0,
        }
        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT COALESCE(loc.name, length_loc.name, cf.location) AS resolved_location,
                       COUNT(*) AS fish_count
                FROM caught_fish cf
                LEFT JOIN trash t ON LOWER(TRIM(cf.fish_name)) = LOWER(t.name)
                LEFT JOIN locations loc ON cf.location = loc.name
                LEFT JOIN locations length_loc ON CAST(cf.length AS TEXT) = length_loc.name
                WHERE cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
                  AND t.name IS NULL
                GROUP BY COALESCE(loc.name, length_loc.name, cf.location)
            ''', (user_id, chat_id))
            location_counts: Dict[Any, int] = {}
            for loc, fish_count in cursor.fetchall():
                count = int(fish_count or 0)
                location_counts[loc] = location_counts.get(loc, 0) + count
                summary['regular_count'] += count
            summary['location_counts'] = location_counts

            cursor.execute('''
                SELECT COUNT(*)
                FROM caught_fish cf
                INNER JOIN trash t ON LOWER(TRIM(cf.fish_name)) = LOWER(t.name)
                WHERE cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
            ''', (user_id, chat_id))
            row = cursor.fetchone()
            summary['trash_count'] = int(row[0] or 0) if row else 0

            cursor.execute('''
                SELECT COALESCE(SUM(quantity), 0)
                FROM player_treasures
                WHERE user_id = ? AND quantity > 0
            ''', (user_id,))
            row = cursor.fetchone()
            summary['total_treasures'] = int(row[0] or 0) if row else 0

            cursor.execute('SELECT COUNT(*) FROM player_trophies WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            summary['trophy_count'] = int(row[0] or 0) if row else 0

        return summary

    def calculate_fish_price(self, fish: Dict[str, Any], weight: float, length: float) -> int:
        """Рассчитать цену рыбы: редкость/размер + динамика спроса + дневной рынок."""
        base_price = fish.get('price', 0) or 0
        rarity = fish.get('rarity', 'Обычная')
        fish_name = str(fish.get('fish_name') or fish.get('name') or '').strip()

        # Аномалия: отдельная экономика продажи.
        # Всегда минимум 10 000 + явный бонус за вес.
        if rarity == 'Аномалия':
            safe_weight = max(0.0, float(weight or 0))
            weight_bonus = int(round(safe_weight * 1000))
            base_anomaly_price = 10000 + weight_bonus
            modifiers = self.get_fish_price_modifiers(fish_name)
            return max(1, int(round(base_anomaly_price * float(modifiers.get('total_multiplier') or 1.0))))

        rarity_multipliers = {
            'Обычная': 1.15,
            'Редкая': 1.5,
            'Легендарная': 2.2,
            'Мифическая': 5.0,
        }
        rarity_multiplier = rarity_multipliers.get(rarity, 1.0)

        min_weight = fish.get('min_weight') or 0
        max_weight = fish.get('max_weight') or 0
        min_length = fish.get('min_length') or 0
        max_length = fish.get('max_length') or 0

        def normalize(value: float, minimum: float, maximum: float) -> float:
            if maximum <= minimum:
                return 0.5
            return max(0.0, min(1.0, (value - minimum) / (maximum - minimum)))

        weight_ratio = normalize(weight, min_weight, max_weight)
        length_ratio = normalize(length, min_length, max_length)
        size_ratio = (0.7 * weight_ratio) + (0.3 * length_ratio)
        size_multiplier = 0.7 + (0.8 * size_ratio)

        price = int(round(base_price * rarity_multiplier * size_multiplier))
        modifiers = self.get_fish_price_modifiers(fish_name)
        price = int(round(price * float(modifiers.get('total_multiplier') or 1.0)))
        return max(1, price)

    def get_level_from_xp(self, xp: int) -> int:
        """Получить уровень по суммарному опыту"""
        xp_value = max(0, int(xp or 0))
        level = 0
        for idx in range(1, len(LEVEL_XP_THRESHOLDS)):
            if xp_value >= LEVEL_XP_THRESHOLDS[idx]:
                level = idx
            else:
                break
        return min(level, MAX_LEVEL)

    def get_level_progress(self, xp: int) -> Dict[str, Any]:
        """Получить прогресс уровня по суммарному опыту"""
        xp_value = max(0, int(xp or 0))
        level = self.get_level_from_xp(xp_value)
        if level >= MAX_LEVEL:
            return {
                "level": MAX_LEVEL,
                "xp_total": xp_value,
                "level_start_xp": LEVEL_XP_THRESHOLDS[MAX_LEVEL],
                "next_level_xp": None,
                "xp_into_level": 0,
                "xp_needed": 0,
                "progress": 1.0,
            }

        level_start = LEVEL_XP_THRESHOLDS[level]
        next_level_xp = LEVEL_XP_THRESHOLDS[level + 1]
        xp_into_level = xp_value - level_start
        xp_needed = max(1, next_level_xp - level_start)
        progress = max(0.0, min(1.0, xp_into_level / xp_needed))

        return {
            "level": level,
            "xp_total": xp_value,
            "level_start_xp": level_start,
            "next_level_xp": next_level_xp,
            "xp_into_level": xp_into_level,
            "xp_needed": xp_needed,
            "progress": progress,
        }

    def calculate_item_xp_details(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Рассчитать опыт за предмет с деталями бонуса"""
        if item.get('is_trash') or item.get('rarity') == 'Мусор':
            return {
                'xp_total': 1,
                'xp_base': 1,
                'rarity_bonus': 0,
                'rarity_multiplier': 1.0,
                'weight_multiplier': 1.0,
                'weight_bonus': 0,
            }

        rarity = item.get('rarity', 'Обычная')
        base_xp = BASE_XP_BY_RARITY.get(rarity, BASE_XP_BY_RARITY['Обычная'])
        rarity_multiplier = RARITY_XP_MULTIPLIERS.get(rarity, 1.0)

        weight = float(item.get('weight') or 0)
        min_weight = float(item.get('min_weight') or 0)
        max_weight = float(item.get('max_weight') or 0)

        weight_multiplier = 1.0
        if max_weight > min_weight and weight > 0:
            ratio = (weight - min_weight) / (max_weight - min_weight)
            ratio = max(0.0, min(1.0, ratio))
            weight_multiplier = 1.0 + (0.6 * ratio)

        xp_before_weight = base_xp * rarity_multiplier
        xp_rarity = int(round(xp_before_weight))
        xp_total = int(round(xp_before_weight * weight_multiplier))
        xp_base = int(round(base_xp))
        rarity_bonus = max(0, xp_rarity - xp_base)
        weight_bonus = max(0, xp_total - xp_rarity)

        return {
            'xp_total': max(1, xp_total),
            'xp_base': max(1, xp_base),
            'rarity_bonus': rarity_bonus,
            'rarity_multiplier': rarity_multiplier,
            'weight_multiplier': weight_multiplier,
            'weight_bonus': weight_bonus,
        }

    def calculate_item_xp(self, item: Dict[str, Any]) -> int:
        """Рассчитать опыт за предмет (рыба или мусор)"""
        return self.calculate_item_xp_details(item)['xp_total']

    def calculate_weights(self, fish_list: List[Dict[str, Any]]) -> List[float]:
        """Вычислить веса для взвешенного случайного выбора рыб.

        Простая функция: базовые веса по редкости + небольшой вклад от среднего веса рыбы.
        """
        rarity_base = {
            'Обычная': 60.0,
            'Редкая': 30.0,
            'Легендарная': 3.0,
            'Мифическая': 0.05,
            'Мусор': 5.0,
        }
        weights: List[float] = []
        for fish in fish_list:
            rarity = fish.get('rarity') or 'Обычная'
            w = float(rarity_base.get(rarity, 20.0))
            try:
                min_w = float(fish.get('min_weight') or 0)
                max_w = float(fish.get('max_weight') or 0)
                if max_w > 0 and max_w >= min_w:
                    avg = (min_w + max_w) / 2.0
                    # add a small contribution from average weight
                    w += (avg * 1.0)
            except Exception:
                pass
            weights.append(max(1.0, w))
        return weights

    def add_player_xp(self, user_id: int, chat_id: int, xp_amount: int) -> Dict[str, Any]:
        """Добавить опыт игроку и обновить уровень"""
        xp_delta = int(xp_amount or 0)
        with self._connect() as conn:
            cursor = conn.cursor()
            # Use the same player-row selection logic as `update_player`:
            # prefer a global profile row (chat_id IS NULL or <1) when chat-aware schema is used.
            cursor.execute('PRAGMA table_info(players)')
            cols = [c[1] for c in cursor.fetchall()]
            if 'chat_id' in cols:
                cursor.execute('SELECT COALESCE(xp, 0), COALESCE(level, 0) FROM players WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) LIMIT 1', (user_id,))
                row = cursor.fetchone()
                if not row:
                    cursor.execute('SELECT COALESCE(xp, 0), COALESCE(level, 0) FROM players WHERE user_id = ? AND chat_id = ? LIMIT 1', (user_id, chat_id))
                    row = cursor.fetchone()
                current_xp = row[0] if row else 0
                current_level = row[1] if row else 0
                new_xp = max(0, current_xp + xp_delta)
                new_level = self.get_level_from_xp(new_xp)
                # update global row if exists, else update per-chat row
                cursor.execute('UPDATE players SET xp = ?, level = ? WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)', (new_xp, new_level, user_id))
                if cursor.rowcount == 0:
                    cursor.execute('UPDATE players SET xp = ?, level = ? WHERE user_id = ? AND chat_id = ?', (new_xp, new_level, user_id, chat_id))
            else:
                cursor.execute('SELECT COALESCE(xp, 0), COALESCE(level, 0) FROM players WHERE user_id = ? ORDER BY created_at DESC LIMIT 1', (user_id,))
                row = cursor.fetchone()
                current_xp = row[0] if row else 0
                current_level = row[1] if row else 0
                new_xp = max(0, current_xp + xp_delta)
                new_level = self.get_level_from_xp(new_xp)
                cursor.execute('UPDATE players SET xp = ?, level = ? WHERE user_id = ?', (new_xp, new_level, user_id))
            conn.commit()

        progress = self.get_level_progress(new_xp)
        progress['leveled_up'] = new_level > (current_level or 0)
        return progress
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить таблицу лидеров (по умолчанию - глобально за все время)"""
        return self.get_leaderboard_period(limit=limit)

    def record_ticket_award(
        self,
        user_id: int,
        username: str,
        amount: int,
        source_type: str,
        source_ref: Optional[str] = None,
        jackpot_amount: int = 0,
    ) -> Dict[str, Any]:
        """Записать выдачу билетов и создать отдельную запись на каждый билет."""
        delta = int(amount or 0)
        if delta <= 0:
            return {
                'award_id': None,
                'ticket_codes': [],
                'tickets_total': self.get_user_tickets(user_id),
            }

        safe_username = str(username or 'Неизвестно').strip() or 'Неизвестно'
        safe_source_type = str(source_type or 'unknown').strip() or 'unknown'
        safe_source_ref = str(source_ref or '').strip() or None
        safe_jackpot_amount = int(jackpot_amount or 0)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO ticket_awards (user_id, username, source_type, source_ref, amount, jackpot_amount)
                VALUES (?, ?, ?, ?, ?, ?)
                RETURNING id
                ''',
                (int(user_id), safe_username, safe_source_type, safe_source_ref, delta, safe_jackpot_amount),
            )
            award_row = cursor.fetchone()
            award_id = int(award_row[0]) if award_row else None

            ticket_codes: List[str] = []
            if award_id:
                for ticket_index in range(1, delta + 1):
                    ticket_code = f"b{award_id}-{ticket_index}"
                    cursor.execute(
                        '''
                        INSERT INTO ticket_items (ticket_code, award_id, user_id, username, source_type, source_ref)
                        VALUES (?, ?, ?, ?, ?, ?)
                        ''',
                        (ticket_code, award_id, int(user_id), safe_username, safe_source_type, safe_source_ref),
                    )
                    ticket_codes.append(ticket_code)

            cursor.execute("PRAGMA table_info(players)")
            columns = [col[1] for col in cursor.fetchall()]
            uses_chat = 'chat_id' in columns

            if uses_chat:
                cursor.execute(
                    'UPDATE players SET tickets = COALESCE(tickets, 0) + ? WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1)',
                    (delta, user_id),
                )
                if cursor.rowcount == 0:
                    cursor.execute(
                        'UPDATE players SET tickets = COALESCE(tickets, 0) + ? WHERE user_id = ?',
                        (delta, user_id),
                    )
            else:
                cursor.execute(
                    'UPDATE players SET tickets = COALESCE(tickets, 0) + ? WHERE user_id = ?',
                    (delta, user_id),
                )
            conn.commit()

        return {
            'award_id': award_id,
            'ticket_codes': ticket_codes,
            'tickets_total': self.get_user_tickets(user_id),
        }

    def add_tickets(
        self,
        user_id: int,
        amount: int,
        username: Optional[str] = None,
        source_type: str = 'unknown',
        source_ref: Optional[str] = None,
        jackpot_amount: int = 0,
    ) -> int:
        """Начислить билеты пользователю и вернуть новый баланс билетов."""
        resolved_username = str(username or '').strip()
        if not resolved_username:
            try:
                player = self.get_player(user_id, -1)
            except Exception:
                player = None
            resolved_username = str((player or {}).get('username') or 'Неизвестно').strip() or 'Неизвестно'

        result = self.record_ticket_award(
            user_id=user_id,
            username=resolved_username,
            amount=amount,
            source_type=source_type,
            source_ref=source_ref,
            jackpot_amount=jackpot_amount,
        )
        return int(result.get('tickets_total') or 0)

    def get_user_tickets(self, user_id: int) -> int:
        """Текущее количество билетов пользователя (глобально по user_id)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM ticket_items WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            if row is not None:
                return int(row[0] or 0)
            cursor.execute(
                'SELECT COALESCE(MAX(tickets), 0) FROM players WHERE user_id = ?',
                (user_id,),
            )
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0

    def get_tickets_leaderboard(self, limit: int = 3) -> List[Dict[str, Any]]:
        """Топ пользователей по билетам (глобально)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    user_id,
                    COALESCE(MAX(username), 'Неизвестно') AS username,
                    COUNT(*) AS tickets
                FROM ticket_items
                GROUP BY user_id
                ORDER BY tickets DESC, user_id ASC
                LIMIT ?
                ''',
                (limit,),
            )
            rows = cursor.fetchall()
            return [
                {
                    'user_id': int(row[0]),
                    'username': row[1],
                    'tickets': int(row[2] or 0),
                }
                for row in rows
            ]

    def get_user_tickets_rank(self, user_id: int) -> Dict[str, int]:
        """Вернуть место пользователя в глобальном рейтинге билетов и его билеты."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT user_id, COUNT(*) AS tickets
                FROM ticket_items
                GROUP BY user_id
                ORDER BY tickets DESC, user_id ASC
                '''
            )
            rows = cursor.fetchall()

        rank = 0
        tickets = 0
        total_users = len(rows)
        for idx, row in enumerate(rows, start=1):
            row_user_id = int(row[0])
            row_tickets = int(row[1] or 0)
            if row_user_id == int(user_id):
                rank = idx
                tickets = row_tickets
                break

        if rank == 0:
            tickets = self.get_user_tickets(user_id)
            rank = total_users + 1 if total_users > 0 else 1

        return {
            'rank': rank,
            'tickets': tickets,
            'total_users': total_users,
        }

    def get_random_ticket(self) -> Optional[Dict[str, Any]]:
        """Получить случайный билет из общего пула."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT ticket_code, award_id, user_id, username, source_type, source_ref, created_at
                FROM ticket_items
                ORDER BY RANDOM()
                LIMIT 1
                '''
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))

    def get_random_tickets_in_period(
        self,
        start_at: datetime,
        end_at: datetime,
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """Получить случайные билеты из диапазона дат."""
        safe_limit = max(1, int(limit or 1))
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT ticket_code, award_id, user_id, username, source_type, source_ref, created_at
                FROM ticket_items
                WHERE created_at >= ? AND created_at <= ?
                ORDER BY RANDOM()
                LIMIT ?
                ''',
                (
                    start_at.strftime('%Y-%m-%d %H:%M:%S'),
                    end_at.strftime('%Y-%m-%d %H:%M:%S'),
                    safe_limit,
                ),
            )
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description] if cursor.description else []
            return [dict(zip(columns, row)) for row in rows]

    def get_ticket_counts_for_users_in_period(
        self,
        user_ids: List[int],
        start_at: datetime,
        end_at: datetime,
    ) -> Dict[int, int]:
        """Получить число билетов каждого пользователя в указанном диапазоне дат."""
        if not user_ids:
            return {}

        with self._connect() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(user_ids))
            cursor.execute(
                f'''
                SELECT user_id, COUNT(*) AS tickets
                FROM ticket_items
                WHERE created_at >= ? AND created_at <= ? AND user_id IN ({placeholders})
                GROUP BY user_id
                ''',
                [
                    start_at.strftime('%Y-%m-%d %H:%M:%S'),
                    end_at.strftime('%Y-%m-%d %H:%M:%S'),
                    *[int(user_id) for user_id in user_ids],
                ],
            )
            rows = cursor.fetchall()

        result: Dict[int, int] = {}
        for row in rows or []:
            try:
                result[int(row[0])] = int(row[1] or 0)
            except Exception:
                continue
        return result

    def get_chat_leaderboard_period(self, chat_id: int, limit: int = 10, since: Optional[datetime] = None, until: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """Получить топ по общему весу улова в конкретном чате за период.
        Логика идентична get_leaderboard_period (sold=0, JOIN fish),
        но с обязательным фильтром cf.chat_id = chat_id.
        """
        with self._connect() as conn:
            cursor = conn.cursor()

            where_clauses: List[str] = ['cf.chat_id = %s', 'cf.sold = 0']
            params: List = [chat_id]

            if since is not None:
                where_clauses.append('cf.caught_at >= %s')
                params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
            if until is not None:
                where_clauses.append('cf.caught_at <= %s')
                params.append(until.strftime('%Y-%m-%d %H:%M:%S'))

            where_sql = 'WHERE ' + ' AND '.join(where_clauses)

            query = f'''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') as username,
                    cf.user_id,
                    COUNT(cf.id) as total_fish,
                    COALESCE(SUM(cf.weight), 0) as total_weight
                FROM caught_fish cf
                JOIN fish f ON TRIM(cf.fish_name) = f.name
                LEFT JOIN players p ON p.user_id = cf.user_id
                {where_sql}
                GROUP BY cf.user_id
                ORDER BY total_weight DESC, total_fish DESC
                LIMIT %s
            '''

            params.append(limit)
            logger.info(
                'get_chat_leaderboard_period QUERY: chat_id=%s since=%s until=%s limit=%s',
                chat_id, since, until, limit
            )
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                logger.info(
                    'get_chat_leaderboard_period RESULT: %d rows for chat_id=%s',
                    len(rows), chat_id
                )
                for row in rows:
                    logger.info(
                        '  row: username=%s user_id=%s total_fish=%s total_weight=%s',
                        row[0], row[1], row[2], row[3]
                    )
                return [
                    {
                        'username': row[0],
                        'user_id': row[1],
                        'total_fish': row[2],
                        'total_weight': row[3],
                    }
                    for row in rows
                ]
            except Exception:
                logger.exception('get_chat_leaderboard_period failed')
                return []

    def get_users_weight_leaderboard(
        self,
        user_ids: List[int],
        since: Optional[datetime] = None,
        until: Optional[datetime] = None,
    ) -> List[Dict[str, Any]]:
        """Топ по общему весу непроданной рыбы для заданного списка user_id за период."""
        if not user_ids:
            return []
        with self._connect() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['%s'] * len(user_ids))
            where_clauses = [f'cf.user_id IN ({placeholders})', 'cf.sold = 0']
            params: List = list(user_ids)
            if since is not None:
                where_clauses.append('cf.caught_at >= %s')
                params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
            if until is not None:
                where_clauses.append('cf.caught_at <= %s')
                params.append(until.strftime('%Y-%m-%d %H:%M:%S'))
            where_sql = 'WHERE ' + ' AND '.join(where_clauses)
            query = f'''
                SELECT
                    cf.user_id,
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    COUNT(cf.id) AS total_fish,
                    COALESCE(SUM(cf.weight), 0) AS total_weight
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                {where_sql}
                GROUP BY cf.user_id
                ORDER BY total_weight DESC, total_fish DESC
            '''
            try:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return [
                    {
                        'user_id': row[0],
                        'username': row[1],
                        'total_fish': row[2],
                        'total_weight': float(row[3]),
                    }
                    for row in rows
                ]
            except Exception:
                logger.exception('get_users_weight_leaderboard failed')
                return []

    def get_level_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Получить топ по уровню (глобально)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(username), 'Неизвестно') as username,
                    user_id,
                    MAX(COALESCE(level, 0)) as level,
                    MAX(COALESCE(xp, 0)) as xp
                FROM players
                GROUP BY user_id
                ORDER BY level DESC, xp DESC
                LIMIT ?
                ''',
                (limit,)
            )
            rows = cursor.fetchall()
            return [
                {
                    'username': row[0],
                    'user_id': row[1],
                    'level': row[2],
                    'xp': row[3],
                }
                for row in rows
            ]

    def create_tournament(
        self,
        chat_id: int,
        created_by: int,
        title: str,
        tournament_type: str,
        starts_at: datetime,
        ends_at: datetime,
        target_fish: Optional[str] = None,
        target_location: Optional[str] = None,
        prize_pool: int = 50,
        prize_places: int = 10,
    ) -> Optional[int]:
        """Создать турнир и вернуть его ID."""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                safe_places = max(1, min(int(prize_places or 10), 100))

                # Normalize datetime parameters to strings for cross-DB compatibility
                if isinstance(starts_at, datetime):
                    starts_val = starts_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    starts_val = starts_at
                if isinstance(ends_at, datetime):
                    ends_val = ends_at.strftime("%Y-%m-%d %H:%M:%S")
                else:
                    ends_val = ends_at

                cursor.execute(
                    '''
                    INSERT INTO tournaments (
                        chat_id, created_by, title, tournament_type,
                        starts_at, ends_at, target_fish, prize_pool,
                        target_location, prize_places
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    RETURNING id
                    ''',
                    (
                        chat_id,
                        created_by,
                        title,
                        tournament_type,
                        starts_val,
                        ends_val,
                        target_fish,
                        int(prize_pool or 50),
                        target_location,
                        safe_places,
                    ),
                )
                row = None
                try:
                    row = cursor.fetchone()
                except Exception:
                    # Some DB drivers may not return from RETURNING with this wrapper
                    row = None

                # Commit regardless; if RETURNING didn't work, try to find the inserted row
                conn.commit()

                if row and row[0] is not None:
                    return int(row[0])

                # Fallback: query for the inserted tournament by unique-ish fields
                try:
                    cursor.execute(
                        'SELECT id FROM tournaments WHERE chat_id = ? AND created_by = ? AND title = ? AND starts_at = ? ORDER BY id DESC LIMIT 1',
                        (chat_id, created_by, title, starts_val),
                    )
                    found = cursor.fetchone()
                    if found:
                        return int(found[0])
                except Exception:
                    # ignore and fall through
                    pass

                return None
            except Exception:
                logger.exception("create_tournament failed")
                try:
                    conn.rollback()
                except Exception:
                    pass
                return None

    def get_tournament(self, tournament_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM tournaments WHERE id = ? LIMIT 1', (tournament_id,))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def get_active_tournament(self) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM tournaments
                WHERE starts_at <= CURRENT_TIMESTAMP
                  AND ends_at >= CURRENT_TIMESTAMP
                ORDER BY starts_at DESC
                LIMIT 1
                '''
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def get_active_tournament_for_location(self, location_name: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            # Make location check case-insensitive and trim spaces
            cursor.execute(
                '''
                    SELECT *
                    FROM tournaments
                    WHERE (LOWER(TRIM(target_location)) = LOWER(TRIM(?)) OR target_location IS NULL)
                        AND starts_at <= CURRENT_TIMESTAMP
                        AND ends_at >= CURRENT_TIMESTAMP
                    ORDER BY starts_at DESC
                    LIMIT 1
                ''',
                (location_name,),
            )
            row = cursor.fetchone()
            if not row:
                # Log for debugging if no tournament is found
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"No active tournament for location: '{location_name}' (case-insensitive match)")
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def create_raf_event_draft(
        self,
        creator_user_id: int,
        creator_username: Optional[str],
        title: str,
        target_chat_id: int,
        source_message_link: Optional[str],
        duration_hours: Optional[int],
        prizes: List[Dict[str, Any]],
    ) -> Optional[int]:
        """Создать RAF-ивент в статусе draft и связанные призы."""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                safe_duration = int(duration_hours) if duration_hours is not None else None
                safe_title = (title or "RAF Event").strip()[:200]
                safe_link = (source_message_link or "").strip()[:1000] or None
                safe_creator_username = (creator_username or "").strip()[:128] or None

                cursor.execute(
                    '''
                    INSERT INTO raf_events (
                        creator_user_id, creator_username, title, target_chat_id,
                        source_message_link, duration_hours, status
                    )
                    VALUES (?, ?, ?, ?, ?, ?, 'draft')
                    RETURNING id
                    ''',
                    (
                        int(creator_user_id),
                        safe_creator_username,
                        safe_title,
                        int(target_chat_id),
                        safe_link,
                        safe_duration,
                    ),
                )
                row = cursor.fetchone()
                event_id = int(row[0]) if row and row[0] is not None else None

                if not event_id:
                    conn.rollback()
                    return None

                for idx, prize in enumerate(prizes or [], start=1):
                    cursor.execute(
                        '''
                        INSERT INTO raf_event_prizes (
                            event_id, prize_order, prize_text, rarity_key, chance_percent
                        )
                        VALUES (?, ?, ?, ?, ?)
                        ''',
                        (
                            event_id,
                            idx,
                            str(prize.get('prize_text') or '').strip()[:1000],
                            str(prize.get('rarity_key') or '').strip().lower(),
                            float(prize.get('chance_percent') or 0),
                        ),
                    )

                conn.commit()
                return event_id
            except Exception:
                logger.exception("create_raf_event_draft failed")
                try:
                    conn.rollback()
                except Exception:
                    pass
                return None

    def get_raf_event(self, event_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM raf_events WHERE id = ? LIMIT 1', (int(event_id),))
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def get_raf_event_prizes(self, event_id: int) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM raf_event_prizes
                WHERE event_id = ?
                ORDER BY prize_order ASC, id ASC
                ''',
                (int(event_id),),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, row)) for row in rows]

    def get_latest_raf_pending_event(self, creator_user_id: int) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT *
                FROM raf_events
                WHERE creator_user_id = ?
                  AND status IN ('draft', 'paid')
                ORDER BY id DESC
                LIMIT 1
                ''',
                (int(creator_user_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def cancel_raf_event_creation(self, event_id: int, creator_user_id: int) -> bool:
        """Отменить создание RAF-ивента в статусах draft/paid."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT status FROM raf_events WHERE id = ? AND creator_user_id = ? LIMIT 1',
                (int(event_id), int(creator_user_id)),
            )
            row = cursor.fetchone()
            if not row:
                return False
            status = str(row[0] or '')
            if status not in ('draft', 'paid'):
                return False

            cursor.execute(
                "UPDATE raf_events SET status = 'cancelled' WHERE id = ? AND creator_user_id = ?",
                (int(event_id), int(creator_user_id)),
            )
            conn.commit()

    def get_boat_members_count(self, boat_id: int) -> int:
        """Количество участников лодки."""
        self._ensure_boat_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM boat_members WHERE boat_id = ?', (int(boat_id),))
            row = cursor.fetchone()
            return int(row[0] or 0) if row else 0

    def get_user_boat(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить лодку пользователя, если она есть."""
        self._ensure_boat_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT b.*
                FROM boats b
                JOIN boat_members bm ON bm.boat_id = b.id
                WHERE bm.user_id = ?
                ORDER BY b.is_active DESC, b.id DESC
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            boat = dict(zip(columns, row))
            boat['members_count'] = self.get_boat_members_count(int(boat.get('id') or 0))
            return boat

    def get_active_boat_by_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получить активную лодку пользователя, если он сейчас в плавании."""
        self._ensure_boat_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT b.*
                FROM boats b
                JOIN boat_members bm ON bm.boat_id = b.id
                WHERE bm.user_id = ?
                  AND b.is_active = 1
                ORDER BY b.id DESC
                LIMIT 1
                ''',
                (int(user_id),),
            )
            row = cursor.fetchone()
            if not row:
                return None
            columns = [description[0] for description in cursor.description]
            boat = dict(zip(columns, row))
            boat['members_count'] = self.get_boat_members_count(int(boat.get('id') or 0))
            return boat

    def is_user_on_boat_trip(self, user_id: int) -> bool:
        """Проверить, находится ли пользователь в активном плавании."""
        return self.get_active_boat_by_user(user_id) is not None

    def mark_raf_event_paid(self, event_id: int, creator_user_id: int, payment_charge_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE raf_events
                SET status = 'paid', payment_charge_id = ?
                WHERE id = ?
                  AND creator_user_id = ?
                  AND status = 'draft'
                ''',
                (str(payment_charge_id or ''), int(event_id), int(creator_user_id)),
            )
            conn.commit()
            return bool(getattr(cursor, 'rowcount', 0))

    def activate_raf_event(self, event_id: int, creator_user_id: int) -> Optional[Dict[str, Any]]:
        """Запустить RAF-ивент. Вернет событие после успешного запуска."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT duration_hours
                FROM raf_events
                WHERE id = ?
                  AND creator_user_id = ?
                  AND status = 'paid'
                LIMIT 1
                ''',
                (int(event_id), int(creator_user_id)),
            )
            row = cursor.fetchone()
            if not row:
                return None

            duration_hours = row[0]
            now_dt = datetime.utcnow()
            ends_at = None
            if duration_hours is not None:
                try:
                    ends_at = now_dt + timedelta(hours=int(duration_hours))
                except Exception:
                    ends_at = None

            cursor.execute(
                '''
                UPDATE raf_events
                SET status = 'active', starts_at = ?, activated_at = ?, ends_at = ?
                WHERE id = ?
                  AND creator_user_id = ?
                  AND status = 'paid'
                ''',
                (now_dt, now_dt, ends_at, int(event_id), int(creator_user_id)),
            )
            if not bool(getattr(cursor, 'rowcount', 0)):
                conn.rollback()
                return None

            conn.commit()
            return self.get_raf_event(int(event_id))

    def _close_expired_raf_events(self, chat_id: int):
        """Служебно: закрыть истекшие RAF-ивенты в чате."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                UPDATE raf_events
                SET status = 'finished'
                WHERE target_chat_id = ?
                  AND status = 'active'
                  AND ends_at IS NOT NULL
                  AND ends_at < CURRENT_TIMESTAMP
                ''',
                (int(chat_id),),
            )
            conn.commit()

    def try_roll_raf_prize(
        self,
        chat_id: int,
        rarity_key: str,
        winner_user_id: int,
        winner_username: str,
        won_location: Optional[str] = None,
        trigger_source: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Проверить активные RAF-ивенты и попытаться выдать приз под конкретную редкость."""
        self._close_expired_raf_events(chat_id)
        normalized_rarity = str(rarity_key or '').strip().lower()
        if not normalized_rarity:
            return None

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    p.id,
                    p.event_id,
                    p.prize_text,
                    p.rarity_key,
                    p.chance_percent,
                    e.title,
                    e.creator_user_id,
                    e.target_chat_id
                FROM raf_event_prizes p
                JOIN raf_events e ON e.id = p.event_id
                WHERE e.target_chat_id = ?
                  AND e.status = 'active'
                  AND (e.starts_at IS NULL OR e.starts_at <= CURRENT_TIMESTAMP)
                  AND (e.ends_at IS NULL OR e.ends_at >= CURRENT_TIMESTAMP)
                  AND p.is_claimed = 0
                  AND LOWER(TRIM(p.rarity_key)) = LOWER(TRIM(?))
                ORDER BY e.activated_at ASC, p.prize_order ASC, p.id ASC
                ''',
                (int(chat_id), normalized_rarity),
            )
            rows = cursor.fetchall()
            if not rows:
                return None

            cols = [d[0] for d in cursor.description]
            candidates = [dict(zip(cols, row)) for row in rows]

            for cand in candidates:
                chance = float(cand.get('chance_percent') or 0)
                if chance <= 0:
                    continue
                roll = random.uniform(0, 100)
                is_winner = roll <= chance
                logger.info(
                    "[RAF_LOG] Prize attempt: chat_id=%s user_id=%s username=%s event_id=%s prize_id=%s prize=%s rarity=%s roll=%.4f chance=%.2f winner=%s",
                    chat_id,
                    winner_user_id,
                    winner_username,
                    cand.get('event_id'),
                    cand.get('id'),
                    cand.get('prize_text'),
                    normalized_rarity,
                    roll,
                    chance,
                    is_winner,
                )
                if roll > chance:
                    continue

                won_at = datetime.utcnow().isoformat()
                cursor.execute(
                    '''
                    UPDATE raf_event_prizes
                    SET is_claimed = 1,
                        winner_user_id = ?,
                        winner_username = ?,
                        won_at = ?,
                        won_location = ?,
                        trigger_source = ?
                    WHERE id = ?
                      AND is_claimed = 0
                    RETURNING id
                    ''',
                    (
                        int(winner_user_id),
                        str(winner_username or ''),
                        won_at,
                        won_location,
                        trigger_source,
                        int(cand['id']),
                    ),
                )
                claimed_row = cursor.fetchone()
                if not claimed_row:
                    logger.info(
                        "[RAF_LOG] Prize %s already claimed concurrently. Skip.",
                        cand.get('id'),
                    )
                    continue

                event_id = int(cand['event_id'])
                cursor.execute(
                    'SELECT COUNT(*) FROM raf_event_prizes WHERE event_id = ? AND is_claimed = 0',
                    (event_id,),
                )
                remain_row = cursor.fetchone()
                remaining = int(remain_row[0] or 0) if remain_row else 0
                if remaining <= 0:
                    cursor.execute(
                        "UPDATE raf_events SET status = 'finished' WHERE id = ? AND status = 'active'",
                        (event_id,),
                    )

                logger.info(
                    "[RAF_LOG] Prize WIN: event_id=%s prize_id=%s prize=%s winner_user_id=%s winner_username=%s chance=%.2f roll=%.4f remaining_prizes=%s",
                    event_id,
                    cand.get('id'),
                    cand.get('prize_text'),
                    winner_user_id,
                    winner_username,
                    chance,
                    roll,
                    remaining,
                )
                if remaining <= 0:
                    logger.info(
                        "[RAF_LOG] Event finished: event_id=%s all prizes claimed.",
                        event_id,
                    )

                conn.commit()

                return {
                    'event_id': event_id,
                    'prize_id': int(cand['id']),
                    'event_title': cand.get('title'),
                    'prize_text': cand.get('prize_text'),
                    'rarity_key': normalized_rarity,
                    'chance_percent': chance,
                    'roll_value': roll,
                    'creator_user_id': cand.get('creator_user_id'),
                    'target_chat_id': cand.get('target_chat_id'),
                    'remaining_prizes': remaining,
                }

            return None

    def get_tour_leaderboard_weight(self, starts_at: datetime, ends_at: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    cf.user_id,
                    COUNT(cf.id) AS total_fish,
                    COALESCE(SUM(cf.weight), 0) AS total_weight
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
                GROUP BY cf.user_id
                ORDER BY total_weight DESC, total_fish DESC
                LIMIT ?
                ''',
                (starts_at, ends_at, max(1, int(limit or 10))),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_tour_leaderboard_length(self, starts_at: datetime, ends_at: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    cf.user_id,
                    COUNT(cf.id) AS total_fish,
                    COALESCE(SUM(cf.length), 0) AS total_length
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
                GROUP BY cf.user_id
                ORDER BY total_length DESC, total_fish DESC
                LIMIT ?
                ''',
                (starts_at, ends_at, max(1, int(limit or 10))),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_location_leaderboard_length(self, location_name: str, starts_at: datetime, ends_at: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    cf.user_id,
                    COALESCE(MAX(cf.fish_name), 'Неизвестно') AS fish_name,
                    COALESCE(MAX(cf.length), 0) AS best_length
                FROM caught_fish cf
                LEFT JOIN players p ON p.user_id = cf.user_id
                WHERE cf.location = ?
                  AND cf.caught_at >= ?
                  AND cf.caught_at <= ?
                  AND COALESCE(cf.sold, 0) = 0
                GROUP BY cf.user_id
                ORDER BY best_length DESC
                LIMIT ?
                ''',
                (location_name, starts_at, ends_at, max(1, int(limit or 10))),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_location_leaderboard_weight(self, location_name: str, starts_at: datetime, ends_at: datetime, limit: int = 10) -> List[Dict[str, Any]]:
        """Leaderboard of single best (max) fish weight per user for a location."""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Use a CTE to find max weight per user, then join back to caught_fish
            # to get the fish name corresponding to that max weight. This avoids
            # taking an arbitrary MAX(fish_name) unrelated to the weight.
            cursor.execute(
                '''
                WITH best AS (
                    SELECT user_id, MAX(weight) AS best_weight
                    FROM caught_fish
                    WHERE location = ?
                      AND caught_at >= ?
                      AND caught_at <= ?
                      AND COALESCE(sold, 0) = 0
                    GROUP BY user_id
                )
                SELECT
                    COALESCE(MAX(p.username), 'Неизвестно') AS username,
                    b.user_id,
                    COALESCE(MAX(cf.fish_name), 'Неизвестно') AS fish_name,
                    b.best_weight
                FROM best b
                LEFT JOIN caught_fish cf ON cf.user_id = b.user_id AND cf.weight = b.best_weight
                LEFT JOIN players p ON p.user_id = b.user_id
                GROUP BY b.user_id, b.best_weight
                ORDER BY b.best_weight DESC
                LIMIT ?
                ''',
                (location_name, starts_at, ends_at, max(1, int(limit or 10))),
            )
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_leaderboard_period(self, limit: int = 10, since: Optional[datetime] = None, until: Optional[datetime] = None, chat_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Получить таблицу лидеров за период (с фильтром по началу и концу) и/или по чату"""
        with self._connect() as conn:
            cursor = conn.cursor()

            where_clauses: List[str] = []
            params: List = []

            # Always join players to get username
            join_clause = "LEFT JOIN players p ON p.user_id = cf.user_id"

            # NOTE: Per configuration, leaderboard no longer supports filtering by chat_id.
            # The `chat_id` parameter is accepted for compatibility but ignored.

            if since is not None:
                where_clauses.append("datetime(cf.caught_at) >= datetime(?)")
                params.append(since.strftime("%Y-%m-%d %H:%M:%S"))
            if until is not None:
                where_clauses.append("datetime(cf.caught_at) <= datetime(?)")
                params.append(until.strftime("%Y-%m-%d %H:%M:%S"))

            where_clauses.append("cf.sold = 0")

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            query = f'''
                SELECT 
                    COALESCE(MAX(p.username), 'Неизвестно') as username,
                    cf.user_id as user_id,
                    COUNT(cf.id) as total_fish,
                    COALESCE(SUM(cf.weight), 0) as total_weight
                FROM caught_fish cf
                JOIN fish f ON TRIM(cf.fish_name) = f.name
                {join_clause}
                {where_sql}
                GROUP BY cf.user_id
                ORDER BY total_weight DESC, total_fish DESC
                LIMIT ?
            '''

            params.append(limit)
            cursor.execute(query, params)

            rows = cursor.fetchall()
            return [
                {
                    'username': row[0],
                    'user_id': row[1],
                    'total_fish': row[2],
                    'total_weight': row[3]
                }
                for row in rows
            ]
    
    def get_rods(self) -> List[Dict[str, Any]]:
        """Получить список всех удочек"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM rods ORDER BY price')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def ensure_rod_catalog(self):
        """Гарантировать наличие базового каталога удочек и корректного max_weight."""
        rods_data = [
            ("Бамбуковая удочка", 0, 100, 100, 0, 30),
            ("Углепластиковая удочка", 1500, 150, 150, 5, 60),
            ("Карбоновая удочка", 4500, 200, 200, 10, 120),
            ("Золотая удочка", 15000, 300, 300, 20, 350),
            ("Удачливая удочка", 25000, 150, 150, 15, 650),
        ]
        rods_weight_updates = [
            (30, "Бамбуковая удочка"),
            (60, "Углепластиковая удочка"),
            (120, "Карбоновая удочка"),
            (350, "Золотая удочка"),
            (650, "Удачливая удочка"),
        ]

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.executemany(
                '''
                INSERT OR IGNORE INTO rods (name, price, durability, max_durability, fish_bonus, max_weight)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                rods_data,
            )

            for max_w, rod_name in rods_weight_updates:
                cursor.execute('UPDATE rods SET max_weight = ? WHERE name = ?', (max_w, rod_name))

            conn.commit()
    
    def get_locations(self) -> List[Dict[str, Any]]:
        """Получить список всех локаций"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM locations ORDER BY id')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_location_players_count(self, location_name: str, chat_id: int) -> int:
        """Получить количество игроков на локации в конкретном чате"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*)
                FROM players
                WHERE current_location = ?
            ''', (location_name,))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_baits(self) -> List[Dict[str, Any]]:
        """Получить список всех наживок"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM baits ORDER BY name')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_bait_by_id(self, bait_id: int) -> Optional[Dict[str, Any]]:
        """Получить наживку по ID"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM baits WHERE id = ?', (bait_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_player_baits(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить наживки игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, COALESCE(pb.quantity, 0) as player_quantity 
                FROM baits b 
                LEFT JOIN player_baits pb ON b.name = pb.bait_name AND pb.user_id = ?
                ORDER BY b.fish_bonus DESC
            ''', (user_id,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_active_feeder_bonus(self, user_id: int, chat_id: int) -> int:
        """Получить активный бонус кормушки для игрока.

        Возвращает процентный бонус (целое число). Если таблиц/колонок кормушек
        в текущей схеме нет, возвращает 0.
        """
        candidate_tables = [
            'player_feeders',
            'active_feeders',
            'player_feeder_effects',
            'feeders_active',
        ]
        bonus_columns_priority = ['bonus_percent', 'fish_bonus', 'bonus', 'effect_bonus']
        time_columns_priority = ['expires_at', 'active_until', 'ends_at', 'end_at']
        active_columns_priority = ['is_active', 'active', 'enabled']

        with self._connect() as conn:
            cursor = conn.cursor()

            for table in candidate_tables:
                try:
                    cursor.execute(
                        "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
                        (table,)
                    )
                    columns = {row[0] for row in cursor.fetchall()}
                    if not columns or 'user_id' not in columns:
                        continue

                    bonus_col = next((col for col in bonus_columns_priority if col in columns), None)
                    if not bonus_col:
                        continue

                    time_col = next((col for col in time_columns_priority if col in columns), None)
                    active_col = next((col for col in active_columns_priority if col in columns), None)

                    where_parts = ["user_id = ?"]
                    params: List[Union[int, str]] = [user_id]

                    if 'chat_id' in columns:
                        where_parts.append("(chat_id = ? OR chat_id IS NULL OR chat_id < 1)")
                        params.append(chat_id)

                    if active_col:
                        where_parts.append(f"({active_col} = 1 OR {active_col} IS NULL)")

                    if time_col:
                        where_parts.append(f"({time_col} IS NULL OR {time_col} > CURRENT_TIMESTAMP)")

                    query = f"SELECT COALESCE(MAX({bonus_col}), 0) FROM {table} WHERE " + " AND ".join(where_parts)
                    cursor.execute(query, params)
                    row = cursor.fetchone()
                    value = int((row[0] if row else 0) or 0)
                    return max(0, value)
                except Exception:
                    # Пробуем следующую таблицу/схему без падения игрового цикла.
                    continue

        return 0

    def _ensure_booster_tables(self):
        """Создать таблицы бустеров (кормушки/эхолот), если их еще нет."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_feeders (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT DEFAULT 0,
                    feeder_type TEXT NOT NULL,
                    bonus_percent INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id, feeder_type)
                )
            ''')
            # Ensure unique index for ON CONFLICT targets
            try:
                cursor.execute('''
                    CREATE UNIQUE INDEX IF NOT EXISTS player_feeders_user_chat_type_key
                    ON player_feeders (user_id, chat_id, feeder_type)
                ''')
            except Exception as e:
                # Ignore if index already exists or not supported
                pass
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS player_echosounder (
                    id INTEGER PRIMARY KEY,
                    user_id BIGINT NOT NULL,
                    chat_id BIGINT DEFAULT 0,
                    expires_at TIMESTAMP NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, chat_id)
                )
            ''')

            # Legacy-safe schema patching: old deployments may already have these
            # tables but with missing columns.
            cursor.execute("ALTER TABLE player_feeders ADD COLUMN IF NOT EXISTS chat_id BIGINT DEFAULT 0")
            cursor.execute("ALTER TABLE player_feeders ADD COLUMN IF NOT EXISTS feeder_type TEXT")
            cursor.execute("ALTER TABLE player_feeders ADD COLUMN IF NOT EXISTS bonus_percent INTEGER DEFAULT 0")
            cursor.execute("ALTER TABLE player_feeders ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP")

            cursor.execute("ALTER TABLE player_echosounder ADD COLUMN IF NOT EXISTS chat_id BIGINT DEFAULT 0")
            cursor.execute("ALTER TABLE player_echosounder ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP")

            # Normalize nullable chat_id for global echosounder mode.
            cursor.execute("UPDATE player_echosounder SET chat_id = 0 WHERE chat_id IS NULL")
            conn.commit()

    def get_active_feeder(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        """Вернуть активную кормушку пользователя для чата (или глобальную)."""
        self._ensure_booster_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT user_id, chat_id, feeder_type, bonus_percent, expires_at
                FROM player_feeders
                WHERE user_id = ?
                  AND (chat_id = ? OR chat_id IS NULL OR chat_id < 1)
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY expires_at DESC
                LIMIT 1
                ''',
                (user_id, chat_id),
            )
            row = cursor.fetchone()
            if not row:
                return None
            cols = [d[0] for d in cursor.description]
            return dict(zip(cols, row))

    def get_feeder_cooldown_remaining(self, user_id: int, chat_id: int) -> int:
        """Вернуть оставшееся время активной кормушки в секундах."""
        self._ensure_booster_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COALESCE(EXTRACT(EPOCH FROM (expires_at - CURRENT_TIMESTAMP)), 0)
                FROM player_feeders
                WHERE user_id = ?
                  AND (chat_id = ? OR chat_id IS NULL OR chat_id < 1)
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY expires_at DESC
                LIMIT 1
                ''',
                (user_id, chat_id),
            )
            row = cursor.fetchone()
            if not row or row[0] is None:
                return 0
            return max(0, int(row[0]))

    def activate_feeder(self, user_id: int, chat_id: int, feeder_type: str, bonus_percent: int, duration_minutes: int):
        """Активировать кормушку для пользователя в текущем чате."""
        self._ensure_booster_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            expires_expr_minutes = int(duration_minutes)
            # Сначала пробуем обновить существующую кормушку
            cursor.execute(
                '''
                UPDATE player_feeders
                SET bonus_percent = ?, expires_at = CURRENT_TIMESTAMP + (? || ' minutes')::interval
                WHERE user_id = ? AND chat_id = ? AND feeder_type = ?
            ''',
                (int(bonus_percent), expires_expr_minutes, user_id, chat_id, feeder_type)
            )
            if cursor.rowcount == 0:
                # Если не было обновлено — вставляем новую
                cursor.execute(
                    '''
                    INSERT INTO player_feeders (user_id, chat_id, feeder_type, bonus_percent, expires_at)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP + (? || ' minutes')::interval)
                ''',
                    (user_id, chat_id, feeder_type, int(bonus_percent), expires_expr_minutes)
                )
            conn.commit()

    def get_echosounder_remaining_seconds(self, user_id: int, chat_id: int) -> int:
        """Вернуть оставшееся время эхолота (глобально на пользователя) в секундах."""
        self._ensure_booster_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT COALESCE(EXTRACT(EPOCH FROM (expires_at - CURRENT_TIMESTAMP)), 0)
                FROM player_echosounder
                WHERE user_id = ?
                  AND chat_id = 0
                  AND expires_at > CURRENT_TIMESTAMP
                ORDER BY expires_at DESC
                LIMIT 1
                ''',
                (user_id,),
            )
            row = cursor.fetchone()
            if not row or row[0] is None:
                return 0
            return max(0, int(row[0]))

    def is_echosounder_active(self, user_id: int, chat_id: int) -> bool:
        """Проверить, активен ли эхолот у пользователя."""
        return self.get_echosounder_remaining_seconds(user_id, chat_id) > 0

    def activate_echosounder(self, user_id: int, chat_id: int, duration_hours: int):
        """Активировать эхолот (глобально на пользователя, независимо от чата)."""
        self._ensure_booster_tables()
        with self._connect() as conn:
            cursor = conn.cursor()
            hours = int(duration_hours)
            cursor.execute(
                '''
                UPDATE player_echosounder
                SET expires_at = CURRENT_TIMESTAMP + (? || ' hours')::interval
                WHERE user_id = ? AND chat_id = 0
                ''',
                (hours, user_id),
            )

            if cursor.rowcount == 0:
                cursor.execute(
                    '''
                    INSERT INTO player_echosounder (user_id, chat_id, expires_at)
                    VALUES (?, 0, CURRENT_TIMESTAMP + (? || ' hours')::interval)
                    ''',
                    (user_id, hours),
                )
            conn.commit()
    
    def get_bait_count(self, user_id: int, bait_name: str) -> int:
        """Получить количество наживки у игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT quantity FROM player_baits 
                WHERE user_id = ? AND bait_name = ?
            ''', (user_id, bait_name))
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def add_bait_to_inventory(self, user_id: int, bait_name: str, quantity: int = 1):
        """Добавить наживку в инвентарь"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO player_baits (user_id, bait_name, quantity)
                VALUES (?, ?, COALESCE((SELECT quantity FROM player_baits WHERE user_id = ? AND bait_name = ?), 0) + ?)
            ''', (user_id, bait_name, user_id, bait_name, quantity))
            conn.commit()
    
    def use_bait(self, user_id: int, bait_name: str) -> bool:
        """Использовать наживку"""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Проверяем количество наживки
            cursor.execute('''
                SELECT quantity FROM player_baits 
                WHERE user_id = ? AND bait_name = ?
            ''', (user_id, bait_name))
            result = cursor.fetchone()
            
            if not result or result[0] <= 0:
                return False
            
            # Уменьшаем количество
            cursor.execute('''
                UPDATE player_baits SET quantity = quantity - 1
                WHERE user_id = ? AND bait_name = ?
            ''', (user_id, bait_name))
            
            # Удаляем если количество 0
            cursor.execute('''
                DELETE FROM player_baits WHERE user_id = ? AND bait_name = ? AND quantity <= 0
            ''', (user_id, bait_name))
            
            conn.commit()
            return True
    
    def get_trash_by_location(self, location: str) -> List[Dict[str, Any]]:
        """Получить список мусора для локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM trash 
                WHERE locations LIKE ? OR locations = 'Все'
                ORDER BY name
            ''', (f"%{location}%",))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            result = [dict(zip(columns, row)) for row in rows]
            # Если нет мусора для конкретной локации — вернём весь мусор 
            if not result:
                cursor.execute('SELECT * FROM trash ORDER BY name')
                rows = cursor.fetchall()
                result = [dict(zip(columns, row)) for row in rows]
            return result
    
    def get_random_trash(self, location: str) -> Optional[Dict[str, Any]]:
        """Получить случайный мусор для локации"""
        trash_list = self.get_trash_by_location(location)
        if not trash_list:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT * FROM trash ORDER BY name')
                rows = cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                trash_list = [dict(zip(columns, row)) for row in rows]
            if not trash_list:
                return None
        
        import random
        return random.choice(trash_list)
    
    def check_bait_suitable_for_fish(self, bait_name: str, fish_name: str) -> bool:
        """Проверить подходит ли наживка для рыбы"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT suitable_baits FROM fish WHERE name = ?
            ''', (fish_name,))
            result = cursor.fetchone()
            
            if not result:
                return False
            
            suitable_baits = result[0]
            if suitable_baits == "Все":
                return True
            
            # Сравниваем без учёта регистра и пробелов
            suitable_list = [b.strip().lower() for b in suitable_baits.split(',') if b.strip()]
            if not bait_name:
                return False
            return bait_name.strip().lower() in suitable_list

    def add_star_transaction(self, user_id: int, telegram_payment_charge_id: str, total_amount: int, refund_status: str = "none", chat_id: Optional[int] = None, chat_title: Optional[str] = None) -> bool:
        """Добавить запись о транзакции Telegram Stars"""
        if not telegram_payment_charge_id:
            return False
        with self._connect() as conn:
            cursor = conn.cursor()
            # If DB has chat_id/chat_title columns, insert them as well when provided via kwargs
            try:
                cursor.execute("PRAGMA table_info(star_transactions)")
                cols = [c[1] for c in cursor.fetchall()]
            except Exception:
                cols = []

            if 'chat_id' in cols and 'chat_title' in cols:
                cursor.execute('''
                    INSERT OR IGNORE INTO star_transactions (user_id, telegram_payment_charge_id, total_amount, chat_id, chat_title, refund_status)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, telegram_payment_charge_id, total_amount, chat_id, chat_title, refund_status))
            else:
                cursor.execute('''
                    INSERT OR IGNORE INTO star_transactions (user_id, telegram_payment_charge_id, total_amount, refund_status)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, telegram_payment_charge_id, total_amount, refund_status))
            conn.commit()
            return cursor.rowcount > 0

    def increment_chat_stars(self, chat_id: int, amount: int, chat_title: Optional[str] = None) -> bool:
        """Увеличить счётчик звёзд для чата. Создаст запись если нужно."""
        if chat_id is None:
            return False
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                # Ensure row exists
                cursor.execute('INSERT OR IGNORE INTO chat_configs (chat_id, admin_user_id, is_configured, chat_title, stars_total) VALUES (?, ?, 1, ?, 0)', (chat_id, 0, chat_title))
                # Update title if provided
                if chat_title is not None:
                    cursor.execute('UPDATE chat_configs SET chat_title = ? WHERE chat_id = ?', (chat_title, chat_id))
                cursor.execute('UPDATE chat_configs SET stars_total = COALESCE(stars_total, 0) + ? WHERE chat_id = ?', (amount, chat_id))
                conn.commit()
                return True
        except Exception as e:
            logger.error("increment_chat_stars error: %s", e)
            return False

    def get_all_chat_stars(self) -> List[Dict[str, Any]]:
        """Return list of chats with their title and total stars, sourced from star_transactions."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT
                    s.chat_id,
                    COALESCE(c.chat_title, '') AS chat_title,
                    COALESCE(s.stars_total, 0) AS stars_total,
                    COALESCE(s.occurrences, 0) AS occurrences
                FROM (
                    SELECT chat_id,
                           SUM(total_amount) AS stars_total,
                           COUNT(*) AS occurrences
                    FROM star_transactions
                    WHERE chat_id IS NOT NULL
                      AND COALESCE(refund_status, 'none') = 'none'
                    GROUP BY chat_id
                ) s
                LEFT JOIN chat_configs c ON c.chat_id = s.chat_id
                ORDER BY s.stars_total DESC NULLS LAST
            ''')
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description]
            return [dict(zip(cols, r)) for r in rows]

    def get_all_chat_ids(self) -> List[int]:
        """Return list of all known chat IDs (from chat_configs).

        Used by admin broadcast commands to iterate over chats.
        """
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT chat_id FROM chat_configs')
                rows = cursor.fetchall()
                return [int(r[0]) for r in rows if r and r[0] is not None]
        except Exception:
            logger.exception("get_all_chat_ids failed")
            return []

    def get_chat_occurrences(self, chat_id: int) -> int:
        """Return number of star_transactions rows for a given chat_id."""
        if chat_id is None:
            return 0
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM star_transactions WHERE chat_id = ?', (chat_id,))
            row = cursor.fetchone()
            return int(row[0]) if row else 0

    def update_chat_title(self, chat_id: int, chat_title: str) -> bool:
        """Update chat title in chat_configs."""
        if chat_id is None or not chat_title:
            return False
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('INSERT OR IGNORE INTO chat_configs (chat_id, admin_user_id, is_configured, chat_title, stars_total) VALUES (?, ?, 1, ?, 0)', (chat_id, 0, chat_title))
            cursor.execute('UPDATE chat_configs SET chat_title = ? WHERE chat_id = ?', (chat_title, chat_id))
            conn.commit()
            return True

    def get_star_transaction(self, telegram_payment_charge_id: str) -> Optional[Dict[str, Any]]:
        """Получить транзакцию по telegram_payment_charge_id"""
        if not telegram_payment_charge_id:
            return None
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM star_transactions WHERE telegram_payment_charge_id = ?
            ''', (telegram_payment_charge_id,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def update_star_refund_status(self, telegram_payment_charge_id: str, refund_status: str) -> bool:
        """Обновить статус возврата по транзакции"""
        if not telegram_payment_charge_id:
            return False
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE star_transactions
                SET refund_status = ?
                WHERE telegram_payment_charge_id = ?
            ''', (refund_status, telegram_payment_charge_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_baits_for_location(self, location: str) -> List[Dict[str, Any]]:
        """Получить наживки, подходящие для рыбы на данной локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Получаем все уникальные наживки для рыб на этой локации
            cursor.execute('''
                SELECT DISTINCT b.*
                FROM baits b
                WHERE EXISTS (
                    SELECT 1 FROM fish f
                    WHERE f.locations LIKE ? 
                    AND (f.suitable_baits LIKE '%' || b.name || '%' OR f.suitable_baits = 'Все')
                )
                AND LOWER(TRIM(b.name)) <> 'живец'
                ORDER BY b.price
            ''', (f'%{location}%',))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def get_player_baits_for_location(self, user_id: int, location: str) -> List[Dict[str, Any]]:
        """Получить наживки игрока, подходящие для локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT b.*, COALESCE(pb.quantity, 0) as player_quantity
                FROM baits b
                LEFT JOIN player_baits pb ON b.name = pb.bait_name AND pb.user_id = ?
                WHERE EXISTS (
                    SELECT 1 FROM fish f
                    WHERE f.locations LIKE ?
                    AND (f.suitable_baits LIKE '%' || b.name || '%' OR f.suitable_baits = 'Все')
                )
                AND COALESCE(pb.quantity, 0) > 0
                ORDER BY b.name
            ''', (user_id, f'%{location}%'))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]

    def get_unsold_trash_summary(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Сводка непроданного мусора игрока в чате."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    cf.fish_name,
                    COUNT(*) AS quantity,
                    COALESCE(SUM(cf.weight), 0) AS total_weight,
                    COALESCE(MAX(t.price), 0) AS unit_price
                FROM caught_fish cf
                LEFT JOIN fish f ON LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(f.name))
                LEFT JOIN trash t ON LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(t.name))
                WHERE cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
                  AND f.name IS NULL
                GROUP BY cf.fish_name
                ORDER BY quantity DESC, cf.fish_name ASC
                ''',
                (int(user_id), int(chat_id)),
            )
            rows = cursor.fetchall() or []

        result: List[Dict[str, Any]] = []
        for fish_name, quantity, total_weight, unit_price in rows:
            qty = int(quantity or 0)
            price = int(unit_price or 0)
            result.append(
                {
                    'fish_name': str(fish_name or ''),
                    'quantity': qty,
                    'total_weight': float(total_weight or 0.0),
                    'unit_price': price,
                    'total_price': qty * price,
                }
            )
        return result

    def convert_small_fish_to_live_bait(self, user_id: int, chat_id: int, quantity: int = 0) -> Dict[str, Any]:
        """Конвертирует мелкую рыбу (Плотва/Верховка) в наживку Живец."""
        qty_limit = max(0, int(quantity or 0))
        placeholders = ','.join('?' for _ in LIVE_BAIT_FISH_NAMES)

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f'''
                SELECT cf.id, cf.fish_name
                FROM caught_fish cf
                JOIN fish f ON LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(f.name))
                WHERE cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
                  AND f.name IN ({placeholders})
                ORDER BY cf.id ASC
                ''',
                [int(user_id), int(chat_id), *LIVE_BAIT_FISH_NAMES],
            )
            rows = cursor.fetchall() or []

            if not rows:
                return {'ok': False, 'reason': 'no_small_fish'}

            selected = rows if qty_limit <= 0 else rows[:qty_limit]
            fish_ids = [int(r[0]) for r in selected]
            converted = len(fish_ids)
            if converted <= 0:
                return {'ok': False, 'reason': 'no_small_fish'}

            fish_counter: Dict[str, int] = {}
            for _, fish_name in selected:
                key = str(fish_name or '')
                fish_counter[key] = int(fish_counter.get(key, 0) or 0) + 1

            sold_placeholders = ','.join('?' for _ in fish_ids)
            cursor.execute(
                f'''
                UPDATE caught_fish
                SET sold = 1, sold_at = CURRENT_TIMESTAMP
                WHERE id IN ({sold_placeholders})
                ''',
                fish_ids,
            )

            cursor.execute(
                '''
                INSERT INTO player_baits (user_id, bait_name, quantity)
                VALUES (?, ?, ?)
                ON CONFLICT (user_id, bait_name)
                DO UPDATE SET quantity = player_baits.quantity + EXCLUDED.quantity
                ''',
                (int(user_id), LIVE_BAIT_NAME, converted),
            )
            conn.commit()

        return {
            'ok': True,
            'converted_count': converted,
            'converted_by_fish': fish_counter,
            'bait_name': LIVE_BAIT_NAME,
            'bait_added': converted,
        }

    def convert_fish_to_bait_by_ids(self, user_id: int, chat_id: int, fish_ids: List[int]) -> Dict[str, Any]:
        """Конвертирует выбранных рыб в наживку по их ID."""
        if not fish_ids:
            return {'ok': False, 'reason': 'no_fish_selected'}

        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 1. Получаем инфу о рыбах
            placeholders = ','.join('?' for _ in fish_ids)
            cursor.execute(
                f'''
                SELECT cf.id, cf.fish_name
                FROM caught_fish cf
                WHERE cf.id IN ({placeholders})
                  AND cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
                ''',
                [*fish_ids, int(user_id), int(chat_id)],
            )
            rows = cursor.fetchall() or []
            if not rows:
                return {'ok': False, 'reason': 'fish_not_found'}

            # 2. Получаем все существующие наживки для сопоставления
            cursor.execute('SELECT name FROM baits')
            existing_baits = {row[0].strip().lower(): row[0] for row in cursor.fetchall()}

            converted_baits: Dict[str, int] = {}
            actual_fish_ids = []
            
            live_bait_fish = [n.strip().lower() for n in LIVE_BAIT_FISH_NAMES]

            for fid, fname in rows:
                fname_clean = str(fname or '').strip()
                fname_lower = fname_clean.lower()
                
                target_bait = None
                
                # Точное совпадение имени рыбы и наживки
                if fname_lower in existing_baits:
                    target_bait = existing_baits[fname_lower]
                # Совпадение с живой наживкой (Живец)
                elif fname_lower in live_bait_fish:
                    target_bait = LIVE_BAIT_NAME
                
                if target_bait:
                    actual_fish_ids.append(fid)
                    converted_baits[target_bait] = converted_baits.get(target_bait, 0) + 1

            if not actual_fish_ids:
                return {'ok': False, 'reason': 'no_convertible_fish'}

            # 3. Помечаем рыбу как использованную
            id_placeholders = ','.join('?' for _ in actual_fish_ids)
            cursor.execute(
                f'UPDATE caught_fish SET sold = 1, sold_at = CURRENT_TIMESTAMP WHERE id IN ({id_placeholders})',
                actual_fish_ids
            )

            # 4. Начисляем наживку
            for bname, qty in converted_baits.items():
                cursor.execute(
                    '''
                    INSERT INTO player_baits (user_id, bait_name, quantity)
                    VALUES (?, ?, ?)
                    ON CONFLICT (user_id, bait_name)
                    DO UPDATE SET quantity = player_baits.quantity + EXCLUDED.quantity
                    ''',
                    (int(user_id), bname, qty),
                )
            
            conn.commit()

        return {
            'ok': True,
            'converted_count': len(actual_fish_ids),
            'details': converted_baits
        }

    def get_convertible_fish_list(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Получить список рыб в инвентаре, которые можно переработать в наживку."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # 1. Получаем все существующие наживки
            cursor.execute('SELECT name FROM baits')
            existing_baits = {row[0].strip().lower() for row in cursor.fetchall()}
            
            # 2. Получаем всех рыб в инвентаре (не проданных)
            cursor.execute('''
                SELECT id, fish_name, weight
                FROM caught_fish
                WHERE user_id = ?
                  AND (chat_id = ? OR chat_id IS NULL OR chat_id < 1)
                  AND COALESCE(sold, 0) = 0
                ORDER BY fish_name ASC, weight DESC
            ''', (int(user_id), int(chat_id)))
            
            rows = cursor.fetchall() or []
            
            convertible = []
            live_bait_fish = {n.strip().lower() for n in LIVE_BAIT_FISH_NAMES}
            
            for fid, fname, weight in rows:
                fname_lower = str(fname or '').strip().lower()
                if fname_lower in existing_baits or fname_lower in live_bait_fish:
                    convertible.append({
                        'id': fid,
                        'name': fname,
                        'weight': weight
                    })
            return convertible

    def donate_trash_to_clan(self, user_id: int, chat_id: int, item_name: str, quantity: int) -> Dict[str, Any]:
        """Пожертвовать мусор в артель, списав его из инвентаря игрока."""
        clan = self.get_clan_by_user(user_id)
        if not clan:
            return {'ok': False, 'reason': 'not_in_clan'}

        donate_qty = max(1, int(quantity or 1))
        clean_item = str(item_name or '').strip()
        if not clean_item:
            return {'ok': False, 'reason': 'bad_item'}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT cf.id
                FROM caught_fish cf
                LEFT JOIN fish f ON LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(f.name))
                WHERE cf.user_id = ?
                  AND (cf.chat_id = ? OR cf.chat_id IS NULL OR cf.chat_id < 1)
                  AND COALESCE(cf.sold, 0) = 0
                  AND f.name IS NULL
                  AND LOWER(TRIM(cf.fish_name)) = LOWER(TRIM(?))
                ORDER BY cf.id ASC
                LIMIT ?
                ''',
                (int(user_id), int(chat_id), clean_item, donate_qty),
            )
            rows = cursor.fetchall() or []
            selected_ids = [int(r[0]) for r in rows]

            if len(selected_ids) < donate_qty:
                return {
                    'ok': False,
                    'reason': 'not_enough_trash',
                    'available': len(selected_ids),
                    'required': donate_qty,
                }

            sold_placeholders = ','.join('?' for _ in selected_ids)
            cursor.execute(
                f'''
                UPDATE caught_fish
                SET sold = 1, sold_at = CURRENT_TIMESTAMP
                WHERE id IN ({sold_placeholders})
                ''',
                selected_ids,
            )

            cursor.execute(
                '''
                INSERT INTO clan_donations (clan_id, item_name, quantity, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (clan_id, item_name)
                DO UPDATE SET
                    quantity = clan_donations.quantity + EXCLUDED.quantity,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (int(clan['id']), clean_item, donate_qty),
            )
            cursor.execute(
                '''
                SELECT quantity
                FROM clan_donations
                WHERE clan_id = ? AND item_name = ?
                ''',
                (int(clan['id']), clean_item),
            )
            total_row = cursor.fetchone()
            conn.commit()

        return {
            'ok': True,
            'clan_id': int(clan['id']),
            'item_name': clean_item,
            'donated': donate_qty,
            'clan_total': int(total_row[0] or 0) if total_row else donate_qty,
        }

    def get_webapp_book_entries(self, user_id: Optional[int] = None, search: str = '', limit: int = 128) -> List[Dict[str, Any]]:
        """Список рыб для webapp-книги с базовой лор-информацией."""
        safe_limit = max(1, min(int(limit or 128), 500))
        search_term = str(search or '').strip()
        like_pattern = f"%{search_term}%" if search_term else "%"
        safe_user_id = int(user_id) if user_id is not None else 0

        fish_stickers: Dict[str, str] = {}
        try:
            from fish_stickers import FISH_STICKERS
            fish_stickers = dict(FISH_STICKERS or {})
        except Exception:
            fish_stickers = {}

        caught_name_set: set[str] = set()
        if safe_user_id > 0:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT DISTINCT LOWER(TRIM(fish_name))
                    FROM caught_fish
                    WHERE user_id = ?
                    ''',
                    (safe_user_id,),
                )
                rows_caught = cursor.fetchall() or []
                for row in rows_caught:
                    if row and row[0]:
                        caught_name_set.add(str(row[0]))

                cursor.execute(
                    '''
                    SELECT DISTINCT LOWER(TRIM(fish_name))
                    FROM player_trophies
                    WHERE user_id = ?
                    ''',
                    (safe_user_id,),
                )
                rows_trophies = cursor.fetchall() or []
                for row in rows_trophies:
                    if row and row[0]:
                        caught_name_set.add(str(row[0]))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT name, rarity, min_weight, max_weight, min_length, max_length, locations, suitable_baits, price
                FROM fish
                WHERE LOWER(TRIM(name)) LIKE LOWER(TRIM(?))
                ORDER BY
                    CASE rarity
                        WHEN 'Аномалия' THEN 6
                        WHEN 'Мифическая' THEN 5
                        WHEN 'Легендарная' THEN 4
                        WHEN 'Аквариумная' THEN 3
                        WHEN 'Редкая' THEN 2
                        ELSE 1
                    END DESC,
                    name ASC
                LIMIT ?
                ''',
                (like_pattern, safe_limit),
            )
            rows = cursor.fetchall() or []

        items: List[Dict[str, Any]] = []
        for idx, row in enumerate(rows, start=1):
            fish_name = str(row[0] or '')
            rarity = str(row[1] or 'Обычная')
            min_weight = float(row[2] or 0.0)
            max_weight = float(row[3] or 0.0)
            min_length = float(row[4] or 0.0)
            max_length = float(row[5] or 0.0)
            locations = str(row[6] or 'Неизвестно')
            baits = str(row[7] or 'Неизвестно')
            image_file = str(fish_stickers.get(fish_name) or 'fishdef.webp')
            is_caught = str(fish_name).strip().lower() in caught_name_set

            lore = (
                f"{fish_name} чаще встречается в локациях: {locations}. "
                f"Рекомендуемая наживка: {baits}."
            )

            items.append(
                {
                    'index': idx,
                    'name': fish_name,
                    'rarity': rarity,
                    'min_weight': round(min_weight, 2),
                    'max_weight': round(max_weight, 2),
                    'min_length': round(min_length, 1),
                    'max_length': round(max_length, 1),
                    'locations': locations,
                    'baits': baits,
                    'price': int(row[8] or 0),
                    'lore': lore,
                    'is_caught': is_caught,
                    'catch_status': 'Поймана' if is_caught else 'НЕ СЛОВЛЕНА',
                    'image_url': f'/api/fish-image/{image_file}',
                }
            )

        return items

    def get_webapp_book_total_count(self) -> int:
        """Общее количество рыб в игре для пагинации книги."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM fish')
            row = cursor.fetchone()
            return int((row[0] if row else 0) or 0)

    def get_webapp_adventures_state(self, user_id: int) -> Dict[str, Any]:
        """Сводка по приключениям: личные рекорды и топы по играм."""
        safe_user_id = int(user_id)
        result: Dict[str, Any] = {'games': {}, 'tops': {}}

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute(
                '''
                SELECT game_code, best_score, best_distance, runs_count
                FROM webapp_adventure_scores
                WHERE user_id = ?
                ''',
                (safe_user_id,),
            )
            personal_rows = cursor.fetchall() or []
            for game_code, best_score, best_distance, runs_count in personal_rows:
                result['games'][str(game_code)] = {
                    'best_score': int(best_score or 0),
                    'best_distance': float(best_distance or 0.0),
                    'runs_count': int(runs_count or 0),
                }

            for game_code in ('runner', 'maze'):
                cursor.execute(
                    '''
                    SELECT s.user_id,
                           COALESCE(MAX(p.username), 'user') AS username,
                           s.best_score,
                           s.best_distance
                    FROM webapp_adventure_scores s
                    LEFT JOIN players p ON p.user_id = s.user_id
                    WHERE s.game_code = ?
                    GROUP BY s.user_id, s.best_score, s.best_distance
                    ORDER BY s.best_score DESC, s.best_distance DESC, s.user_id ASC
                    LIMIT 10
                    ''',
                    (game_code,),
                )
                top_rows = cursor.fetchall() or []
                top_items: List[Dict[str, Any]] = []
                for idx, row in enumerate(top_rows, start=1):
                    top_items.append(
                        {
                            'place': idx,
                            'user_id': int(row[0] or 0),
                            'username': str(row[1] or 'user'),
                            'best_score': int(row[2] or 0),
                            'best_distance': float(row[3] or 0.0),
                        }
                    )
                result['tops'][game_code] = top_items

        for code in ('runner', 'maze'):
            result['games'].setdefault(code, {'best_score': 0, 'best_distance': 0.0, 'runs_count': 0})
            result['tops'].setdefault(code, [])

        return result

    def save_webapp_adventure_result(self, user_id: int, game_code: str, score: int, distance: float = 0.0) -> Dict[str, Any]:
        """Сохранить результат приключения и вернуть обновленную статистику игрока."""
        safe_user_id = int(user_id)
        safe_code = str(game_code or '').strip().lower()
        if safe_code not in ('runner', 'maze'):
            return {'ok': False, 'reason': 'invalid_game_code'}

        safe_score = max(0, int(score or 0))
        safe_distance = max(0.0, float(distance or 0.0))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO webapp_adventure_scores (user_id, game_code, best_score, best_distance, runs_count, updated_at)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                ON CONFLICT (user_id, game_code)
                DO UPDATE SET
                    best_score = GREATEST(webapp_adventure_scores.best_score, EXCLUDED.best_score),
                    best_distance = GREATEST(webapp_adventure_scores.best_distance, EXCLUDED.best_distance),
                    runs_count = webapp_adventure_scores.runs_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (safe_user_id, safe_code, safe_score, safe_distance),
            )

            cursor.execute(
                '''
                SELECT best_score, best_distance, runs_count
                FROM webapp_adventure_scores
                WHERE user_id = ? AND game_code = ?
                LIMIT 1
                ''',
                (safe_user_id, safe_code),
            )
            row = cursor.fetchone()

            if row:
                best_score = int(row[0] or 0)
                best_distance = float(row[1] or 0.0)
                runs_count = int(row[2] or 0)
            else:
                best_score = safe_score
                best_distance = safe_distance
                runs_count = 1

            cursor.execute(
                '''
                SELECT COUNT(*)
                FROM webapp_adventure_scores
                WHERE game_code = ?
                  AND (best_score > ? OR (best_score = ? AND best_distance > ?))
                ''',
                (safe_code, best_score, best_score, best_distance),
            )
            rank_row = cursor.fetchone()
            rank = int((rank_row[0] if rank_row else 0) or 0) + 1
            conn.commit()

        return {
            'ok': True,
            'game_code': safe_code,
            'best_score': best_score,
            'best_distance': best_distance,
            'runs_count': runs_count,
            'rank': rank,
        }

    def get_webapp_guilds_snapshot(self, user_id: int, limit: int = 20) -> Dict[str, Any]:
        """Снимок артелей для webapp: моя артель и топ списка."""
        my_clan = self.get_clan_by_user(int(user_id))
        clans = self.list_clans(limit=max(1, min(int(limit or 20), 50)))

        clan_ids: List[int] = []
        for clan in clans:
            try:
                clan_ids.append(int(clan.get('id') or 0))
            except Exception:
                continue
        if my_clan:
            try:
                my_id = int(my_clan.get('id') or 0)
                if my_id > 0 and my_id not in clan_ids:
                    clan_ids.append(my_id)
            except Exception:
                pass

        requests_by_clan: Dict[int, List[Dict[str, Any]]] = {}
        if my_clan and str(my_clan.get('role') or '') == 'leader':
            try:
                my_clan_id = int(my_clan.get('id') or 0)
                if my_clan_id > 0:
                    requests_by_clan[my_clan_id] = self.get_webapp_clan_requests(my_clan_id, limit=limit)
            except Exception:
                logger.exception("Failed to load clan requests for user_id=%s", user_id)

        profiles_by_clan: Dict[int, Dict[str, Any]] = {}
        if clan_ids:
            placeholders = ','.join('?' for _ in clan_ids)
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    f'''
                    SELECT clan_id, avatar_emoji, color_hex, access_type, description, min_level
                    FROM webapp_clan_profiles
                    WHERE clan_id IN ({placeholders})
                    ''',
                    clan_ids,
                )
                rows = cursor.fetchall() or []
                for row in rows:
                    cid = int(row[0] or 0)
                    profiles_by_clan[cid] = {
                        'avatar_emoji': str(row[1] or '🏰'),
                        'color_hex': str(row[2] or '#00b4d8'),
                        'access_type': str(row[3] or 'open'),
                        'description': str(row[4] or ''),
                        'min_level': int(row[5] or 0),
                    }

        def _merge_profile(clan: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
            if not clan:
                return None
            cid = int(clan.get('id') or 0)
            profile = profiles_by_clan.get(cid) or {
                'avatar_emoji': '🏰',
                'color_hex': '#00b4d8',
                'access_type': 'open',
                'description': '',
            }
            merged = {**clan, **profile}
            if cid in requests_by_clan:
                merged['requests'] = requests_by_clan.get(cid, [])
            return merged

        return {
            'my_clan': _merge_profile(my_clan),
            'items': [_merge_profile(clan) for clan in clans if clan],
        }

    def save_webapp_clan_profile(
        self,
        clan_id: int,
        avatar_emoji: str,
        color_hex: str,
        access_type: str,
        description: str,
        updated_by: int,
        min_level: int = 0,
    ) -> Dict[str, Any]:
        """Сохранить визуальный профиль артели для webapp."""
        safe_clan_id = int(clan_id)
        safe_updated_by = int(updated_by)
        safe_avatar = str(avatar_emoji or '🏰').strip() or '🏰'
        safe_color = str(color_hex or '#00b4d8').strip() or '#00b4d8'
        safe_access = str(access_type or 'open').strip().lower()
        if safe_access not in ('open', 'invite'):
            safe_access = 'open'
        safe_desc = str(description or '').strip()[:500]
        safe_min_level = max(0, int(min_level or 0))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                INSERT INTO webapp_clan_profiles (clan_id, avatar_emoji, color_hex, access_type, description, min_level, created_by, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT (clan_id)
                DO UPDATE SET
                    avatar_emoji = EXCLUDED.avatar_emoji,
                    color_hex = EXCLUDED.color_hex,
                    access_type = EXCLUDED.access_type,
                    description = EXCLUDED.description,
                    min_level = EXCLUDED.min_level,
                    created_by = EXCLUDED.created_by,
                    updated_at = CURRENT_TIMESTAMP
                ''',
                (safe_clan_id, safe_avatar, safe_color, safe_access, safe_desc, safe_min_level, safe_updated_by),
            )
            conn.commit()

        return {
            'ok': True,
            'clan_id': safe_clan_id,
            'avatar_emoji': safe_avatar,
            'color_hex': safe_color,
            'access_type': safe_access,
            'description': safe_desc,
        }

    def add_webapp_clan_request(self, user_id: int, clan_id: int) -> Dict[str, Any]:
        """Создать или переоткрыть заявку на вступление в артель."""
        safe_user_id = int(user_id)
        safe_clan_id = int(clan_id)

        if self.get_clan_by_user(safe_user_id):
            return {'ok': False, 'reason': 'already_in_clan'}

        clan = self.get_clan_by_id(safe_clan_id)
        if not clan:
            return {'ok': False, 'reason': 'clan_not_found'}

        members_count = int(clan.get('members_count') or 0)
        max_members = int(clan.get('max_members') or self.get_clan_member_limit(int(clan.get('level') or 1)))
        if members_count >= max_members:
            return {'ok': False, 'reason': 'clan_full'}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT min_level, access_type FROM webapp_clan_profiles WHERE clan_id = ?',
                (safe_clan_id,),
            )
            profile_row = cursor.fetchone()
            if not profile_row:
                return {'ok': False, 'reason': 'clan_not_found'}

            access_type = str(profile_row[1] or 'open')
            if access_type != 'invite':
                return {'ok': False, 'reason': 'not_invite_only'}

            min_level = int(profile_row[0] or 0)
            cursor.execute('SELECT level FROM players WHERE user_id = ? LIMIT 1', (safe_user_id,))
            user_row = cursor.fetchone()
            user_level = int(user_row[0] or 0) if user_row else 0
            if user_level < min_level:
                return {'ok': False, 'reason': 'level_too_low', 'required': min_level}

            cursor.execute(
                '''
                INSERT INTO webapp_clan_requests (clan_id, requester_user_id, status, created_at, processed_at)
                VALUES (?, ?, 'pending', CURRENT_TIMESTAMP, NULL)
                ON CONFLICT (clan_id, requester_user_id)
                DO UPDATE SET
                    status = 'pending',
                    created_at = CURRENT_TIMESTAMP,
                    processed_at = NULL
                ''',
                (safe_clan_id, safe_user_id),
            )
            request_id = int(cursor.lastrowid or 0)
            conn.commit()

        return {
            'ok': True,
            'request_id': request_id,
            'clan_id': safe_clan_id,
            'status': 'pending',
        }

    def get_webapp_clan_requests(self, clan_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить входящие заявки в конкретную артель."""
        safe_clan_id = int(clan_id)
        safe_limit = max(1, min(int(limit or 50), 200))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT
                    r.id,
                    r.requester_user_id,
                    COALESCE(MAX(p.username), 'user') AS username,
                    MAX(p.level) AS level,
                    r.created_at
                FROM webapp_clan_requests r
                LEFT JOIN players p ON p.user_id = r.requester_user_id
                WHERE r.clan_id = ?
                  AND r.status = 'pending'
                GROUP BY r.id, r.requester_user_id, r.created_at
                ORDER BY r.created_at DESC, r.id DESC
                LIMIT ?
                ''',
                (safe_clan_id, safe_limit),
            )
            rows = cursor.fetchall() or []

        result: List[Dict[str, Any]] = []
        for request_id, requester_user_id, username, level, created_at in rows:
            result.append(
                {
                    'request_id': int(request_id or 0),
                    'user_id': int(requester_user_id or 0),
                    'username': str(username or 'user'),
                    'level': int(level or 0),
                    'user_avatar': '👤',
                    'created_at': created_at,
                }
            )
        return result

    def respond_webapp_clan_request(self, user_id: int, request_id: int, action: str) -> Dict[str, Any]:
        """Принять или отклонить заявку в артель."""
        safe_user_id = int(user_id)
        safe_request_id = int(request_id)
        normalized_action = str(action or '').strip().lower()
        if normalized_action not in {'accept', 'decline'}:
            return {'ok': False, 'reason': 'invalid_action'}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT r.id, r.clan_id, r.requester_user_id, r.status, c.owner_user_id
                FROM webapp_clan_requests r
                JOIN clans c ON c.id = r.clan_id
                WHERE r.id = ?
                LIMIT 1
                ''',
                (safe_request_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'reason': 'request_not_found'}

            _, clan_id, requester_user_id, status, owner_user_id = row
            if int(owner_user_id or 0) != safe_user_id:
                return {'ok': False, 'reason': 'forbidden'}
            if str(status or '') != 'pending':
                return {'ok': False, 'reason': 'request_already_processed'}

            next_status = 'accepted' if normalized_action == 'accept' else 'declined'

            if normalized_action == 'accept':
                join_result = self.join_clan(int(requester_user_id or 0), int(clan_id or 0))
                if not join_result.get('ok'):
                    return join_result

            cursor.execute(
                '''
                UPDATE webapp_clan_requests
                SET status = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (next_status, safe_request_id),
            )
            conn.commit()

        return {'ok': True, 'request_id': safe_request_id, 'status': next_status}

    def get_webapp_friends(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Получить список друзей пользователя для webapp."""
        safe_user_id = int(user_id)
        safe_limit = max(1, min(int(limit or 50), 200))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT f.friend_user_id,
                       COALESCE(MAX(p.username), 'user') AS username,
                       MAX(p.last_fish_time) AS last_fish_time,
                       MAX(p.level) AS level
                FROM webapp_friend_links f
                LEFT JOIN players p ON p.user_id = f.friend_user_id
                WHERE f.user_id = ?
                GROUP BY f.friend_user_id
                ORDER BY username ASC
                LIMIT ?
                ''',
                (safe_user_id, safe_limit),
            )
            rows = cursor.fetchall() or []

        result: List[Dict[str, Any]] = []
        now_utc = datetime.now(timezone.utc)
        for friend_user_id, username, last_fish_time, level in rows:
            status_text = 'давно не заходил'
            if last_fish_time:
                dt_val = self._parse_utc_datetime(last_fish_time)
                if dt_val is not None:
                    minutes = int(max(0.0, (now_utc - dt_val).total_seconds()) // 60)
                    if minutes <= 2:
                        status_text = 'в сети'
                    elif minutes < 60:
                        status_text = f'{minutes} мин назад'
                    else:
                        hours = minutes // 60
                        status_text = f'{hours} ч назад'

            result.append(
                {
                    'user_id': int(friend_user_id or 0),
                    'username': str(username or 'user'),
                    'level': int(level or 0),
                    'status': status_text,
                    'is_online': status_text == 'в сети',
                }
            )

        return result

    def add_webapp_friend_by_username(self, user_id: int, username: str) -> Dict[str, Any]:
        """Создать заявку в друзья по username."""
        safe_user_id = int(user_id)
        raw_username = str(username or '').strip()
        if not raw_username:
            return {'ok': False, 'reason': 'username_required'}

        clean_username = raw_username[1:] if raw_username.startswith('@') else raw_username

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT user_id
                FROM players
                WHERE LOWER(TRIM(username)) = LOWER(TRIM(?))
                   OR LOWER(TRIM(username)) = LOWER(TRIM(?))
                ORDER BY created_at DESC
                LIMIT 1
                ''',
                (clean_username, f'@{clean_username}'),
            )
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'reason': 'user_not_found'}

            friend_user_id = int(row[0] or 0)
            if friend_user_id <= 0:
                return {'ok': False, 'reason': 'user_not_found'}
            if friend_user_id == safe_user_id:
                return {'ok': False, 'reason': 'cannot_add_self'}

            cursor.execute(
                '''
                SELECT 1
                FROM webapp_friend_links
                WHERE user_id = ? AND friend_user_id = ?
                LIMIT 1
                ''',
                (safe_user_id, friend_user_id),
            )
            if cursor.fetchone():
                return {'ok': False, 'reason': 'already_friends'}

            cursor.execute(
                '''
                SELECT id
                FROM webapp_friend_requests
                WHERE requester_user_id = ?
                  AND addressee_user_id = ?
                  AND status = 'pending'
                LIMIT 1
                ''',
                (safe_user_id, friend_user_id),
            )
            existing_pending = cursor.fetchone()
            if existing_pending:
                return {
                    'ok': True,
                    'request_id': int(existing_pending[0] or 0),
                    'username': f'@{clean_username}',
                    'already_pending': True,
                }

            cursor.execute(
                '''
                SELECT id
                FROM webapp_friend_requests
                WHERE requester_user_id = ?
                  AND addressee_user_id = ?
                  AND status = 'pending'
                LIMIT 1
                ''',
                (friend_user_id, safe_user_id),
            )
            reverse_pending = cursor.fetchone()
            if reverse_pending:
                return {
                    'ok': False,
                    'reason': 'incoming_request_exists',
                    'request_id': int(reverse_pending[0] or 0),
                }

            cursor.execute(
                '''
                INSERT INTO webapp_friend_requests (requester_user_id, addressee_user_id, status, created_at)
                VALUES (?, ?, 'pending', CURRENT_TIMESTAMP)
                ''',
                (safe_user_id, friend_user_id),
            )
            request_id = int(cursor.lastrowid or 0)
            conn.commit()

        return {
            'ok': True,
            'request_id': request_id,
            'friend_user_id': friend_user_id,
            'username': f'@{clean_username}',
        }

    def get_webapp_friend_requests(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Входящие заявки в друзья для webapp."""
        safe_user_id = int(user_id)
        safe_limit = max(1, min(int(limit or 50), 200))

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT fr.id,
                       fr.requester_user_id,
                       COALESCE(MAX(p.username), 'user') AS username,
                       MAX(p.level) AS level,
                       fr.created_at
                FROM webapp_friend_requests fr
                LEFT JOIN players p ON p.user_id = fr.requester_user_id
                WHERE fr.addressee_user_id = ?
                  AND fr.status = 'pending'
                GROUP BY fr.id, fr.requester_user_id, fr.created_at
                ORDER BY fr.created_at DESC, fr.id DESC
                LIMIT ?
                ''',
                (safe_user_id, safe_limit),
            )
            rows = cursor.fetchall() or []

        result: List[Dict[str, Any]] = []
        for request_id, requester_user_id, username, level, created_at in rows:
            result.append(
                {
                    'request_id': int(request_id or 0),
                    'requester_user_id': int(requester_user_id or 0),
                    'username': str(username or 'user'),
                    'level': int(level or 0),
                    'created_at': created_at,
                }
            )
        return result

    def respond_webapp_friend_request(self, user_id: int, request_id: int, action: str) -> Dict[str, Any]:
        """Принять или отклонить заявку в друзья."""
        safe_user_id = int(user_id)
        safe_request_id = int(request_id)
        normalized_action = str(action or '').strip().lower()
        if normalized_action not in {'accept', 'decline'}:
            return {'ok': False, 'reason': 'invalid_action'}

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                '''
                SELECT id, requester_user_id, addressee_user_id, status
                FROM webapp_friend_requests
                WHERE id = ?
                LIMIT 1
                ''',
                (safe_request_id,),
            )
            row = cursor.fetchone()
            if not row:
                return {'ok': False, 'reason': 'request_not_found'}

            _, requester_user_id, addressee_user_id, status = row
            if int(addressee_user_id or 0) != safe_user_id:
                return {'ok': False, 'reason': 'forbidden'}
            if str(status or '') != 'pending':
                return {'ok': False, 'reason': 'request_already_processed'}

            next_status = 'accepted' if normalized_action == 'accept' else 'declined'
            cursor.execute(
                '''
                UPDATE webapp_friend_requests
                SET status = ?, processed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                ''',
                (next_status, safe_request_id),
            )

            if normalized_action == 'accept':
                requester = int(requester_user_id or 0)
                addressee = int(addressee_user_id or 0)
                cursor.execute(
                    '''
                    INSERT INTO webapp_friend_links (user_id, friend_user_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, friend_user_id) DO NOTHING
                    ''',
                    (requester, addressee),
                )
                cursor.execute(
                    '''
                    INSERT INTO webapp_friend_links (user_id, friend_user_id, created_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, friend_user_id) DO NOTHING
                    ''',
                    (addressee, requester),
                )
            conn.commit()

        return {'ok': True, 'request_id': safe_request_id, 'status': next_status}

    def get_weather(self, location: str) -> Optional[Dict[str, Any]]:
        """Получить погоду локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM weather WHERE location = ?', (location,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def get_or_update_weather(self, location: str) -> Dict[str, Any]:
        """Получить или обновить информацию о погоде"""
        from weather import weather_system

        with self._connect() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT * FROM weather WHERE location = ?', (location,))
            row = cursor.fetchone()

            if not row:
                condition, temp = weather_system.generate_weather(location)
                cursor.execute('''
                    INSERT INTO weather (location, condition, temperature)
                    VALUES (?, ?, ?)
                ''', (location, condition, temp))
                conn.commit()
                cursor.execute('SELECT * FROM weather WHERE location = ?', (location,))
                row = cursor.fetchone()

            columns = [description[0] for description in cursor.description]
            weather = dict(zip(columns, row))

            if weather_system.should_update_weather(weather['last_updated']):
                new_condition, new_temp = weather_system.generate_weather(location)
                cursor.execute('''
                    UPDATE weather 
                    SET condition = ?, temperature = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE location = ? AND last_updated = ?
                ''', (new_condition, new_temp, location, weather['last_updated']))
                conn.commit()

                if cursor.rowcount:
                    cursor.execute('SELECT * FROM weather WHERE location = ?', (location,))
                    row = cursor.fetchone()
                    columns = [description[0] for description in cursor.description]
                    weather = dict(zip(columns, row))
                else:
                    # Погода уже обновлена другим процессом/запросом
                    cursor.execute('SELECT * FROM weather WHERE location = ?', (location,))
                    row = cursor.fetchone()
                    columns = [description[0] for description in cursor.description]
                    weather = dict(zip(columns, row))

            return weather

    def update_weather(self, location: str, condition: str, temperature: int):
        """Обновить погоду локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE weather 
                SET condition = ?, temperature = ?, last_updated = CURRENT_TIMESTAMP
                WHERE location = ?
            ''', (condition, temperature, location))
            conn.commit()

    def init_player_rod(self, user_id: int, rod_name: str, chat_id: int):
        """Инициализировать удочку для игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            rod = self.get_rod(rod_name)
            if not rod:
                return False
            uses = self._get_temp_rod_uses(rod_name)
            if uses is None:
                uses = rod['max_durability']

            # Initialize as a GLOBAL rod entry (chat_id = -1) so rod state is shared across chats
            cursor.execute('''
                INSERT OR IGNORE INTO player_rods (user_id, rod_name, current_durability, max_durability, chat_id)
                VALUES (?, ?, ?, ?, -1)
            ''', (user_id, rod_name, uses, uses))
            conn.commit()
            return True

    def get_player_rod(self, user_id: int, rod_name: str, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить состояние удочки игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Prefer a global rod row (chat_id IS NULL or <1)
            cursor.execute('SELECT * FROM player_rods WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ? LIMIT 1', (user_id, rod_name))
            row = cursor.fetchone()
            if not row:
                # Fallback to any per-chat row for compatibility
                cursor.execute('SELECT * FROM player_rods WHERE user_id = ? AND rod_name = ? LIMIT 1', (user_id, rod_name))
                row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None

    def consume_temp_rod_use(self, user_id: int, rod_name: str, chat_id: int) -> Dict[str, Any]:
        """Списать один удачный улов для временной удочки"""
        if rod_name == BAMBOO_ROD:
            return {"remaining": None, "broken": False}

        if rod_name not in TEMP_ROD_RANGES:
            return {"remaining": None, "broken": False}

        with self._connect() as conn:
            cursor = conn.cursor()
            # Prefer global rod row
            cursor.execute('''
                SELECT current_durability, max_durability FROM player_rods
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
            ''', (user_id, rod_name))
            row = cursor.fetchone()
            if not row:
                # No global rod found - initialize a global rod
                self.init_player_rod(user_id, rod_name, chat_id)
                cursor.execute('''
                    SELECT current_durability, max_durability FROM player_rods
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
                ''', (user_id, rod_name))
                row = cursor.fetchone()

            current_dur, max_dur = row if row else (0, 0)
            current_dur = max(0, current_dur - 1)
            if current_dur <= 0:
                # Delete the global rod entry
                cursor.execute('DELETE FROM player_rods WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?', (user_id, rod_name))
                conn.commit()
                return {"remaining": 0, "max": max_dur, "broken": True}

            cursor.execute('''
                UPDATE player_rods SET current_durability = ?
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
            ''', (current_dur, user_id, rod_name))
            conn.commit()
            return {"remaining": current_dur, "max": max_dur, "broken": False}

    def reduce_rod_durability(self, user_id: int, rod_name: str, damage: int, chat_id: int):
        """Уменьшить прочность удочки"""
        if rod_name != BAMBOO_ROD:
            return
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Проверяем, существует ли запись для этой удочки
            cursor.execute('''
                SELECT current_durability FROM player_rods 
                WHERE user_id = %s AND (chat_id IS NULL OR chat_id < 1) AND rod_name = %s
            ''', (user_id, rod_name))
            
            result = cursor.fetchone()
            if not result:
                # Если записи нет - инициализируем удочку в этом чате
                self.init_player_rod(user_id, rod_name, chat_id=chat_id)
            
            # Уменьшаем прочность
            cursor.execute('''
                UPDATE player_rods 
                SET current_durability = GREATEST(0, current_durability - %s)
                WHERE user_id = %s AND (chat_id IS NULL OR chat_id < 1) AND rod_name = %s
            ''', (damage, user_id, rod_name))
            conn.commit()
            
            # Запускаем процесс восстановления, если еще не запущен
            self.start_rod_recovery(user_id, rod_name, chat_id)

    def repair_rod(self, user_id: int, rod_name: str, chat_id: int):
        """Полностью восстановить удочку"""
        if rod_name != BAMBOO_ROD:
            return
        with self._connect() as conn:
            cursor = conn.cursor()
            rod = self.get_rod(rod_name)
            if rod:
                cursor.execute('''
                    UPDATE player_rods 
                    SET current_durability = ?, recovery_start_time = NULL, last_repair_time = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
                ''', (rod['max_durability'], user_id, rod_name))
                conn.commit()

    def start_rod_recovery(self, user_id: int, rod_name: str, chat_id: int):
        """Начать процесс восстановления удочки"""
        if rod_name != BAMBOO_ROD:
            return
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE player_rods 
                SET recovery_start_time = CURRENT_TIMESTAMP
                WHERE user_id = %s AND (chat_id IS NULL OR chat_id < 1) AND rod_name = %s
            ''', (user_id, rod_name))
            conn.commit()

    def recover_rod_durability(self, user_id: int, rod_name: str, recovery_amount: int, chat_id: int):
        """Восстановить прочность удочки на указанное значение"""
        if rod_name != BAMBOO_ROD:
            return
        with self._connect() as conn:
            cursor = conn.cursor()
            rod = self.get_rod(rod_name)
            if rod:
                cursor.execute('''
                    UPDATE player_rods 
                    SET current_durability = LEAST(%s, current_durability + %s)
                    WHERE user_id = %s AND (chat_id IS NULL OR chat_id < 1) AND rod_name = %s
                ''', (rod['max_durability'], recovery_amount, user_id, rod_name))
                conn.commit()

    # ==================== МЕТОДЫ ДЛЯ РАБОТЫ С СЕТЯМИ ====================
    
    def get_nets(self) -> List[Dict[str, Any]]:
        """Получить список всех сетей"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nets ORDER BY price')
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in rows]
    
    def get_net(self, net_name: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о сети"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM nets WHERE name = ?', (net_name,))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def init_player_net(self, user_id: int, net_name: str, chat_id: int):
        """Инициализировать сеть для игрока в конкретном чате"""
        net = self.get_net(net_name)
        if not net:
            return
        
        with self._connect() as conn:
            cursor = conn.cursor()
            # Initialize as a GLOBAL player_net (chat_id = -1) so nets/uses are shared across chats
            cursor.execute('''
                INSERT OR IGNORE INTO player_nets (user_id, net_name, uses_left, chat_id)
                VALUES (?, ?, ?, -1)
            ''', (user_id, net_name, net['max_uses']))
            conn.commit()
    
    def get_player_net(self, user_id: int, net_name: str, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о сети игрока в конкретном чате"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Prefer a global player_net row (chat_id IS NULL or <1)
            cursor.execute('''
                SELECT pn.*, n.price, n.fish_count, n.cooldown_hours, n.max_uses, n.description
                FROM player_nets pn
                JOIN nets n ON pn.net_name = n.name
                WHERE pn.user_id = ? AND (pn.chat_id IS NULL OR pn.chat_id < 1) AND pn.net_name = ?
                LIMIT 1
            ''', (user_id, net_name))
            row = cursor.fetchone()
            if row:
                columns = [description[0] for description in cursor.description]
                return dict(zip(columns, row))
            return None
    
    def get_player_nets(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Получить все сети игрока в конкретном чате"""
        with self._connect() as conn:
            cursor = conn.cursor()
            # Prefer global entries for player nets
            cursor.execute('''
                SELECT pn.*, n.price, n.fish_count, n.cooldown_hours, n.max_uses, n.description
                FROM player_nets pn
                JOIN nets n ON pn.net_name = n.name
                WHERE pn.user_id = ? AND (pn.chat_id IS NULL OR pn.chat_id < 1)
                ORDER BY n.price
            ''', (user_id,))
            rows = cursor.fetchall()
            columns = [description[0] for description in cursor.description]
            nets = [dict(zip(columns, row)) for row in rows]
            if not nets:
                # Initialize global default net and re-query
                self.init_player_net(user_id, 'Базовая сеть', chat_id)
                cursor.execute('''
                    SELECT pn.*, n.price, n.fish_count, n.cooldown_hours, n.max_uses, n.description
                    FROM player_nets pn
                    JOIN nets n ON pn.net_name = n.name
                    WHERE pn.user_id = ? AND (pn.chat_id IS NULL OR pn.chat_id < 1)
                    ORDER BY n.price
                ''', (user_id,))
                rows = cursor.fetchall()
                nets = [dict(zip(columns, row)) for row in rows]
            return nets

    def grant_net(self, user_id: int, net_name: str, chat_id: int, count: int = 1) -> bool:
        """Выдать пользователю указанную сеть (глобально).
        Если запись уже есть — увеличиваем `uses_left`, иначе создаём запись.
        """
        net = self.get_net(net_name)
        if not net:
            return False

        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT uses_left FROM player_nets
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND net_name = ?
            ''', (user_id, net_name))
            row = cursor.fetchone()
            if row:
                current = row[0]
                if current == -1:
                    # Уже бесконечная сеть
                    return True
                # Увеличиваем на count * max_uses (если max_uses == -1 — делаем -1)
                if net.get('max_uses', -1) == -1:
                    new = -1
                else:
                    new = current + int(count) * int(net.get('max_uses', 1))
                cursor.execute('''
                    UPDATE player_nets SET uses_left = ?
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND net_name = ?
                ''', (new, user_id, net_name))
            else:
                if net.get('max_uses', -1) == -1:
                    uses = -1
                else:
                    uses = int(count) * int(net.get('max_uses', 1))
                cursor.execute('''
                    INSERT OR REPLACE INTO player_nets (user_id, net_name, uses_left, chat_id)
                    VALUES (?, ?, ?, -1)
                ''', (user_id, net_name, uses))
            conn.commit()
            return True

    def grant_rod(self, user_id: int, rod_name: str, chat_id: int) -> bool:
        """Выдать пользователю удочку (глобально). Если уже есть — восстанавливаем до полной прочности."""
        rod = self.get_rod(rod_name)
        if not rod:
            return False

        with self._connect() as conn:
            cursor = conn.cursor()
            # Проверяем наличие глобальной записи
            cursor.execute('''
                SELECT 1 FROM player_rods
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
            ''', (user_id, rod_name))
            if cursor.fetchone():
                # If this is a temporary rod (uses range), initialize uses accordingly
                uses = self._get_temp_rod_uses(rod_name)
                if uses is None:
                    max_dur = rod.get('max_durability', rod.get('durability', 0))
                    current = max_dur
                else:
                    max_dur = uses
                    current = uses

                cursor.execute('''
                    UPDATE player_rods
                    SET current_durability = ?, max_durability = ?
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND rod_name = ?
                ''', (current, max_dur, user_id, rod_name))
            else:
                uses = self._get_temp_rod_uses(rod_name)
                if uses is None:
                    max_dur = rod.get('max_durability', rod.get('durability', 0))
                    current = max_dur
                else:
                    max_dur = uses
                    current = uses

                cursor.execute('''
                    INSERT OR REPLACE INTO player_rods (user_id, rod_name, current_durability, max_durability, chat_id)
                    VALUES (?, ?, ?, ?, -1)
                ''', (user_id, rod_name, current, max_dur))
            conn.commit()
            return True
    
    def buy_net(self, user_id: int, net_name: str, chat_id: int) -> bool:
        """Купить сеть в конкретном чате"""
        net = self.get_net(net_name)
        if not net:
            return False
        
        player = self.get_player(user_id, chat_id)
        if not player or player['coins'] < net['price']:
            return False
        
        # Проверяем, есть ли уже эта сеть у игрока
        player_net = self.get_player_net(user_id, net_name, chat_id)
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            if player_net:
                # Если сеть уже есть, добавляем использования
                if net['max_uses'] == -1:
                    # Бесконечная сеть - не добавляем
                    return False
                cursor.execute('''
                    UPDATE player_nets
                    SET uses_left = uses_left + ?
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND net_name = ?
                ''', (net['max_uses'], user_id, net_name))
            else:
                # Создаем новую сеть
                # Insert as a GLOBAL player_net (chat_id = -1)
                cursor.execute('''
                    INSERT INTO player_nets (user_id, net_name, uses_left, chat_id)
                    VALUES (?, ?, ?, -1)
                ''', (user_id, net_name, net['max_uses']))
            
            # Списываем монеты
            cursor.execute('''
                UPDATE players
                SET coins = coins - ?
                WHERE user_id = ?
            ''', (net['price'], user_id))
            
            conn.commit()
            return True
    
    def use_net(self, user_id: int, net_name: str, chat_id: int) -> bool:
        """Использовать сеть (уменьшить количество использований) в конкретном чате"""
        player_net = self.get_player_net(user_id, net_name, chat_id)
        if not player_net:
            return False
        
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Обновляем ГЛОБАЛЬНОЕ время последнего использования ЛЮБОЙ сети
            cursor.execute('''
                UPDATE players
                SET last_net_use_time = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (user_id,))
            
            # Обновляем время последнего использования конкретной сети (для архива)
            cursor.execute('''
                UPDATE player_nets
                SET last_use_time = CURRENT_TIMESTAMP
                WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND net_name = ?
            ''', (user_id, net_name))
            
            # Уменьшаем количество использований (только если не бесконечная)
            if player_net['max_uses'] != -1:
                cursor.execute('''
                    UPDATE player_nets
                    SET uses_left = uses_left - 1
                    WHERE user_id = ? AND (chat_id IS NULL OR chat_id < 1) AND net_name = ?
                ''', (user_id, net_name))
            
            conn.commit()
            return True
    
    def get_net_cooldown_remaining(self, user_id: int, net_name: str, chat_id: int) -> int:
        """Получить оставшееся время кулдауна для ЛЮБОЙ сети (глобальный кулдаун) в чате"""
        # Получаем информацию о сети для получения её кулдауна
        net = self.get_net(net_name)
        if not net:
            return 0
        
        # Получаем глобальное время последнего использования ЛЮБОЙ сети
        player = self.get_player(user_id, chat_id)
        if not player or not player['last_net_use_time']:
            return 0
        
        # Use timezone-aware UTC datetimes to avoid comparing naive and aware datetimes
        from datetime import datetime, timedelta, timezone
        try:
            last_use = datetime.fromisoformat(player['last_net_use_time'])
        except Exception:
            return 0

        # Treat stored naive timestamps as UTC
        if last_use.tzinfo is None:
            last_use = last_use.replace(tzinfo=timezone.utc)

        cooldown_hours = net['cooldown_hours']  # Используем кулдаун ЭТОЙ сети
        cooldown_end = last_use + timedelta(hours=cooldown_hours)

        now = datetime.now(timezone.utc)
        if now >= cooldown_end:
            return 0

        remaining = (cooldown_end - now).total_seconds()
        return int(remaining)

    def reset_net_cooldowns(self, user_id: int) -> None:
        """Сбросить кулдаун всех сетей игрока (обнулить время последнего использования)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE players SET last_net_use_time = NULL WHERE user_id = %s',
                (user_id,)
            )
            cursor.execute(
                'UPDATE player_nets SET last_use_time = NULL WHERE user_id = %s',
                (user_id,)
            )
            conn.commit()

    def mark_harpoon_used(self, user_id: int, chat_id: int) -> None:
        """Сохранить время последнего использования гарпуна."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                now_iso = datetime.utcnow().isoformat()
                # Пишем метку в запись гарпуна в player_rods.
                cursor.execute(
                    '''
                    UPDATE player_rods
                    SET last_repair_time = ?
                    WHERE user_id = ?
                      AND (chat_id = ? OR chat_id IS NULL OR chat_id < 1)
                      AND rod_name = 'Гарпун'
                    ''',
                    (now_iso, user_id, chat_id),
                )
                conn.commit()
        except Exception:
            logger.exception("mark_harpoon_used failed user=%s chat=%s", user_id, chat_id)

    def get_harpoon_cooldown_remaining(self, user_id: int, chat_id: int, cooldown_minutes: int) -> int:
        """Вернуть оставшееся время КД гарпуна в секундах (0 — гарпун готов)."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT last_repair_time
                    FROM player_rods
                    WHERE user_id = ?
                      AND (chat_id = ? OR chat_id IS NULL OR chat_id < 1)
                      AND rod_name = 'Гарпун'
                    ORDER BY CASE WHEN chat_id = ? THEN 0 ELSE 1 END
                    LIMIT 1
                    ''',
                    (user_id, chat_id, chat_id),
                )
                row = cursor.fetchone()
                if not row or not row[0]:
                    return 0

                last_used = datetime.fromisoformat(str(row[0]))
                end_time = last_used + timedelta(minutes=int(cooldown_minutes))
                remaining = (end_time - datetime.utcnow()).total_seconds()
                return max(0, int(remaining))
        except Exception:
            logger.exception("get_harpoon_cooldown_remaining failed user=%s chat=%s", user_id, chat_id)
            return 0

    def get_dynamite_cooldown_remaining(self, user_id: int, chat_id: int, cooldown_hours: int = 8) -> int:
        """Получить оставшееся время КД динамита в секундах."""
        player = self.get_player(user_id, chat_id)
        if not player:
            return 0

        last_use_raw = player.get('last_dynamite_use_time')
        if not last_use_raw:
            return 0

        from datetime import datetime, timedelta, timezone
        try:
            last_use = datetime.fromisoformat(str(last_use_raw))
        except Exception:
            return 0

        if last_use.tzinfo is None:
            last_use = last_use.replace(tzinfo=timezone.utc)

        cooldown_end = last_use + timedelta(hours=cooldown_hours)
        now = datetime.now(timezone.utc)
        if now >= cooldown_end:
            return 0
        return int((cooldown_end - now).total_seconds())

    def reset_dynamite_cooldown(self, user_id: int) -> None:
        """Сбросить КД динамита игрока."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE players SET last_dynamite_use_time = NULL WHERE user_id = %s',
                (user_id,)
            )
            conn.commit()

    def get_dynamite_ban_remaining(self, user_id: int, chat_id: int) -> int:
        """Оставшееся время ареста рыбохраной для динамита (в секундах)."""
        player = self.get_player(user_id, chat_id)
        if not player:
            return 0

        ban_until_raw = player.get('dynamite_ban_until')
        if not ban_until_raw:
            return 0

        from datetime import datetime, timezone
        try:
            ban_until = datetime.fromisoformat(str(ban_until_raw))
        except Exception:
            return 0

        if ban_until.tzinfo is None:
            ban_until = ban_until.replace(tzinfo=timezone.utc)

        now = datetime.now(timezone.utc)
        if now >= ban_until:
            # Авто-снятие просроченного ареста
            try:
                self.update_player(user_id, chat_id, dynamite_ban_until=None)
            except Exception:
                pass
            return 0

        return int((ban_until - now).total_seconds())

    def update_dynamite_state(self, user_id: int, current_location: str) -> tuple:
        """Update dynamite usage state for the player and return
        (location_changed, consecutive_explosions, dynamite_penalty, recovery_explosions).
        Rules:
        - If last use >60 minutes -> reset counters.
        - If changed location -> set consecutive=1 and start recovery (1 explosion to clear penalty).
        - If remained on same location -> increment consecutive; when consecutive >=3 set a 5% penalty,
          for >=4 set 10% penalty. Recovery on location change clears penalty after one explosion there.
        """
        from datetime import datetime, timedelta
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT consecutive_dynamite_at_location, last_dynamite_location, dynamite_penalty, last_dynamite_use_time, dynamite_recovery_explosions
                FROM players
                WHERE user_id = %s AND chat_id = -1
            ''', (user_id,))
            row = cursor.fetchone()

            if not row:
                location_changed = True
                consecutive = 1
                dynamite_penalty = 0.0
                recovery = 0
            else:
                last_consecutive, last_location, dynamite_penalty, last_use_time, recovery = row
                last_consecutive = int(last_consecutive or 0)
                dynamite_penalty = float(dynamite_penalty or 0.0)
                recovery = int(recovery or 0)

                # Idle timer: 60+ minutes resets counters
                if last_use_time:
                    try:
                        last_dt = datetime.fromisoformat(str(last_use_time))
                        now_dt = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
                        if now_dt - last_dt >= timedelta(minutes=60):
                            last_consecutive = 0
                            dynamite_penalty = 0.0
                            recovery = 0
                    except Exception:
                        pass

                location_changed = (last_location != current_location)

                if location_changed:
                    # При переходе на новую локацию — первый взрыв должен снять штраф динамита.
                    consecutive = 1
                    if dynamite_penalty and float(dynamite_penalty) > 0:
                        dynamite_penalty = 0.0
                        recovery = 0
                    else:
                        recovery = 0
                else:
                    consecutive = last_consecutive + 1

                    if recovery > 0 and dynamite_penalty > 0:
                        # After one explosion on new location, clear penalty
                        recovery += 1
                        if recovery >= 1:
                            dynamite_penalty = 0.0
                            recovery = 0

                    if recovery == 0:
                        if consecutive >= 4:
                            dynamite_penalty = 10.0
                        elif consecutive >= 3:
                            dynamite_penalty = 5.0
                        else:
                            dynamite_penalty = 0.0

            # persist new state and update last_dynamite_use_time
            now_iso = datetime.now().isoformat()
            cursor.execute('''
                UPDATE players
                SET consecutive_dynamite_at_location = %s,
                    last_dynamite_location = %s,
                    dynamite_penalty = %s,
                    dynamite_recovery_explosions = %s,
                    last_dynamite_use_time = %s
                WHERE user_id = %s
            ''', (consecutive, current_location, dynamite_penalty, recovery, now_iso, user_id))
            conn.commit()

            return (location_changed, consecutive, dynamite_penalty, recovery)

    def get_dynamite_penalty(self, user_id: int) -> float:
        """Return current dynamite penalty percentage for a user."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT dynamite_penalty
                FROM players
                WHERE user_id = %s AND chat_id = -1
            ''', (user_id,))
            row = cursor.fetchone()
            return float(row[0]) if (row and row[0]) else 0.0

    def set_dynamite_ban(self, user_id: int, chat_id: int, hours: int = 24) -> None:
        """Установить арест рыбохраной для динамита."""
        from datetime import datetime, timedelta
        ban_until = (datetime.now() + timedelta(hours=hours)).isoformat()
        self.update_player(user_id, chat_id, dynamite_ban_until=ban_until)

    def clear_dynamite_ban(self, user_id: int, chat_id: int) -> None:
        """Снять арест рыбохраны для динамита."""
        self.update_player(user_id, chat_id, dynamite_ban_until=None)

    # ===== РЕФЕРАЛЬНАЯ СИСТЕМА =====
    
    def set_player_ref(self, user_id: int, chat_id: int, ref_user_id: int) -> bool:
        """Установить реферера для пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players
                SET ref = ?
                WHERE user_id = ?
            ''', (ref_user_id, user_id))
            conn.commit()
            return True
    
    def get_player_ref(self, user_id: int, chat_id: int) -> Optional[int]:
        """Получить реферера пользователя"""
        player = self.get_player(user_id, chat_id)
        if player:
            return player.get('ref')
        return None
    
    def set_ref_link(self, user_id: int, chat_id: int, ref_link: str) -> bool:
        """Сохранить реф ссылку для пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE players
                SET ref_link = ?
                WHERE user_id = ?
            ''', (ref_link, user_id))
            conn.commit()
            return True
    
    def get_ref_link(self, user_id: int, chat_id: int) -> Optional[str]:
        """Получить реф ссылку пользователя"""
        player = self.get_player(user_id, chat_id)
        if player:
            return player.get('ref_link')
        return None
    
    def configure_chat(self, chat_id: int, admin_user_id: int) -> bool:
        """Настроить чат для реферальной системы"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO chat_configs (chat_id, admin_user_id, is_configured)
                VALUES (?, ?, 1)
            ''', (chat_id, admin_user_id))
            conn.commit()
            return True
    
    def is_chat_configured(self, chat_id: int) -> bool:
        """Проверить, настроен ли чат"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 1 FROM chat_configs 
                WHERE chat_id = ? AND is_configured = 1
            ''', (chat_id,))
            return cursor.fetchone() is not None
    
    def get_chat_admin(self, chat_id: int) -> Optional[int]:
        """Получить админа, настроившего чат"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_user_id FROM chat_configs 
                WHERE chat_id = ? AND is_configured = 1
            ''', (chat_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_user_ref_link(self, user_id: int, ref_link: str) -> bool:
        """Сохранить реф-ссылку пользователя (Telegram Affiliate)"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_ref_links (user_id, ref_link, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, ref_link))
            conn.commit()
            return True
    
    def get_user_ref_link(self, user_id: int) -> Optional[str]:
        """Получить сохранённую реф-ссылку пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ref_link FROM user_ref_links WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_user_chat_link(self, user_id: int, chat_invite_link: str) -> bool:
        """Сохранить ссылку на чат пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_ref_links
                SET chat_invite_link = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (chat_invite_link, user_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_user_chat_link(self, user_id: int) -> Optional[str]:
        """Получить сохранённую ссылку на чат пользователя"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chat_invite_link FROM user_ref_links WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_chat_ref_link(self, chat_id: int, ref_link: str, chat_invite_link: str = None) -> bool:
        """Установить реф-ссылку администратора для чата"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE chat_configs 
                SET admin_ref_link = ?, chat_invite_link = ?
                WHERE chat_id = ?
            ''', (ref_link, chat_invite_link, chat_id))
            conn.commit()
            return cursor.rowcount > 0
    
    def get_chat_ref_link(self, chat_id: int) -> Optional[str]:
        """Получить реф-ссылку для чата"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT admin_ref_link FROM chat_configs 
                WHERE chat_id = ? AND is_configured = 1
            ''', (chat_id,))
            row = cursor.fetchone()
            return row[0] if row else None
    
    def get_user_registered_chats(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить все чаты, зарегистрированные этим юзером"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT chat_id, admin_ref_link, chat_invite_link
                FROM chat_configs 
                WHERE admin_user_id = %s AND is_configured = 1
            ''', (user_id,))
            rows = cursor.fetchall()
            cols = [d[0] for d in cursor.description] if cursor.description else []
            return [dict(zip(cols, row)) for row in rows]

    def add_ref_access(self, user_id: int, chat_id: int) -> bool:
        """Выдать пользователю доступ к статистике указанного чата."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT OR IGNORE INTO ref_access (user_id, chat_id)
                    VALUES (?, ?)
                    ''',
                    (int(user_id), int(chat_id)),
                )
                conn.commit()
                return True
        except Exception:
            logger.exception("add_ref_access failed user=%s chat=%s", user_id, chat_id)
            return False

    def get_ref_access_chats(self, user_id: int) -> List[int]:
        """Список chat_id, к которым у пользователя есть реф-доступ."""
        result: List[int] = []
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT chat_id FROM ref_access WHERE user_id = ? ORDER BY chat_id', (int(user_id),))
                result.extend(int(row[0]) for row in cursor.fetchall() if row and row[0] is not None)

                # Владелец чата (admin_user_id) автоматически имеет доступ к своему чату.
                cursor.execute(
                    '''
                    SELECT chat_id
                    FROM chat_configs
                    WHERE admin_user_id = ? AND COALESCE(is_configured, 1) = 1
                    ''',
                    (int(user_id),),
                )
                result.extend(int(row[0]) for row in cursor.fetchall() if row and row[0] is not None)

            # Deduplicate while preserving order
            seen = set()
            ordered = []
            for chat_id in result:
                if chat_id in seen:
                    continue
                seen.add(chat_id)
                ordered.append(chat_id)
            return ordered
        except Exception:
            logger.exception("get_ref_access_chats failed user=%s", user_id)
            return []

    def get_chat_title(self, chat_id: int) -> Optional[str]:
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT chat_title FROM chat_configs WHERE chat_id = ? LIMIT 1', (int(chat_id),))
                row = cursor.fetchone()
                return row[0] if row and row[0] else None
        except Exception:
            logger.exception("get_chat_title failed chat=%s", chat_id)
            return None

    def get_chat_stars_total(self, chat_id: int, min_age_days: Optional[int] = None) -> int:
        """Сумма stars по чату из star_transactions (без рефандов)."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                if min_age_days is not None and int(min_age_days) > 0:
                    cutoff = datetime.utcnow() - timedelta(days=int(min_age_days))
                    cursor.execute(
                        '''
                        SELECT COALESCE(SUM(total_amount), 0)
                        FROM star_transactions
                        WHERE chat_id = ?
                          AND COALESCE(refund_status, 'none') = 'none'
                          AND created_at <= ?
                        ''',
                        (int(chat_id), cutoff.strftime('%Y-%m-%d %H:%M:%S')),
                    )
                else:
                    cursor.execute(
                        '''
                        SELECT COALESCE(SUM(total_amount), 0)
                        FROM star_transactions
                        WHERE chat_id = ?
                          AND COALESCE(refund_status, 'none') = 'none'
                        ''',
                        (int(chat_id),),
                    )
                row = cursor.fetchone()
                return int(row[0] or 0) if row else 0
        except Exception:
            logger.exception("get_chat_stars_total failed chat=%s min_age_days=%s", chat_id, min_age_days)
            return 0

    def get_chat_refunds_total(self, chat_id: int) -> int:
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    SELECT COALESCE(SUM(total_amount), 0)
                    FROM star_transactions
                    WHERE chat_id = ?
                      AND COALESCE(refund_status, 'none') != 'none'
                    ''',
                    (int(chat_id),),
                )
                row = cursor.fetchone()
                return int(row[0] or 0) if row else 0
        except Exception:
            logger.exception("get_chat_refunds_total failed chat=%s", chat_id)
            return 0

    def get_withdrawn_stars(self, user_id: int, chat_id: Optional[int] = None) -> int:
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                if chat_id is None:
                    cursor.execute(
                        'SELECT COALESCE(SUM(amount), 0) FROM star_withdrawals WHERE user_id = ?',
                        (int(user_id),),
                    )
                else:
                    cursor.execute(
                        'SELECT COALESCE(SUM(amount), 0) FROM star_withdrawals WHERE user_id = ? AND chat_id = ?',
                        (int(user_id), int(chat_id)),
                    )
                row = cursor.fetchone()
                return int(row[0] or 0) if row else 0
        except Exception:
            logger.exception("get_withdrawn_stars failed user=%s chat=%s", user_id, chat_id)
            return 0

    def mark_stars_withdrawn(self, user_id: int, amount: int, chat_id: Optional[int] = None) -> bool:
        """Зафиксировать одобренный вывод звёзд."""
        amt = int(amount or 0)
        if amt <= 0:
            return False
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    '''
                    INSERT INTO star_withdrawals (user_id, chat_id, amount)
                    VALUES (?, ?, ?)
                    ''',
                    (int(user_id), int(chat_id) if chat_id is not None else None, amt),
                )
                conn.commit()
                return True
        except Exception:
            logger.exception("mark_stars_withdrawn failed user=%s amount=%s chat=%s", user_id, amount, chat_id)
            return False

    def get_available_stars_for_withdraw(self, user_id: int, chat_id: int) -> int:
        """Доступно к выводу = 50% от (85% stars старше 21 дня) минус уже выведенное."""
        matured = self.get_chat_stars_total(chat_id, min_age_days=21)
        gross = int((float(matured) * 0.85) / 2)
        withdrawn = self.get_withdrawn_stars(user_id, chat_id)
        return max(0, gross - withdrawn)

    def update_population_state(self, user_id: int, current_location: str) -> tuple:
        """
        Обновить состояние популяции рыб на локации.
        Отслеживает, сколько раз подряд игрок ловит на одной локации.
        Логика снятия штрафа:
        - если не ловить 60+ минут, штраф сбрасывается;
        - при смене локации штраф не снимается сразу: нужно 10 забросов на новой локации.
        Возвращает (location_changed, consecutive_casts, show_warning)
        """
        with self._connect() as conn:
            cursor = conn.cursor()
            
            # Получаем текущее состояние игрока
            cursor.execute('''
                SELECT consecutive_casts_at_location, last_fishing_location, population_penalty,
                       last_fish_time, penalty_recovery_casts, last_population_action_time
                FROM players
                WHERE user_id = %s AND chat_id = -1
            ''', (user_id,))
            row = cursor.fetchone()
            
            if not row:
                # Новый игрок
                location_changed = True
                consecutive_casts = 1
                population_penalty = 0.0
                recovery_casts = 0
            else:
                last_casts, last_location, population_penalty, last_fish_time, recovery_casts, last_population_action_time = row
                last_casts = last_casts or 0
                population_penalty = population_penalty or 0.0
                recovery_casts = recovery_casts or 0

                # Таймер простоя: 60+ минут без ловли полностью снимает штраф и серию.
                activity_time_raw = last_population_action_time or last_fish_time
                if activity_time_raw:
                    try:
                        last_dt = datetime.fromisoformat(str(activity_time_raw))
                        now_dt = datetime.now(last_dt.tzinfo) if last_dt.tzinfo else datetime.now()
                        if now_dt - last_dt >= timedelta(minutes=60):
                            last_casts = 0
                            population_penalty = 0.0
                            recovery_casts = 0
                    except Exception:
                        # Если время в нестандартном формате, продолжаем без таймера простоя.
                        pass
                
                # Проверяем, изменилась ли локация
                location_changed = (last_location != current_location)
                
                if location_changed:
                    # Игрок переместился на новую локацию.
                    # Если есть штраф - он переносится, и снимается только после 10 забросов на новой локации.
                    consecutive_casts = 1
                    recovery_casts = 1 if population_penalty > 0 else 0
                else:
                    # Остался на той же локации
                    consecutive_casts = last_casts + 1

                    # Режим восстановления штрафа после смены локации.
                    if recovery_casts > 0 and population_penalty > 0:
                        recovery_casts += 1
                        if recovery_casts >= 10:
                            population_penalty = 0.0
                            recovery_casts = 0

                    # Обычная шкала штрафов действует, только когда нет восстановления.
                    if recovery_casts == 0:
                        if consecutive_casts >= 60:
                            population_penalty = 15.0
                        elif consecutive_casts >= 50:
                            population_penalty = 11.0
                        elif consecutive_casts >= 40:
                            population_penalty = 8.0
                        elif consecutive_casts >= 30:
                            population_penalty = 5.0
                        else:
                            population_penalty = 0.0
            
            # Обновляем состояние в базе
            now_iso = datetime.now().isoformat()
            cursor.execute('''
                UPDATE players
                SET consecutive_casts_at_location = %s,
                    last_fishing_location = %s,
                    population_penalty = %s,
                    penalty_recovery_casts = %s,
                    last_population_action_time = %s
                WHERE user_id = %s AND chat_id = -1
            ''', (consecutive_casts, current_location, population_penalty, recovery_casts, now_iso, user_id))
            conn.commit()
            
            # show_warning если достигли 30 забросов
            show_warning = (consecutive_casts == 30 and not location_changed)
            
            return (location_changed, consecutive_casts, show_warning)
    
    def get_consecutive_casts(self, user_id: int) -> int:
        """Получить количество консекутивных забросов на текущей локации"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT consecutive_casts_at_location
                FROM players
                WHERE user_id = %s AND chat_id = -1
            ''', (user_id,))
            row = cursor.fetchone()
            return row[0] if (row and row[0]) else 0
    
    def get_population_penalty(self, user_id: int) -> float:
        """Получить текущий штраф на популяцию рыб для игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT population_penalty
                FROM players
                WHERE user_id = %s AND chat_id = -1
            ''', (user_id,))
            row = cursor.fetchone()
            return row[0] if (row and row[0]) else 0.0

    def add_treasure(self, user_id: int, treasure_name: str, quantity: int = 1, chat_id: int = -1) -> bool:
        """Добавить сокровище игроку. Возвращает True при успешной записи."""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                logger.info(
                    "Treasure write start user_id=%s chat_id=%s treasure=%s delta_qty=%s",
                    user_id,
                    chat_id,
                    treasure_name,
                    quantity,
                )
                cursor.execute('''
                    INSERT INTO player_treasures (user_id, chat_id, treasure_name, quantity)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (user_id, chat_id, treasure_name) DO UPDATE
                    SET quantity = player_treasures.quantity + %s
                ''', (user_id, chat_id, treasure_name, quantity, quantity))
                conn.commit()
                cursor.execute('''
                    SELECT quantity
                    FROM player_treasures
                    WHERE user_id = %s AND chat_id = %s AND treasure_name = %s
                ''', (user_id, chat_id, treasure_name))
                row = cursor.fetchone()
                if row:
                    logger.info(
                        "Treasure write confirmed user_id=%s chat_id=%s treasure=%s stored_qty=%s",
                        user_id,
                        chat_id,
                        treasure_name,
                        int(row[0] or 0),
                    )
                    return True

                logger.error(
                    "Treasure write missing after commit user_id=%s chat_id=%s treasure=%s",
                    user_id,
                    chat_id,
                    treasure_name,
                )
                return False
            except Exception as e:
                logger.exception(
                    "Error adding treasure user_id=%s chat_id=%s treasure=%s qty=%s",
                    user_id,
                    chat_id,
                    treasure_name,
                    quantity,
                )
                try:
                    conn.rollback()
                except Exception:
                    pass

                # Self-heal: if table was missing in a stale database, create and retry once.
                try:
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS player_treasures (
                            id INTEGER PRIMARY KEY,
                            user_id BIGINT NOT NULL,
                            chat_id BIGINT DEFAULT -1,
                            treasure_name TEXT NOT NULL,
                            quantity INTEGER DEFAULT 1,
                            obtained_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(user_id, chat_id, treasure_name)
                        )
                    ''')
                    cursor.execute('''
                        INSERT INTO player_treasures (user_id, chat_id, treasure_name, quantity)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (user_id, chat_id, treasure_name) DO UPDATE
                        SET quantity = player_treasures.quantity + %s
                    ''', (user_id, chat_id, treasure_name, quantity, quantity))
                    conn.commit()
                    cursor.execute('''
                        SELECT quantity
                        FROM player_treasures
                        WHERE user_id = %s AND chat_id = %s AND treasure_name = %s
                    ''', (user_id, chat_id, treasure_name))
                    row = cursor.fetchone()
                    if not row:
                        logger.error(
                            "Treasure retry write missing after commit user_id=%s chat_id=%s treasure=%s",
                            user_id,
                            chat_id,
                            treasure_name,
                        )
                        return False
                    logger.warning(
                        "Recovered treasure insert after auto-ensuring table: user_id=%s chat_id=%s treasure=%s stored_qty=%s",
                        user_id,
                        chat_id,
                        treasure_name,
                        int(row[0] or 0),
                    )
                    return True
                except Exception:
                    logger.exception(
                        "Retry add_treasure failed user_id=%s chat_id=%s treasure=%s qty=%s",
                        user_id,
                        chat_id,
                        treasure_name,
                        quantity,
                    )
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    return False

    def get_player_treasures(self, user_id: int, chat_id: int) -> List[Dict[str, Any]]:
        """Получить все сокровища игрока"""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT treasure_name, quantity, obtained_at
                    FROM player_treasures
                    WHERE user_id = %s AND chat_id = %s AND quantity > 0
                    ORDER BY obtained_at DESC
                ''', (user_id, chat_id))
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                return [dict(zip(cols, row)) for row in rows]
            except Exception as e:
                logger.error(f"Error getting player treasures: {e}")
                return []

    def get_player_treasures_all_chats(self, user_id: int) -> List[Dict[str, Any]]:
        """Получить все сокровища игрока по всем чатам"""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    SELECT chat_id, treasure_name, quantity, obtained_at
                    FROM player_treasures
                    WHERE user_id = %s AND quantity > 0
                    ORDER BY obtained_at DESC
                ''', (user_id,))
                rows = cursor.fetchall()
                cols = [d[0] for d in cursor.description] if cursor.description else []
                return [dict(zip(cols, row)) for row in rows]
            except Exception as e:
                logger.error(f"Error getting player treasures across chats: {e}")
                return []

    def remove_treasure(self, user_id: int, chat_id: int, treasure_name: str, quantity: int = 1, reason: str = 'SOLD'):
        """Удалить сокровище у игрока (уменьшает quantity до 0 минимум)."""
        with self._connect() as conn:
            cursor = conn.cursor()
            try:
                logger.info(
                    "Treasure remove start user_id=%s chat_id=%s treasure=%s delta_qty=%s reason=%s",
                    user_id,
                    chat_id,
                    treasure_name,
                    quantity,
                    reason,
                )
                cursor.execute('''
                    UPDATE player_treasures
                    SET quantity = CASE WHEN quantity - %s > 0 THEN quantity - %s ELSE 0 END
                    WHERE user_id = %s AND chat_id = %s AND treasure_name = %s
                ''', (quantity, quantity, user_id, chat_id, treasure_name))
                conn.commit()

                cursor.execute('''
                    SELECT quantity
                    FROM player_treasures
                    WHERE user_id = %s AND chat_id = %s AND treasure_name = %s
                ''', (user_id, chat_id, treasure_name))
                row = cursor.fetchone()
                if row:
                    logger.info(
                        "Treasure remove confirmed user_id=%s chat_id=%s treasure=%s stored_qty=%s reason=%s",
                        user_id,
                        chat_id,
                        treasure_name,
                        int(row[0] or 0),
                        reason,
                    )
                else:
                    logger.warning(
                        "Treasure remove row missing user_id=%s chat_id=%s treasure=%s",
                        user_id,
                        chat_id,
                        treasure_name,
                    )
            except Exception as e:
                logger.error(f"Error removing treasure: {e}")
                conn.rollback()


# Экземпляр базы данных для импорта в других модулях
db = Database()
