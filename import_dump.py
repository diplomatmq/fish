# import_only_data.py
import os
import psycopg2
import sys
import re

# Prefer DATABASE_URL from environment (use the public proxy URL from Railway)
DSN = os.getenv('DATABASE_URL', "postgresql://postgres:ipbLFJFEodFfVgmDWEgEzshxuddpEmZs@postgres.railway.internal:5432/railway")
DUMP = "dump.sql"

def should_execute(stmt: str) -> bool:
    s = stmt.strip().upper()
    return s.startswith("INSERT INTO") or s.startswith("COPY ")

def iter_statements(path):
    buf = []
    in_copy = False
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if in_copy:
                buf.append(line)
                if line.strip() == "\\.":
                    yield "".join(buf)
                    buf = []
                    in_copy = False
                continue
            if line.strip().upper().startswith("COPY "):
                in_copy = True
                buf.append(line)
                continue
            buf.append(line)
            if line.strip().endswith(";"):
                yield "".join(buf)
                buf = []
        if buf:
            yield "".join(buf)

def main():
    # Use SSL by default for external Railway proxy connections
    try:
        conn = psycopg2.connect(DSN, sslmode='require')
    except Exception as e:
        print("Connection failed:", e)
        sys.exit(1)
    conn.autocommit = True
    cur = conn.cursor()
    try:
        for i, stmt in enumerate(iter_statements(DUMP), 1):
            if should_execute(stmt):
                try:
                    cur.execute(stmt)
                except Exception as e:
                    # If row already exists (unique violation), skip and continue
                    pgcode = getattr(e, 'pgcode', None)
                    if pgcode == '23505':
                        print(f"WARNING duplicate on statement #{i}: {e}")
                        continue
                    print(f"ERROR on statement #{i}: {e}")
                    print("Failed SQL (truncated):", stmt[:1000])
                    conn.close()
                    sys.exit(1)
        print("Импорт INSERT/COPY завершён")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()