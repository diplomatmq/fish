# ── Stage 1: build Telegram WebApp UI ─────────────────────────────────────────
FROM node:20-alpine AS ui-build
WORKDIR /ui
COPY webapp/ui_from_testpers/package.json webapp/ui_from_testpers/package-lock.json ./
RUN npm ci
COPY webapp/ui_from_testpers/ ./
RUN npm run build

# ── Stage 2: Python app ───────────────────────────────────────────────────────
FROM python:3.11-slim
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libjpeg-dev \
    libpng-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=ui-build /ui/dist ./webapp/ui_from_testpers/dist
RUN chmod +x ./entrypoint.sh || true

ENV PYTHONUNBUFFERED=1
CMD ["./entrypoint.sh"]
