FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# Tizim paketlari (cryptography uchun kerakli bo'lishi mumkin)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
        libffi-dev \
        curl \
    && rm -rf /var/lib/apt/lists/*

# Avval requirements — Docker layer cache uchun
COPY requirements.txt /app/
RUN pip install --upgrade pip && pip install -r requirements.txt

# Loyiha kodi
COPY . /app/

# SQLite fayl uchun (volume bilan saqlanadi)
RUN mkdir -p /app/data
ENV STORE_DB_PATH=/app/data/store.db

# Static fayllar (admin uchun kerak bo'lsa)
RUN python manage.py collectstatic --noinput || true

EXPOSE 8001

# Production server — gunicorn
CMD ["gunicorn", "sadinov.wsgi:application", \
     "--bind", "0.0.0.0:8001", \
     "--workers", "3", \
     "--timeout", "60", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
