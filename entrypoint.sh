#!/bin/sh
set -e

# Persistent mount path inside container
TARGET_DIR=${FISHBOT_DB_PATH:-/data/fishbot.db}
TARGET_PATH=$(dirname "$TARGET_DIR")

mkdir -p "$TARGET_PATH"

# If DB file doesn't exist in the volume, copy initial one from image if present
if [ ! -f "$TARGET_DIR" ]; then
  if [ -f ./fishbot.db ]; then
    cp ./fishbot.db "$TARGET_DIR"
    echo "Copied initial fishbot.db to $TARGET_DIR"
  else
    echo "No initial fishbot.db found in image; a new DB will be created at $TARGET_DIR when app runs"
  fi
fi

# Export env var so code can use it
export FISHBOT_DB_PATH="$TARGET_DIR"

# If config.py reads FISHBOT_DB_PATH, it will pick it up. Start the bot.
exec python bot.py
