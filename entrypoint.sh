#!/bin/sh
set -e

if [ -z "$DATABASE_URL" ]; then
  echo "Error: DATABASE_URL is not set — required for Postgres."
  exit 1
fi

echo "Using Postgres via DATABASE_URL"
exec python -u bot.py
