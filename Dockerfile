FROM python:3.12-slim

WORKDIR /app

# System deps needed to build psycopg (v3) and other C-extension
# packages.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Non-root user
RUN useradd --create-home appuser
RUN mkdir -p /data/candles && chown -R appuser:appuser /data
USER appuser

EXPOSE 8000

# Run migrations, then start the API. In production you may prefer
# to run migrations as a separate step/job instead of on every
# container start.
CMD ["sh", "-c", "alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]