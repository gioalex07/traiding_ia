# Development Guide

## Local Setup

### Requirements
- Python 3.12+
- Docker + Docker Compose
- Alpaca paper account (free at [alpaca.markets](https://alpaca.markets))

### Install dependencies

```bash
pip install -r requirements-dev.txt
```

### Run the stack

```bash
cp .env.example .env
# Fill in ALPACA_API_KEY and ALPACA_API_SECRET

docker compose --profile dev up -d --build
curl -X POST http://localhost:8000/admin/bootstrap
curl http://localhost:8000/health
```

Open the dashboard at `http://localhost:8000/dashboard`.

---

## Testing

```bash
# All tests
pytest tests/ -v

# Single file
pytest tests/test_mean_reversion_strategy.py -v

# With coverage
pytest tests/ --cov=rac --cov-report=term-missing
```

Tests are fully offline — no database or Alpaca connection required. All external dependencies are faked via in-memory stubs.

---

## Code Quality

```bash
# Lint (style + imports)
ruff check rac/ tests/ --select E,F,W,I

# Auto-fix safe issues
ruff check rac/ tests/ --select E,F,W,I --fix

# Type check
mypy rac/ --ignore-missing-imports --no-strict-optional
```

---

## CI Pipeline

Five GitHub Actions jobs run on every push to `main` and every PR:

| Job | Tool | What it checks |
|---|---|---|
| Lint | ruff 0.9.10 | Style, imports, unused vars |
| Type check | mypy 1.15.0 | Type annotations across `rac/` |
| Tests | pytest 9.0.3 | All tests in `tests/` |
| Security | pip-audit | CVEs in production dependencies |
| Docker build | Docker | API + worker images build cleanly |

Docker build only runs after lint and tests pass.

---

## Project Structure

```
rac/
├── api/            FastAPI application + dashboard HTML
├── admin/          Kill switch repository
├── audit/          Immutable event log
├── backtest/       Walk-forward engine, portfolio simulator, metrics
├── brokers/        Alpaca adapter (base class + implementation)
├── config.py       All settings via environment variables
├── dashboard/      Dashboard service + HTML template
├── db/             Bootstrap (migrations runner), health checks
├── discovery/      Environment discovery (broker/AI detection)
├── features/       Technical indicator computation and storage
├── local_ai/       Ollama client for signal explanation
├── market_data/    OHLCV ingestion, validation, historical loader
├── notifications/  Telegram client + AlertService
├── orders/         Executor, reconciliation, repository
├── pipeline/       End-to-end paper analysis pipeline
├── portfolio/      NAV snapshots, mark-to-market, consistency gate
├── reports/        Daily EOD report builder
├── risk/           Risk policy evaluation
├── strategies/     Signal generation, performance tracking
└── worker/         Main async loop
db/
└── migrations/     Numbered SQL migrations (run via /admin/bootstrap)
tests/              All unit tests (offline, no DB required)
docs/               This documentation
scripts/            Utility scripts (e.g. test_telegram.py)
ops/
└── prometheus/     prometheus.yml scrape config
```

---

## Adding a DB Migration

1. Create `db/migrations/NNN_description.sql` (increment the number).
2. Apply it:

```bash
curl -X POST http://localhost:8000/admin/bootstrap
```

The bootstrap endpoint is idempotent — it applies only migrations not yet recorded in the `schema_migrations` table.

---

## Running the Worker Manually

```bash
# Inside the container
docker compose exec worker python -m rac.worker.loop

# Locally (requires DB + Alpaca credentials in environment)
set -a && source .env && set +a
python -m rac.worker.loop
```

---

## Telegram Setup

1. Open Telegram and search `@BotFather`.
2. Send `/newbot` and follow the prompts — copy the token.
3. Send a message to your bot, then open `@userinfobot` to get your `chat_id`.
4. Set in `.env`:

```
TELEGRAM_BOT_TOKEN=1234567890:ABCdef...
TELEGRAM_CHAT_ID=123456789
```

5. Test:

```bash
set -a && source .env && set +a
python scripts/test_telegram.py
```
