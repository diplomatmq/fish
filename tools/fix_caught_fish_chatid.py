#!/usr/bin/env python3
"""Fix caught_fish.chat_id values and add trigger to enforce future writes.

Usage: python tools\fix_caught_fish_chatid.py

What it does:
- Creates a timestamped backup of the SQLite DB.
- Normalizes existing rows: if caught_fish.chat_id is NULL or <= 0, set it to the player's chat_id (MAX available) for that user.
- Creates an AFTER INSERT trigger to auto-fill chat_id for future inserts when chat_id is NULL/invalid.
"""
from pathlib import Path
import shutil
import datetime
import sys
import os

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from config import DB_PATH

# Optional Postgres support
try:
    import psycopg2
except Exception:
    psycopg2 = None


def backup_db(db_path: Path) -> Path:
    ts = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = db_path.with_name(db_path.name + f".backup-{ts}")
    print(f"Creating DB backup: {dest}")
    shutil.copy2(db_path, dest)
    return dest


def run_fix(db_path: Path):
    # If DATABASE_URL is provided, operate on Postgres via psycopg2
    database_url = os.getenv('DATABASE_URL')
    if database_url and psycopg2:
        conn = psycopg2.connect(database_url)
        cur = conn.cursor()
        print("Running Postgres normalization of caught_fish.chat_id...")
        try:
            # Normalize empty string chat_id to NULL
            try:
                cur.execute("UPDATE caught_fish SET chat_id = NULL WHERE chat_id = ''")
                conn.commit()
            except Exception:
                conn.rollback()

            update_sql = '''
            UPDATE caught_fish
            SET chat_id = (
                SELECT MAX(p.chat_id::bigint) FROM players p WHERE p.user_id = caught_fish.user_id AND p.chat_id IS NOT NULL AND (p.chat_id::text ~ '^[0-9]+$')
            )
            WHERE chat_id IS NULL OR (chat_id::text ~ '^[0-9]+$') = false OR chat_id::bigint < 1
            '''
            cur.execute(update_sql)
            updated = cur.rowcount
            conn.commit()
            print(f"Rows updated: {updated}")

            # Create trigger function + trigger (idempotent)
            print("Creating trigger/function caught_fish_fix_chatid_after_insert (Postgres)...")
            try:
                cur.execute("DROP TRIGGER IF EXISTS caught_fish_fix_chatid_after_insert ON caught_fish")
            except Exception:
                conn.rollback()
            try:
                cur.execute("DROP FUNCTION IF EXISTS fix_caught_fish_chatid() CASCADE")
            except Exception:
                conn.rollback()

            func_sql = '''
            CREATE FUNCTION fix_caught_fish_chatid() RETURNS trigger AS $$
            BEGIN
              IF NEW.chat_id IS NULL OR (NEW.chat_id::text ~ '^[0-9]+$') = false OR NEW.chat_id::bigint < 1 THEN
                UPDATE caught_fish SET chat_id = (
                  SELECT MAX(p.chat_id::bigint) FROM players p WHERE p.user_id = NEW.user_id AND p.chat_id IS NOT NULL AND (p.chat_id::text ~ '^[0-9]+$')
                ) WHERE id = NEW.id;
              END IF;
              RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            '''
            cur.execute(func_sql)
            cur.execute('CREATE TRIGGER caught_fish_fix_chatid_after_insert AFTER INSERT ON caught_fish FOR EACH ROW EXECUTE FUNCTION fix_caught_fish_chatid()')
            conn.commit()
        finally:
            try:
                cur.close()
            except Exception:
                pass
            try:
                conn.close()
            except Exception:
                pass
        return

    # Fallback to SQLite behavior (local DB file)
    import sqlite3
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    print("Normalizing empty/invalid chat_id values in caught_fish (SQLite)...")
    # Normalize empty string chat_id to NULL first
    try:
        cur.execute("UPDATE caught_fish SET chat_id = NULL WHERE chat_id = ''")
        conn.commit()
    except Exception:
        # ignore if table/column not present
        pass

    # Update rows where chat_id is NULL or <=0 using player's chat_id (max available)
    update_sql = '''
    UPDATE caught_fish
    SET chat_id = (
        SELECT MAX(p.chat_id) FROM players p WHERE p.user_id = caught_fish.user_id AND p.chat_id IS NOT NULL AND CAST(p.chat_id AS INTEGER) > 0
    )
    WHERE chat_id IS NULL OR CAST(chat_id AS INTEGER) < 1
    '''
    cur.execute(update_sql)
    updated = cur.rowcount
    conn.commit()
    print(f"Rows updated: {updated}")

    # Create AFTER INSERT trigger to fix future inserts that miss chat_id
    print("Creating trigger caught_fish_fix_chatid_after_insert (idempotent)...")
    try:
        cur.execute("DROP TRIGGER IF EXISTS caught_fish_fix_chatid_after_insert")
    except Exception:
        pass

    trigger_sql = '''
    CREATE TRIGGER caught_fish_fix_chatid_after_insert
    AFTER INSERT ON caught_fish
    FOR EACH ROW
    WHEN (NEW.chat_id IS NULL OR CAST(NEW.chat_id AS INTEGER) < 1)
    BEGIN
      UPDATE caught_fish
      SET chat_id = (
        SELECT MAX(p.chat_id) FROM players p WHERE p.user_id = NEW.user_id AND p.chat_id IS NOT NULL AND CAST(p.chat_id AS INTEGER) > 0
      )
      WHERE id = NEW.id;
    END;
    '''
    cur.execute(trigger_sql)
    conn.commit()

    # Reporting: show top chat_id buckets
    print("Top chat_id by total weight (sample):")
    try:
        cur.execute('''
            SELECT COALESCE(cf.chat_id,'(NULL)') AS chat_id, COUNT(*) AS cnt, COALESCE(SUM(cf.weight),0) AS total_w
            FROM caught_fish cf
            GROUP BY cf.chat_id
            ORDER BY total_w DESC
            LIMIT 20
        ''')
        rows = cur.fetchall()
        for r in rows:
            print(r)
    except Exception as e:
        print("Failed to query summary:", e)

    conn.close()


if __name__ == '__main__':
    dbp = Path(DB_PATH)
    if not dbp.exists():
        print('DB not found at', dbp)
        sys.exit(1)

    backup_db(dbp)
    run_fix(dbp)
