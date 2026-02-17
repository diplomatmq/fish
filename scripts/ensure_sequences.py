"""Run sequence/serial fixes against the DATABASE_URL Postgres instance.

Usage: python scripts/ensure_sequences.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from database import PostgresConnWrapper, ensure_all_serial_pks

def main():
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print('DATABASE_URL not set')
        return 1
    conn = PostgresConnWrapper(db_url)
    try:
        print('Running ensure_all_serial_pks...')
        ensure_all_serial_pks(conn)
        print('Done')
    except Exception as e:
        print('Error:', e)
        return 2
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
