# RAC — Robo Advisor / Autonomous Capital

[![CI](https://github.com/gioalex07/traiding_ia/actions/workflows/ci.yml/badge.svg)](https://github.com/gioalex07/traiding_ia/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Mode](https://img.shields.io/badge/mode-paper%20trading-yellow)
![Tests](https://img.shields.io/badge/tests-155%2B-green)

RAC is a modular paper-trading engine built for disciplined, auditable automated execution. It connects market data ingestion, technical feature engineering, multi-strategy signal generation, risk-gated order execution, portfolio tracking, Telegram alerts, and a machine-learning baseline into a single observable system.

**Live trading is blocked by default.** The MVP targets Alpaca paper trading with a configurable kill switch, daily Telegram reports, and EOD ML retraining.

---

## Features

| Area | What's included |
|---|---|
| **Market data** | Alpaca historical + live bars, OHLCV validation, TimescaleDB |
| **Features** | RSI-14, SMA-3/5/20, Bollinger Bands (20,2σ), MACD (12/26/9), %B |
| **Strategies** | `trend_following_v1`, `mean_reversion_v1` (v0.2.0 — TP 3%, SL 1%) |
| **Risk** | Daily/weekly loss limits, max drawdown, position cap, cooldown, one-position-per-symbol guard |
| **Orders** | Idempotent submission (SHA-256), reconciliation, SL/TP auto-close, cancel on kill switch |
| **Portfolio** | Mark-to-market, real pnl_daily, real drawdown from peak, consistency gate vs broker |
| **Trade outcomes** | Every closed trade linked to its opening signal: P&L, duration, reason |
| **Alerts** | Telegram: fills, kill switch, drawdown breach, daily EOD summary, ML retrain results |
| **Machine Learning** | Signal labeling (TP/SL simulation), RandomForest baseline, feature importance, EOD auto-retrain |
| **Dashboard** | Sidebar nav, 5 sections, live positions with TP/SL bars, NAV chart, win/loss donut, feature importance bars |
| **Live config** | Confidence threshold, timeframe, symbols — change from dashboard without restart |
| **CI/CD** | Ruff · mypy · pytest (155+) · pip-audit · Docker build on every push |

---

## Architecture

```
                        ┌─────────────────────────────────────┐
                        │         FastAPI (port 8000)          │
                        │  Dashboard · REST API · ML endpoints │
                        └────────────┬────────────────────────┘
                                     │
          ┌──────────────────────────▼─────────────────────────────┐
          │                      Worker loop                         │
          │  reconcile → MTM → daily report → label → retrain       │
          │  → kill switch → fetch bars → features → signals        │
          │  → risk → execute (one position per symbol)             │
          └───┬──────────────┬──────────────────┬──────────────────┘
              │              │                  │
     ┌────────▼───┐  ┌───────▼──────┐  ┌───────▼──────────┐
     │   Alpaca   │  │  TimescaleDB │  │     Telegram      │
     │  paper API │  │  (postgres)  │  │  alerts + EOD +   │
     └────────────┘  └──────────────┘  │  ML retrain notif │
                                        └──────────────────┘
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
# Required:
#   ALPACA_API_KEY=...
#   ALPACA_API_SECRET=...
# Optional:
#   TELEGRAM_BOT_TOKEN=...
#   TELEGRAM_CHAT_ID=...
```

### 2. Start

```bash
docker compose --profile dev up -d --build
```

### 3. Bootstrap DB and verify

```bash
curl -X POST http://localhost:8000/admin/bootstrap
curl http://localhost:8000/health
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
| `mlflow` | 5000 | Experiment tracking (profile: `backtest`) |

```bash
# Only API (no worker)
docker compose --profile dev up -d --build api

# Observability stack
docker compose --profile observability up -d
```

---

## Dashboard

Five sections accessible from the sidebar:

| Section | What you see |
|---|---|
| **Overview** | KPI cards (NAV, P&L today, Drawdown %, Equity), live positions with TP/SL progress bars, NAV chart with hover tooltip |
| **Portfolio** | Fills today/week, trade outcomes per close, strategy P&L summary, RAC vs Alpaca positions, consistency gate |
| **Signals & Orders** | Strategy performance, signal/order tables, paper pipeline runner, reconciliation |
| **Machine Learning** | Label stats, win/loss donut chart, feature importance bar chart, label + train buttons |
| **System** | Kill switch, live worker config, audit trail, bootstrap |

---

## Key API Endpoints

### Portfolio

```bash
GET  /portfolio/snapshot          # NAV, cash, pnl_daily, drawdown
GET  /portfolio/live-positions    # open positions with TP/SL distances
GET  /portfolio/fills             # recent fills (days param)
GET  /portfolio/history           # NAV time series
POST /portfolio/mark-to-market    # reprice from Alpaca
GET  /portfolio/consistency       # RAC vs Alpaca diff
```

### Strategies & Orders

```bash
POST /signals/generate            # run strategy on stored features
GET  /signals/{symbol}/{tf}       # latest signals
GET  /strategies/performance      # fills + realized P&L per strategy
POST /orders/execute-signal       # risk-gated order execution
POST /orders/reconcile            # sync with Alpaca
GET  /trade-outcomes              # closed trade history with P&L
GET  /trade-outcomes/summary      # wins/losses/avg % per strategy
```

### Machine Learning

```bash
POST /ml/label                    # label unlabeled signals (tp_pct, sl_pct, batch_size)
GET  /ml/stats                    # win/loss/timeout distribution
POST /ml/train                    # train RandomForest, returns metrics
GET  /ml/dataset/size             # labeled sample count
```

### Admin

```bash
POST /admin/kill-switch           # activate
POST /admin/kill-switch/reset     # deactivate
GET  /admin/worker-config         # current live config
PUT  /admin/worker-config/{key}   # change without restart
POST /admin/bootstrap             # run DB migrations
```

---

## Strategies

### `trend_following_v1`

Buys when `close > SMA-3 > SMA-5` with positive `return_1`. Confidence proportional to momentum magnitude.

| Parameter | Value |
|---|---|
| Min feature points | 5 |
| Stop loss | 2% |
| Take profit | 3% |
| Max position | 5% |

### `mean_reversion_v1` (v0.2.0)

Buys when RSI-14 < 35 **and** Bollinger %B < 0.2 **and** close < SMA-20.  
Risk/reward corrected in v0.2.0: TP 3x wider than SL gives break-even at 25% win rate.

| Parameter | Value |
|---|---|
| Min feature points | 20 |
| Stop loss | **1%** |
| Take profit | **3%** |
| Max position | 2% |

**One-position-per-symbol rule:** the worker skips BUY signals when a position is already open, preventing over-concentration.

---

## Risk Controls

| Parameter | Default | Env var |
|---|---|---|
| Max daily loss | 1% | `RAC_MAX_DAILY_LOSS_PCT` |
| Max weekly loss | 3% | `RAC_MAX_WEEKLY_LOSS_PCT` |
| Max drawdown alert | 5% | `RAC_MAX_DRAWDOWN_PCT` |
| Max position size | 5% | `RAC_MAX_POSITION_PCT` |
| Cooldown after losses | 3 cycles | `RAC_COOLDOWN_AFTER_LOSSES` |
| Min signal confidence | 0.5 | `RAC_MIN_SIGNAL_CONFIDENCE` (live-configurable) |

---

## Telegram Alerts

| Event | Trigger |
|---|---|
| Order filled | Every fill (BUY or SELL) |
| Kill switch ON/OFF | State change (deduplicated) |
| Drawdown breach | When `drawdown ≥ RAC_MAX_DRAWDOWN_PCT` (escalates +5%) |
| Daily EOD summary | Once per day after 21:00 UTC (≈ 4 pm ET) |
| ML model retrained | After each EOD auto-retrain with accuracy + ROC-AUC |

Get a bot token from `@BotFather` and your `chat_id` from `@userinfobot`.

---

## Machine Learning Pipeline

Every day at market close (21:00 UTC) the worker automatically:

1. **Labels** up to 5,000 new signals by simulating TP/SL against forward OHLCV bars
2. **Retrains** a RandomForest classifier if ≥ 50 new labels accumulated
3. **Sends** model metrics to Telegram

Feature vector (9 dimensions per signal):
`rsi_14, bb_pct_b, sma_ratio, bb_width, macd, macd_hist, return_1, volatility_5, direction_buy`

The model improves as more diverse market conditions are recorded. Manual trigger available via dashboard (ML section) or API.

---

## Development

```bash
pip install -r requirements-dev.txt

# Tests
pytest tests/ -v

# Lint + type check
ruff check rac/ tests/ --select E,F,W,I
mypy rac/ --ignore-missing-imports --no-strict-optional

# ML: label signals and train
curl -X POST "http://localhost:8000/ml/label?tp_pct=3.0&sl_pct=1.0&batch_size=2000"
curl -X POST "http://localhost:8000/ml/train?n_estimators=100"
```

---

## Documentation

- [Architecture](docs/architecture.md)
- [Configuration reference](docs/configuration.md)
- [Strategies](docs/strategies.md)
- [Development guide](docs/development.md)
