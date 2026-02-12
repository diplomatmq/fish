FROM python:3.11-slim
# CACHEBUST: 2026-02-13T01:23:45
WORKDIR /app

# Install system deps for Pillow and others if needed (small set)
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
RUN chmod +x ./entrypoint.sh || true

ENV PYTHONUNBUFFERED=1
CMD ["./entrypoint.sh"]
