#!/bin/sh
set -e

# Persistent mount path inside container
TARGET_DIR=${FISHBOT_DB_PATH:-/data/fishbot.db}
TARGET_PATH=$(dirname "$TARGET_DIR")

mkdir -p "$TARGET_PATH"

# If DB file exists but is invalid (not a SQLite file), replace it.
if [ -f "$TARGET_DIR" ]; then
  if ! (head -c 16 "$TARGET_DIR" 2>/dev/null | grep -q "SQLite format 3"); then
    echo "Existing DB at $TARGET_DIR is invalid or corrupted — replacing it."
    rm -f "$TARGET_DIR"
  fi
fi

# If DB file doesn't exist in the volume, copy initial one from image if present
if [ ! -f "$TARGET_DIR" ]; then
  # Prefer a bundled initial DB named fishbot.initial.db (committed as a normal file)
  if [ -f ./fishbot.initial.db ]; then
    cp ./fishbot.initial.db "$TARGET_DIR"
    echo "Copied initial fishbot.initial.db to $TARGET_DIR"
  elif [ -f ./fishbot.db ]; then
    # fallback: older setups may include fishbot.db directly
    cp ./fishbot.db "$TARGET_DIR"
    echo "Copied initial fishbot.db to $TARGET_DIR"
  else
    echo "No initial fishbot DB found in image; attempting to download from INIT_DB_URL if provided"
    if [ -n "$INIT_DB_URL" ]; then
      echo "Downloading initial DB from $INIT_DB_URL"
      if command -v curl >/dev/null 2>&1; then
        curl -fsSL "$INIT_DB_URL" -o ./fishbot.initial.db || echo "curl failed to download initial DB"
      elif command -v wget >/dev/null 2>&1; then
        wget -qO ./fishbot.initial.db "$INIT_DB_URL" || echo "wget failed to download initial DB"
      else
        echo "No curl or wget available to download initial DB"
      fi
      if [ -f ./fishbot.initial.db ]; then
        cp ./fishbot.initial.db "$TARGET_DIR"
        echo "Downloaded and copied initial fishbot.initial.db to $TARGET_DIR"
      else
        echo "Download failed or file missing; a new DB will be created at $TARGET_DIR when app runs"
      fi
    else
      echo "A new DB will be created at $TARGET_DIR when app runs"
    fi
  fi
fi

# Export env var so code can use it
export FISHBOT_DB_PATH="$TARGET_DIR"

# If config.py reads FISHBOT_DB_PATH, it will pick it up. Start the bot.
exec python bot.py
