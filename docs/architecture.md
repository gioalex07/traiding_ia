# Architecture

## Overview

RAC is structured as a pipeline of loosely coupled services, each with a single responsibility. The worker loop orchestrates them in sequence every `RAC_LOOP_INTERVAL` seconds.

```
Market data (Alpaca IEX, ~15 min delay)
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
_skip_reason()              ← guards: stale, already_in_position, no_position_to_sell
      │
      ▼
RiskManager                 ← enforces daily loss, drawdown, position limits
      │
      ▼
PaperOrderExecutor          ← submits to Alpaca, records in DB
      │
      ▼
ReconciliationService       ← polls Alpaca for fill status, updates portfolio + trade outcomes
      │
      ▼
PortfolioRepository         ← records NAV, pnl_daily (real), drawdown (from peak)
      │
      ▼
AlertService (Telegram)     ← fills, kill switch, drawdown, daily summary, ML results
```

## Module Map

| Package | Responsibility |
|---|---|
| `rac.market_data` | OHLCV ingestion, validation, storage, historical loader |
| `rac.features` | Technical indicator computation (RSI, BB, MACD, SMA) |
| `rac.strategies` | Signal generation, strategy manifests, performance queries |
| `rac.risk` | Risk policy evaluation (loss limits, drawdown, position cap) |
| `rac.orders` | Executor, reconciliation, outcome tracking, repository |
| `rac.portfolio` | NAV snapshots, mark-to-market, consistency gate vs broker |
| `rac.brokers` | Alpaca adapter (paper + data API, cancel_order, pagination) |
| `rac.notifications` | Telegram client, AlertService with deduplication |
| `rac.reports` | Daily EOD report builder |
| `rac.ml` | Signal labeling, feature extraction, RandomForest trainer |
| `rac.admin` | Kill switch (append-only log), worker config (DB-backed live config) |
| `rac.backtest` | Walk-forward engine, portfolio simulator, metrics |
| `rac.audit` | Immutable event log for all operational decisions |
| `rac.local_ai` | Ollama client for signal explanation (optional) |
| `rac.worker` | Main async loop, cycle orchestration |
| `rac.api` | FastAPI control plane + admin dashboard |
| `rac.db` | Bootstrap (migrations runner), health checks |

## Worker Cycle (6 steps per interval)

1. **Reconcile** — poll Alpaca for pending order status; mark fills, trigger outcome recording + Telegram notification per fill
2. **Mark to market** — reprice open positions, compute real `pnl_daily` and `drawdown` from peak NAV
3. **EOD block** (once/day after 21:00 UTC) — send daily report, label up to 5k signals, retrain ML model if ≥50 new labels
4. **Kill switch check** — if active: cancel all pending orders at Alpaca, block execution, send alert (deduplicated)
5. **Account + positions** — fetch equity, cash, open positions from Alpaca
6. **Symbol loop** — for each watched symbol:
   - Fetch latest bars → ingest → compute features
   - Monitor SL/TP on open position (`_sl_tp_trigger`)
   - Run strategies in priority order; skip if stale / already_in_position / below confidence threshold; first actionable signal executes

## ML Pipeline

```
Historical signals (BUY/SELL with 13 features each)
      │
      ▼
SignalLabelerService        ← simulate TP/SL against forward OHLCV bars
      │                       outcome: 'win' | 'loss' | 'timeout'
      ▼
signal_labels table         ← 9,000+ labeled (grows daily at market close)
      │
      ▼
TrainingDatasetBuilder      ← extract 9-dim feature vector per labeled signal
      │                       rsi_14, bb_pct_b, sma_ratio, bb_width,
      │                       macd, macd_hist, return_1, volatility_5, direction_buy
      ▼
ModelTrainer                ← RandomForest (class_weight='balanced')
      │                       cross-val ROC-AUC, feature importance
      ▼
AlertService                ← sends metrics to Telegram
```

**Current baseline accuracy:** ~40% (limited data diversity). Improves as more market conditions are recorded. Goal: replace the current hand-crafted confidence formula with the model's probability output.

## Database Schema

All time-series tables use TimescaleDB hypertables.

| Table | Purpose |
|---|---|
| `market_data_ohlcv` | Raw OHLCV bars |
| `features` | Computed technical indicators |
| `signals` | Strategy output with direction, confidence, raw feature payload |
| `signal_labels` | ML labels: win/loss/timeout per signal vs forward bars |
| `orders` | All orders with risk decision, SL/TP, fill tracking |
| `fills` | Immutable fill records (idempotent on `order_id`) |
| `trade_outcomes` | Closed trade P&L: entry/exit price, duration, reason, strategy |
| `positions` | Current open positions per environment |
| `portfolio_snapshots` | NAV, cash, pnl_daily (real), drawdown (from peak) time series |
| `kill_switch_events` | Append-only kill switch state log |
| `worker_config` | Live-configurable worker settings (read each cycle) |
| `audit_events` | Full operational audit trail |

## Safety Design

- **Live trading blocked by default** — requires `RAC_LIVE_TRADING_ENABLED=true` + `RAC_TRADING_MODE=live`
- **Kill switch** — append-only event log; last event determines state. Cancels all pending Alpaca orders when activated
- **One-position-per-symbol** — `already_in_position` guard prevents over-concentration from repeated entries
- **Idempotency** — all orders use a SHA-256 key; duplicate signals never produce duplicate orders
- **Reconciliation** — worker never trusts its own memory for fill status; always re-queries Alpaca
- **Portfolio consistency gate** — compares RAC positions vs Alpaca positions before allowing new orders
- **Signal staleness** — signals older than `signal_max_age_seconds` are discarded (handles IEX 15-min delay)
