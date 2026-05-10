# Architecture

## Overview

RAC is structured as a pipeline of loosely coupled services, each with a single responsibility. The worker loop orchestrates them in sequence every `RAC_LOOP_INTERVAL` seconds.

```
Market data (Alpaca)
      │
      ▼
MarketDataIngestor          ← validates, deduplicates, stores OHLCV bars
      │
      ▼
FeatureService              ← computes RSI, SMA, BB, MACD from stored bars
      │
      ▼
StrategyEngine              ← generates BUY / SELL / HOLD signals
      │
      ▼
RiskManager                 ← enforces daily loss, drawdown, position limits
      │
      ▼
PaperOrderExecutor          ← submits to Alpaca or creates synthetic fills
      │
      ▼
ReconciliationService       ← polls Alpaca for fill status, updates portfolio
      │
      ▼
PortfolioRepository         ← records NAV, pnl_daily, drawdown snapshots
      │
      ▼
AlertService (Telegram)     ← fills, kill switch, drawdown, daily summary
```

## Module Map

| Package | Responsibility |
|---|---|
| `rac.market_data` | OHLCV ingestion, validation, storage, historical loader |
| `rac.features` | Technical indicator computation (RSI, BB, MACD, SMA) |
| `rac.strategies` | Signal generation, strategy manifests, performance queries |
| `rac.risk` | Risk policy evaluation (loss limits, drawdown, position cap) |
| `rac.orders` | Order models, idempotent executor, reconciliation, fill tracking |
| `rac.portfolio` | NAV snapshots, mark-to-market, consistency gate vs. broker |
| `rac.brokers` | Alpaca adapter (paper + data API, pagination) |
| `rac.notifications` | Telegram client, AlertService with deduplication |
| `rac.reports` | Daily EOD report builder |
| `rac.admin` | Kill switch (append-only event log) |
| `rac.backtest` | Walk-forward engine, portfolio simulator, metrics |
| `rac.audit` | Immutable event log for all operational decisions |
| `rac.local_ai` | Ollama client for signal explanation |
| `rac.worker` | Main async loop, cycle orchestration |
| `rac.api` | FastAPI control plane + admin dashboard |
| `rac.db` | Bootstrap (migrations runner), health checks |

## Data Flow: Worker Cycle

Each cycle runs these steps in order:

1. **Reconcile** pending orders against Alpaca — marks fills, triggers Telegram notification per fill.
2. **Mark to market** — reprices open positions, computes real `pnl_daily` and `drawdown` from peak NAV.
3. **Daily report** — sends EOD Telegram summary once per day after 21:00 UTC.
4. **Kill switch check** — if active, skips order execution and sends alert (deduplicated).
5. **Account + positions** — fetches equity, cash, open positions from Alpaca.
6. **Symbol loop** — for each watched symbol:
   - Fetch latest bars → ingest → compute features
   - Monitor SL/TP on open position
   - Run strategies in priority order; first actionable signal wins

## Database Schema

All time-series tables use TimescaleDB hypertables. Key tables:

| Table | Purpose |
|---|---|
| `ohlcv_bars` | Raw market data |
| `feature_points` | Computed technical indicators |
| `signals` | Strategy output with direction + confidence |
| `orders` | All orders with risk decision, SL/TP, fill tracking |
| `fills` | Immutable fill records (idempotent on `order_id`) |
| `positions` | Current open positions per environment |
| `portfolio_snapshots` | NAV, cash, pnl_daily, drawdown time series |
| `kill_switch_events` | Append-only kill switch state log |
| `audit_events` | Full operational audit trail |

## Safety Design

- **Live trading blocked by default** — requires `RAC_LIVE_TRADING_ENABLED=true` + `RAC_TRADING_MODE=live`.
- **Kill switch** — append-only event log; last event determines active state. Can be triggered via API, dashboard, or automatically when drawdown exceeds threshold.
- **Idempotency** — all orders use a SHA-256 key; duplicate signals never produce duplicate orders.
- **Reconciliation** — the worker never trusts its own memory for fill status; always re-queries Alpaca.
- **Portfolio consistency gate** — compares RAC positions vs. Alpaca positions before allowing new orders; blocks on mismatch.
