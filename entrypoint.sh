#!/bin/sh
set -e

# Persistent mount path inside container. Keep default but allow override.
TARGET_DIR=${FISHBOT_DB_PATH:-/data/fishbot.db}
TARGET_PATH=$(dirname "$TARGET_DIR")

mkdir -p "$TARGET_PATH"

# Helper: check if a file looks like a valid SQLite DB
is_sqlite() {
  [ -f "$1" ] || return 1
  head -c 16 "$1" 2>/dev/null | grep -q "SQLite format 3"
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
    echo "Found valid DB at $TARGET_DIR — leaving intact."
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
      cp ./fishbot.initial.db "$TARGET_DIR"
      echo "Copied initial fishbot.initial.db to $TARGET_DIR"
    else
      echo "Bundled fishbot.initial.db exists but is not a valid SQLite file — not copying."
    fi
  elif [ -f ./fishbot.db ]; then
    if is_sqlite ./fishbot.db; then
      cp ./fishbot.db "$TARGET_DIR"
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
        cp "$tmpfile" "$TARGET_DIR"
        echo "Downloaded and copied initial DB to $TARGET_DIR"
        rm -f "$tmpfile"
      else
        echo "Downloaded file is not a valid SQLite DB; leaving $TARGET_DIR empty for the application to create."
        rm -f "$tmpfile"
      fi
    else
      echo "A new DB will be created at $TARGET_DIR when app runs"
    fi
  fi
fi

# Final validation: if a non-empty, valid DB exists, we're good.
if is_sqlite "$TARGET_DIR"; then
  echo "Using SQLite DB at $TARGET_DIR"
else
  echo "No valid DB at $TARGET_DIR; application should create one on first run."
fi

# Export env var so code can use it
export FISHBOT_DB_PATH="$TARGET_DIR"

# Start the bot (this replaces the shell process)
exec python bot.py
