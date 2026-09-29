# Stock Intelligence Platform

A FastAPI backend for scanning, screening, and backtesting stocks
against technical indicators, with saved strategies, watchlists,
and email alerts on newly-triggered signals.

## Stack

- **API**: FastAPI + Uvicorn
- **Database**: PostgreSQL via SQLAlchemy 2.0 (psycopg v3) + Alembic migrations
- **Auth**: JWT access/refresh tokens, argon2 password hashing
- **Scheduling**: APScheduler (daily market data sync + alert evaluation)
- **Rate limiting**: Redis-backed (falls back to in-memory if `REDIS_URL` isn't set)
- **Email**: SMTP (falls back to logging the message if unconfigured)

## Features

- **Auth**: register/login/refresh/logout, change/forgot/reset password, role-based access (user/admin)
- **Market data**: CSV upload + sync pipeline, incremental indicator computation (SMA/EMA/RSI/MACD/ATR/ADX/Supertrend/Bollinger Bands/breakout levels/volume surge)
- **Scanner**: run ad-hoc or named strategies (breakout/breakdown/swing) against a JSON expression tree (AND/OR/NOT, comparisons, crossovers); every run is persisted per-user
- **Backtesting**: replay a strategy's historical signals and measure forward returns
- **Saved strategies**: save a custom expression tree under a name, reuse it via `/strategies/{id}/scan` or in an alert rule
- **Watchlists**: group symbols you care about
- **Alerts**: "notify me by email when `<strategy>` matches", optionally scoped to a watchlist; only notifies on *newly* triggered signals, not every day a match persists
- Full API reference at `/docs` once the server is running

## Setup

1. **Clone and create a virtual environment**

   ```bash
   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Provide a `.env` file** (see `.env` in the repo for the full list). At minimum you need:

   - `DATABASE_URL` — a PostgreSQL connection string using the `psycopg` v3 driver, e.g. `postgresql+psycopg://user:password@localhost:5432/dbname`
   - `JWT_SECRET_KEY` — any long random string
   - `REDIS_URL` — optional; without it, rate limiting falls back to an in-memory store (fine for local dev, not for more than one worker process)
   - `SMTP_HOST` and friends — optional; without them, emails (password reset, alerts) are logged instead of sent

3. **Run migrations**

   ```bash
   alembic upgrade head
   ```

4. **Start the server**

   ```bash
   uvicorn main:app --reload
   ```

   Then open `http://127.0.0.1:8000/docs` for the interactive API reference.

### Running with Docker instead

```bash
docker compose up --build
```

This starts both the API and a Postgres container (see `docker-compose.yml`). You'll still need to run `alembic upgrade head` once the containers are up.

## Getting data into the system

There's no live market data feed yet — instruments and daily candles come in via CSV upload:

1. `POST /market-data/upload` (admin only) with a CSV of daily candles for a symbol.
2. `POST /market-data/sync` to run the full pipeline (compute indicators, update feature snapshots).
3. Optionally set `SYNC_SCHEDULE_ENABLED=true` (+ `SYNC_SCHEDULE_HOUR`/`SYNC_SCHEDULE_MINUTE`) to run step 2 automatically every day; alert evaluation runs automatically a configurable delay after that (`ALERT_SCHEDULE_DELAY_MINUTES`).

## Testing

```bash
pytest
```

The suite covers indicators, the scan expression evaluator, backtesting, auth, rate limiting, watchlists, alerts, and saved strategies — including full HTTP round-trips against an in-memory SQLite database, so no live Postgres/Redis instance is needed to run it.