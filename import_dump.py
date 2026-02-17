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
        retry_queue = []
        for i, stmt in enumerate(iter_statements(DUMP), 1):
            if not should_execute(stmt):
                continue
            try:
                cur.execute(stmt)
            except Exception as e:
                pgcode = getattr(e, 'pgcode', None)
                if pgcode == '23505':
                    print(f"WARNING duplicate on statement #{i}: {e}")
                    continue
                if pgcode == '23503':
                    # foreign key violation - try to create placeholder in players, then retry
                    print(f"DEFERRED FK on statement #{i}: {e}")
                    try:
                        # try to extract user_id from INSERT statement
                        m = re.search(r"INSERT\s+INTO\s+\"?([^\(\s\"]+)\"?\s*\(([^)]+)\)\s*VALUES\s*\((.+)\)", stmt, re.IGNORECASE | re.DOTALL)
                        if m:
                            cols = [c.strip().strip('"') for c in m.group(2).split(',')]
                            vals_raw = m.group(3).strip()
                            # split top-level commas in values (ignore commas inside single quotes)
                            vals = []
                            cur_val = []
                            in_sq = False
                            i_ch = 0
                            while i_ch < len(vals_raw):
                                ch = vals_raw[i_ch]
                                if ch == "'":
                                    # handle escaped single quotes by skipping next if doubled
                                    if in_sq and i_ch + 1 < len(vals_raw) and vals_raw[i_ch+1] == "'":
                                        cur_val.append("''")
                                        i_ch += 2
                                        continue
                                    in_sq = not in_sq
                                    cur_val.append(ch)
                                elif ch == ',' and not in_sq:
                                    vals.append(''.join(cur_val).strip())
                                    cur_val = []
                                else:
                                    cur_val.append(ch)
                                i_ch += 1
                            if cur_val:
                                vals.append(''.join(cur_val).strip())
                            if 'user_id' in cols:
                                idx = cols.index('user_id')
                                raw_val = vals[idx]
                                # strip quotes
                                uid = raw_val.strip().strip("'")
                                try:
                                    uid_int = int(uid)
                                    # insert placeholder player
                                    try:
                                        cur.execute("INSERT INTO players (user_id, chat_id, username, created_at) VALUES (%s, %s, %s, now()) ON CONFLICT DO NOTHING", (uid_int, -1, f"imported_{uid_int}"))
                                        # try original statement again
                                        try:
                                            cur.execute(stmt)
                                            continue
                                        except Exception:
                                            pass
                                    except Exception:
                                        pass
                                except Exception:
                                    pass
                    except Exception:
                        pass
                    # if still failing, defer and retry later
                    retry_queue.append((i, stmt))
                    continue
                print(f"ERROR on statement #{i}: {e}")
                print("Failed SQL (truncated):", stmt[:1000])
                conn.close()
                sys.exit(1)

        # Retry deferred FK statements a few times (in case referenced rows are inserted later)
        if retry_queue:
            max_passes = 5
            for attempt in range(1, max_passes + 1):
                if not retry_queue:
                    break
                print(f"Retry pass {attempt} for {len(retry_queue)} deferred statements")
                new_queue = []
                for i, stmt in retry_queue:
                    try:
                        cur.execute(stmt)
                    except Exception as e:
                        pgcode = getattr(e, 'pgcode', None)
                        if pgcode == '23505':
                            print(f"WARNING duplicate on retried statement #{i}: {e}")
                            continue
                        if pgcode == '23503':
                            new_queue.append((i, stmt))
                            continue
                        print(f"ERROR on retried statement #{i}: {e}")
                        print("Failed SQL (truncated):", stmt[:1000])
                        conn.close()
                        sys.exit(1)
                retry_queue = new_queue
            if retry_queue:
                print(f"WARNING: {len(retry_queue)} statements still failed with FK after retries. They will be skipped.")
        print("Импорт INSERT/COPY завершён")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    main()