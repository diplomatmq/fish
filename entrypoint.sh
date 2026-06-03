#!/bin/sh

set -e



if [ -n "$DATABASE_URL" ]; then

  echo "Using Postgres via DATABASE_URL"

elif [ -n "$DB_HOST" ] && [ -n "$DB_NAME" ] && [ -n "$DB_USER" ] && [ -n "$DB_PASSWORD" ]; then

  DB_PORT_VALUE="${DB_PORT:-5432}"

  export DATABASE_URL="postgresql://${DB_USER}:${DB_PASSWORD}@${DB_HOST}:${DB_PORT_VALUE}/${DB_NAME}"

  echo "Using Postgres via DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD"

else

  echo "DATABASE_URL is not set. Falling back to SQLite (FISHBOT_DB_PATH)."

  mkdir -p /data

  export FISHBOT_DB_PATH="${FISHBOT_DB_PATH:-/data/fishbot.db}"

fi



SERVICE_MODE_VALUE="${SERVICE_MODE:-bot}"



if [ "$SERVICE_MODE_VALUE" = "webapp" ]; then

  export APP_HOST="${APP_HOST:-0.0.0.0}"

  export APP_PORT="${PORT:-${APP_PORT:-8008}}"

  export GUNICORN_WORKERS="${GUNICORN_WORKERS:-4}"

  # Webhook mode: gunicorn alone cannot serve bot updates — need internal bot on BOT_INTERNAL_WEBHOOK_PORT.
  if [ "${BOT_USE_WEBHOOK:-1}" != "0" ] && [ -n "${BOT_TOKEN:-}" ]; then
    echo "Starting webapp+bot (launcher): public port=${APP_PORT}, internal bot webhook port=${BOT_INTERNAL_WEBHOOK_PORT:-9000}"
    exec python -u launcher.py
  fi

  echo "Starting webapp-only mode on ${APP_HOST}:${APP_PORT} with gunicorn workers=${GUNICORN_WORKERS}"

  exec gunicorn -w "${GUNICORN_WORKERS}" -b "${APP_HOST}:${APP_PORT}" "webapp.app:app" --timeout "${GUNICORN_TIMEOUT:-120}"

fi



if [ "$SERVICE_MODE_VALUE" = "all" ]; then
  export APP_HOST="${APP_HOST:-0.0.0.0}"
  export APP_PORT="${PORT:-${APP_PORT:-8008}}"
  echo "Starting unified mode (Bot + WebApp) via launcher.py on ${APP_HOST}:${APP_PORT}"
  exec python -u launcher.py
fi



echo "Starting bot mode"

exec python -u bot.py

