# Configuration Reference

All configuration is via environment variables. Copy `.env.example` to `.env` and fill in the values. Docker Compose reads `.env` automatically.

## Core

| Variable | Default | Description |
|---|---|---|
| `RAC_ENV` | `dev` | Environment label (`dev`, `paper`, `live`) |
| `RAC_TRADING_MODE` | `paper` | Active trading mode (`paper`, `live`, `backtest`) |
| `RAC_LIVE_TRADING_ENABLED` | `false` | Must be `true` to allow live order submission |
| `RAC_BROKER` | `auto` | Broker to use (`auto`, `alpaca`) |

## Alpaca

| Variable | Default | Description |
|---|---|---|
| `ALPACA_API_KEY` | *(required)* | Alpaca API key (paper or live) |
| `ALPACA_API_SECRET` | *(required)* | Alpaca API secret |
| `ALPACA_PAPER_BASE_URL` | `https://paper-api.alpaca.markets` | Paper trading endpoint |
| `ALPACA_DATA_BASE_URL` | `https://data.alpaca.markets/v2` | Market data endpoint (IEX free tier — 15 min delay) |

## Storage

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://rac:rac@postgres:5432/rac` | TimescaleDB connection |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection |

## Worker

| Variable | Default | Description |
|---|---|---|
| `RAC_SYMBOLS` | `AAPL` | Comma-separated list of symbols to trade |
| `RAC_TIMEFRAME` | `1Min` | Bar timeframe for feature computation |
| `RAC_STRATEGIES` | `trend_following_v1,mean_reversion_v1` | Ordered strategies per cycle |
| `RAC_LOOP_INTERVAL` | `60` | Seconds between worker cycles |
| `RAC_MIN_SIGNAL_CONFIDENCE` | `0.6` | Minimum confidence to execute (0.0–1.0) |

> **Live-configurable:** `RAC_SYMBOLS`, `RAC_TIMEFRAME`, `RAC_MIN_SIGNAL_CONFIDENCE`, and signal max age can be changed at runtime via the dashboard (System → Worker Config) or `PUT /admin/worker-config/{key}` — no restart needed.

## Risk Limits

| Variable | Default | Description |
|---|---|---|
| `RAC_MAX_DAILY_LOSS_PCT` | `1.0` | Max allowed daily loss as % of equity |
| `RAC_MAX_WEEKLY_LOSS_PCT` | `3.0` | Max allowed weekly loss as % of equity |
| `RAC_MAX_DRAWDOWN_PCT` | `5.0` | Drawdown threshold for Telegram alert |
| `RAC_MAX_POSITION_PCT` | `5.0` | Max single-order size as % of equity |
| `RAC_MAX_ASSET_EXPOSURE_PCT` | `10.0` | Max total exposure per asset as % of equity |
| `RAC_COOLDOWN_AFTER_LOSSES` | `3` | Cycles to wait after consecutive losses |

## Telegram Alerts

| Variable | Default | Description |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | *(empty = disabled)* | Bot token from `@BotFather` |
| `TELEGRAM_CHAT_ID` | *(empty = disabled)* | Your chat ID from `@userinfobot` |

When both are set, alerts fire for: order fills, kill switch state changes, drawdown breaches, daily EOD summary, and ML model retrain results.

Test connectivity:
```bash
set -a && source .env && set +a
python scripts/test_telegram.py
```

## Observability

| Variable | Default | Description |
|---|---|---|
| `GRAFANA_ADMIN_USER` | `admin` | Grafana admin username |
| `GRAFANA_ADMIN_PASSWORD` | `change-me` | Grafana admin password |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama endpoint for signal explanation |

## Docker Compose Profiles

| Profile | Services started |
|---|---|
| `dev` | api, worker, scheduler, postgres, redis, redpanda, prometheus, grafana, loki, mlflow |
| `paper` | Same as dev |
| `backtest` | api, worker, scheduler, postgres, redis, redpanda, mlflow |
| `observability` | postgres, prometheus, grafana, loki |
| `ollama-local` | ollama (GPU-accelerated) |

## Worker Config (live, no restart)

These keys live in the `worker_config` DB table and are read at the start of every cycle:

| Key | Default | Description |
|---|---|---|
| `min_signal_confidence` | `0.6` | Confidence threshold (0.0–1.0) |
| `watched_symbols` | `AAPL,MSFT,SPY` | Active symbols |
| `watched_timeframe` | `5Min` | Bar timeframe |
| `signal_max_age_seconds` | `1200` | Max signal age before stale discard |

Change via dashboard (System → Worker Config) or API:
```bash
curl -X PUT http://localhost:8000/admin/worker-config/min_signal_confidence \
  -H "Content-Type: application/json" \
  -d '{"value": "0.55", "actor": "cli"}'
```
