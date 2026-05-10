# RAC — Robo Advisor / Autonomous Capital

[![CI](https://github.com/giovanny-rodriguez/traiding_ia/actions/workflows/ci.yml/badge.svg)](https://github.com/giovanny-rodriguez/traiding_ia/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Mode](https://img.shields.io/badge/mode-paper%20trading-yellow)

RAC is a modular paper-trading engine built for disciplined, auditable automated execution. It connects market data ingestion, technical feature engineering, multi-strategy signal generation, risk-gated order execution, and portfolio tracking into a single observable system.

**Live trading is blocked by default.** The MVP targets Alpaca paper trading with a configurable kill switch and daily Telegram alerts.

---

## Features

| Area | What's included |
|---|---|
| **Market data** | Alpaca historical + live bars, OHLCV validation, TimescaleDB storage |
| **Features** | RSI-14, SMA-3/5/20, Bollinger Bands (20, 2σ), MACD (12/26/9), %B |
| **Strategies** | `trend_following_v1`, `mean_reversion_v1` — multi-strategy worker |
| **Risk** | Daily/weekly loss limits, max drawdown, position size cap, cooldown |
| **Orders** | Idempotent submission (SHA-256 key), reconciliation, SL/TP monitoring |
| **Portfolio** | Mark-to-market, real P&L daily, real drawdown, consistency gate vs. broker |
| **Alerts** | Telegram: fills, kill switch, drawdown breach, daily EOD summary |
| **Backtesting** | Walk-forward simulation, Sharpe, max drawdown, win rate metrics |
| **Local AI** | Signal explanation via Ollama (optional) |
| **Observability** | Dashboard at `/dashboard`, audit trail, structured logs |
| **CI/CD** | Ruff · mypy · pytest · pip-audit · Docker build on every push |

---

## Architecture

```
                        ┌─────────────────────────────────┐
                        │           FastAPI (8000)         │
                        │  /dashboard · /portfolio · ...   │
                        └────────────┬────────────────────┘
                                     │
          ┌──────────────────────────▼──────────────────────────┐
          │                     Worker loop                      │
          │  reconcile → MTM → daily report → kill switch check  │
          │  → fetch bars → features → signals → risk → execute  │
          └───┬──────────────┬───────────────────┬──────────────┘
              │              │                   │
     ┌────────▼───┐  ┌───────▼──────┐  ┌────────▼────────┐
     │   Alpaca   │  │  TimescaleDB │  │    Telegram      │
     │  paper API │  │  (postgres)  │  │  alerts + EOD    │
     └────────────┘  └──────────────┘  └─────────────────┘
```

---

## Quick Start

### Prerequisites

- Docker + Docker Compose
- Alpaca paper account ([alpaca.markets](https://alpaca.markets)) — free
- Telegram bot (optional, for alerts)

### 1. Configure

```bash
cp .env.example .env
# Edit .env — minimum required:
#   ALPACA_API_KEY=...
#   ALPACA_API_SECRET=...
#   TELEGRAM_BOT_TOKEN=...   (optional)
#   TELEGRAM_CHAT_ID=...     (optional)
```

### 2. Start

```bash
docker compose --profile dev up -d --build
```

### 3. Bootstrap DB and verify

```bash
curl -X POST http://localhost:8000/admin/bootstrap
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

### 4. Open dashboard

```
http://localhost:8000/dashboard
```

### 5. Test Telegram alerts

```bash
set -a && source .env && set +a
python scripts/test_telegram.py
```

---

## Services

| Service | Port | Description |
|---|---|---|
| `api` | 8000 | REST API + admin dashboard |
| `worker` | — | Automated trading loop (60s interval) |
| `postgres` | 5432 | TimescaleDB — all market and portfolio data |
| `redis` | 6379 | State and caching |
| `grafana` | 3000 | Observability (profile: `observability`) |
| `prometheus` | 9090 | Metrics (profile: `observability`) |
| `mlflow` | 5000 | Experiment tracking (profile: `backtest`) |

Start only the API (no worker):

```bash
docker compose --profile dev up -d --build api
```

Start with observability stack:

```bash
docker compose --profile observability up -d
```

---

## Key API Endpoints

### Portfolio

```bash
GET  /portfolio/snapshot           # NAV, cash, pnl_daily, drawdown
GET  /portfolio/positions          # open positions
GET  /portfolio/history            # NAV time series (last N snapshots)
POST /portfolio/mark-to-market     # reprice positions from Alpaca
GET  /portfolio/consistency        # RAC vs Alpaca position diff
```

### Strategies

```bash
POST /signals/generate             # run strategy on stored features
GET  /signals/{symbol}/{timeframe} # latest signals
GET  /strategies/performance       # fills + realized P&L per strategy
```

### Orders

```bash
POST /orders/execute-signal        # execute a signal (risk-gated)
POST /orders/reconcile             # sync submitted orders with Alpaca
GET  /orders                       # order history
```

### Admin

```bash
POST /admin/kill-switch            # activate kill switch
POST /admin/kill-switch/reset      # deactivate
GET  /admin/kill-switch            # current state
POST /admin/bootstrap              # run DB migrations
```

### Backtesting

```bash
POST /backtest/run                 # walk-forward simulation
GET  /backtest/list                # recent runs
GET  /backtest/{id}                # run detail + metrics
```

---

## Strategies

### `trend_following_v1`

Buys when price is above SMA-3 > SMA-5 with positive momentum. Requires at least 5 feature points. Stop loss 2%, take profit 3%, max position 5%.

### `mean_reversion_v1`

Buys when RSI-14 < 35 **and** Bollinger %B < 0.2 **and** close < SMA-20 (oversold below the band). Sells the mirror condition. Requires 20 feature points (full BB period). Stop loss 2%, take profit 1.5%, max position 2%.

---

## Risk Controls

| Parameter | Default | Env var |
|---|---|---|
| Max daily loss | 1% | `RAC_MAX_DAILY_LOSS_PCT` |
| Max weekly loss | 3% | `RAC_MAX_WEEKLY_LOSS_PCT` |
| Max drawdown | 5% | `RAC_MAX_DRAWDOWN_PCT` |
| Max position size | 5% | `RAC_MAX_POSITION_PCT` |
| Cooldown after losses | 3 cycles | `RAC_COOLDOWN_AFTER_LOSSES` |

When `RAC_MAX_DRAWDOWN_PCT` is breached a Telegram alert fires. The kill switch can be activated manually via dashboard or API.

---

## Telegram Alerts

| Event | Trigger |
|---|---|
| Order filled | Every fill (buy or sell) |
| Kill switch ON/OFF | State change (deduplicated) |
| Drawdown breach | When `drawdown >= RAC_MAX_DRAWDOWN_PCT` (escalates every 5%) |
| Daily EOD summary | Once per day after 21:00 UTC (≈ 4 pm ET) |

Get a bot token from `@BotFather` and your `chat_id` from `@userinfobot`.

---

## Development

### Run tests locally

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Lint + type check

```bash
ruff check rac/ tests/ --select E,F,W,I
mypy rac/ --ignore-missing-imports --no-strict-optional
```

### Add a strategy

1. Create `rac/strategies/my_strategy.py` implementing `generate(features, environment)` and exposing a `manifest` (see `trend_following.py` for reference).
2. Register it in `rac/strategies/service.py` → `_load_strategy`.
3. Add the strategy ID to `RAC_STRATEGIES` in `.env`.
4. Write tests in `tests/test_my_strategy.py`.

### DB migrations

Add a numbered SQL file to `db/migrations/` and run:

```bash
curl -X POST http://localhost:8000/admin/bootstrap
```

---

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration reference](docs/configuration.md)
- [Strategies](docs/strategies.md)
- [Development guide](docs/development.md)
