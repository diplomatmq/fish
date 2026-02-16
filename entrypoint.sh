#!/bin/sh
set -e

# Persistent mount path inside container. Keep default but allow override.
TARGET_DIR=${FISHBOT_DB_PATH:-/data/fishbot.db}
TARGET_PATH=$(dirname "$TARGET_DIR")

# ensure target directory exists with sensible permissions
mkdir -p "$TARGET_PATH"
chmod 0755 "$TARGET_PATH" || true

# Helper: check if a file looks like a valid SQLite DB
is_sqlite() {
  [ -f "$1" ] || return 1
  # read first 16 bytes and look for SQLite header
  head -c 16 "$1" 2>/dev/null | grep -q "SQLite format 3"
}

# Helper: run a thorough integrity check using Python or sqlite3 CLI
integrity_ok() {
  [ -f "$1" ] || return 1
  if command -v python >/dev/null 2>&1; then
    python - "$1" <<'PY'
import sqlite3,sys
f=sys.argv[1]
try:
    con=sqlite3.connect(f)
    r=con.execute('PRAGMA integrity_check;').fetchone()
    ok = r and r[0]=='ok'
    sys.exit(0 if ok else 1)
except Exception:
    sys.exit(2)
PY
    return $?
  fi
  if command -v sqlite3 >/dev/null 2>&1; then
    res=$(sqlite3 "$1" "PRAGMA integrity_check;" 2>/dev/null | head -n1)
    [ "$res" = "ok" ] && return 0 || return 1
  fi
  # Cannot verify; assume OK so we don't accidentally overwrite
  return 0
}

# Backup invalid/non-SQLite files instead of deleting them outright.
backup_invalid() {
  local file="$1"
  local backups_dir="$TARGET_PATH/backups"
  mkdir -p "$backups_dir"
  ts=$(date -u +%Y%m%dT%H%M%SZ)
  mv "$file" "$backups_dir/$(basename "$file").broken.$ts" || rm -f "$file"
  echo "Backed up invalid file to $backups_dir"
}

# If DB file exists and is valid, leave it as-is (do NOT overwrite).
if [ -f "$TARGET_DIR" ]; then
  if is_sqlite "$TARGET_DIR"; then
    if integrity_ok "$TARGET_DIR"; then
      echo "Found valid DB at $TARGET_DIR — leaving intact."
    else
      echo "Found SQLite DB at $TARGET_DIR but it failed PRAGMA integrity_check. Backing up and attempting recovery."
      backup_invalid "$TARGET_DIR"
    fi
  else
    echo "Found file at $TARGET_DIR but it's not a valid SQLite DB. Backing up and attempting recovery."
    backup_invalid "$TARGET_DIR"
  fi
fi

# If DB file still does not exist, try to initialize it from bundled or remote sources.
if [ ! -f "$TARGET_DIR" ]; then
  # Prefer a bundled initial DB named fishbot.initial.db (committed as a normal file)
  if [ -f ./fishbot.initial.db ]; then
    if is_sqlite ./fishbot.initial.db; then
      # copy atomically
      tmp_dest="${TARGET_DIR}.tmp"
      cp ./fishbot.initial.db "$tmp_dest" && mv -f "$tmp_dest" "$TARGET_DIR"
      chmod 0644 "$TARGET_DIR" || true
      echo "Copied initial fishbot.initial.db to $TARGET_DIR"
    else
      echo "Bundled fishbot.initial.db exists but is not a valid SQLite file — not copying."
    fi
  elif [ -f ./fishbot.db ]; then
    if is_sqlite ./fishbot.db; then
      tmp_dest="${TARGET_DIR}.tmp"
      cp ./fishbot.db "$tmp_dest" && mv -f "$tmp_dest" "$TARGET_DIR"
      chmod 0644 "$TARGET_DIR" || true
      echo "Copied bundled fishbot.db to $TARGET_DIR"
    else
      echo "Bundled fishbot.db exists but is not valid — not copying."
    fi
  else
    echo "No bundled initial DB found in image; attempting to download from INIT_DB_URL if provided"
    if [ -n "$INIT_DB_URL" ]; then
      echo "Downloading initial DB from $INIT_DB_URL"
      tmpfile="/tmp/fishbot.initial.db"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$INIT_DB_URL" -o "$tmpfile" || true
      elif command -v wget >/dev/null 2>&1; then
        wget -qO "$tmpfile" "$INIT_DB_URL" || true
      else
        echo "No curl or wget available to download initial DB"
      fi
      if is_sqlite "$tmpfile"; then
        tmp_dest="${TARGET_DIR}.tmp"
        cp "$tmpfile" "$tmp_dest" && mv -f "$tmp_dest" "$TARGET_DIR"
        chmod 0644 "$TARGET_DIR" || true
        echo "Downloaded and copied initial DB to $TARGET_DIR"
        rm -f "$tmpfile"
      else
        echo "Downloaded file is not a valid SQLite DB; leaving $TARGET_DIR empty for the application to create."
        rm -f "$tmpfile" || true
      fi
    else
      echo "A new DB will be created at $TARGET_DIR when app runs"
    fi
  fi
fi

# Restore from latest backup in $TARGET_PATH/backups if appropriate
BACKUPS_DIR="$TARGET_PATH/backups"

# Helper to pick newest backup file matching fishbot.db* (returns path or empty)
latest_backup() {
  [ -d "$BACKUPS_DIR" ] || return 1
  # find files starting with fishbot.db in backups dir, sort by mtime descending
  ls -1t "$BACKUPS_DIR"/fishbot.db* 2>/dev/null | head -n1 || return 1
}

restore_if_needed() {
  lb=$(latest_backup) || return 0
  if [ -z "$lb" ]; then
    return 0
  fi
  echo "Found latest backup: $lb"

  # If target DB missing -> restore. If force restore requested -> restore.
  if [ ! -f "$TARGET_DIR" ] || [ "$RESTORE_FROM_BACKUP" = "1" ]; then
    echo "Restoring backup $lb -> $TARGET_DIR"
    tmp_dest="${TARGET_DIR}.tmp"
    cp "$lb" "$tmp_dest" && mv -f "$tmp_dest" "$TARGET_DIR"
    chmod 0644 "$TARGET_DIR" || true
    echo "Restored latest backup to $TARGET_DIR"
    return 0
  fi

  # If both exist, compare modification times and restore if backup is newer
  backup_mtime=$(stat -c %Y "$lb" 2>/dev/null || stat -f %m "$lb" 2>/dev/null || echo 0)
  target_mtime=$(stat -c %Y "$TARGET_DIR" 2>/dev/null || stat -f %m "$TARGET_DIR" 2>/dev/null || echo 0)
  if [ "$backup_mtime" -gt "$target_mtime" ]; then
    echo "Backup is newer than current DB; restoring $lb -> $TARGET_DIR"
    tmp_dest="${TARGET_DIR}.tmp"
    cp "$lb" "$tmp_dest" && mv -f "$tmp_dest" "$TARGET_DIR"
    chmod 0644 "$TARGET_DIR" || true
    echo "Restored newer backup to $TARGET_DIR"
  else
    echo "Current DB is newer or equal to latest backup; leaving as-is."
  fi
}

restore_if_needed

if is_sqlite "$TARGET_DIR"; then
  echo "Using SQLite DB at $TARGET_DIR"
else
  echo "No valid DB at $TARGET_DIR; application should create one on first run."
fi

# Export env var so code can use it
export FISHBOT_DB_PATH="$TARGET_DIR"

# Start the bot (this replaces the shell process)
exec python -u bot.py
