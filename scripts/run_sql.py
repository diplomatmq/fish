#!/usr/bin/env python3
"""
Run a SQL file against DATABASE_URL using psycopg2.
Usage:
  python3 scripts/run_sql.py scripts/pg_fix_indexes_and_sequences.sql

If DATABASE_URL is not set, provide full DSN as first arg.
"""
import os
import sys
import psycopg2


def main():
    if len(sys.argv) < 2:
        print("Usage: run_sql.py <sql-file> [DATABASE_URL]")
        sys.exit(2)
    sql_path = sys.argv[1]
    dsn = os.getenv('DATABASE_URL') if len(sys.argv) < 3 else sys.argv[2]
    if not dsn:
        print('DATABASE_URL not set and no DSN provided')
        sys.exit(2)

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    try:
        conn = psycopg2.connect(dsn)
    except Exception as e:
        print('Connection failed:', e)
        sys.exit(1)

    conn.autocommit = True
    cur = conn.cursor()
    try:
        cur.execute(sql)
        print('SQL executed successfully')
    except Exception as e:
        print('Execution failed:', e)
        # print a snippet of SQL to help debugging
        snippet = sql[:2000]
        print('SQL snippet (truncated):')
        print(snippet)
        sys.exit(1)
    finally:
        try:
            cur.close()
            conn.close()
        except Exception:
            pass


if __name__ == '__main__':
    main()
