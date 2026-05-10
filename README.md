# RAC - Robo Advisor / Autonomous Capital

RAC is a modular architecture for market analysis, backtesting, paper trading and controlled automated execution. It is designed around risk management, auditability, local AI with Ollama and strict separation between backtesting, paper trading and live trading.

Start with the architecture document:

- [docs/RAC_ARCHITECTURE.md](docs/RAC_ARCHITECTURE.md)

Live trading is blocked by default. The MVP target is Alpaca paper trading.

## Local Run

Start the minimum development stack:

```bash
docker compose --profile dev up -d --build api
```

If this WSL session cannot access the Docker socket directly, use:

```bash
sudo docker compose --profile dev up -d --build api
```

Check status:

```bash
docker compose --profile dev ps
```

API endpoints:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
curl http://localhost:8000/capabilities
```

Open the local admin dashboard:

```text
http://localhost:8000/dashboard
```

The dashboard shows bot state, Alpaca paper account values, RAC portfolio history, latest signals, latest orders, backtests, local AI status and kill-switch controls. It also includes a paper analysis pipeline that fetches market data, computes features, generates signals and optionally explains the latest signal with Ollama. This pipeline does not execute orders.

Check Alpaca paper read-only connectivity:

```bash
curl http://localhost:8000/broker/capabilities
curl http://localhost:8000/broker/account
curl http://localhost:8000/broker/positions
```

Bootstrap the database schema:

```bash
curl -X POST http://localhost:8000/admin/bootstrap
```

Evaluate a simulated paper order through the risk-manager:

```bash
curl -X POST http://localhost:8000/risk/evaluate \
  -H "Content-Type: application/json" \
  -d '{
    "order": {
      "environment": "paper",
      "symbol": "AAPL",
      "side": "buy",
      "order_type": "limit",
      "quantity": 1,
      "estimated_price": 100,
      "stop_loss_price": 95,
      "take_profit_price": 110,
      "strategy_id": "trend",
      "signal_id": "sig-1"
    },
    "portfolio": {
      "equity": 10000,
      "cash": 10000
    }
  }'
```

Ingest a validated OHLCV bar:

```bash
curl -X POST http://localhost:8000/market-data/ohlcv \
  -H "Content-Type: application/json" \
  -d '{
    "bars": [
      {
        "time": "2026-05-09T16:00:00Z",
        "broker": "alpaca",
        "symbol": "AAPL",
        "timeframe": "1Min",
        "open": 100,
        "high": 101,
        "low": 99,
        "close": 100.5,
        "volume": 12345
      }
    ]
  }'
```

Read latest bars:

```bash
curl "http://localhost:8000/market-data/ohlcv/AAPL/1MIN?limit=5"
```

Compute and read technical features:

```bash
curl -X POST http://localhost:8000/features/compute \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","timeframe":"1MIN","limit":100}'

curl "http://localhost:8000/features/AAPL/1MIN?limit=5"
```

Generate and read strategy signals:

```bash
curl -X POST http://localhost:8000/signals/generate \
  -H "Content-Type: application/json" \
  -d '{"symbol":"AAPL","timeframe":"1MIN","strategy_id":"trend_following_v1","limit":100}'

curl "http://localhost:8000/signals/AAPL/1MIN?limit=5"
```

Execute a signal in paper-only mode:

```bash
SIGNAL_ID="<signal uuid from /signals/AAPL/1MIN>"

curl -X POST http://localhost:8000/orders/execute-signal \
  -H "Content-Type: application/json" \
  -d "{
    \"signal_id\": \"${SIGNAL_ID}\",
    \"portfolio_equity\": 10000,
    \"portfolio_cash\": 10000
  }"

curl "http://localhost:8000/orders?symbol=AAPL&limit=5"
curl -X POST "http://localhost:8000/orders/reconcile"
```

Inspect paper portfolio:

```bash
curl "http://localhost:8000/portfolio/positions?environment=paper"
curl "http://localhost:8000/portfolio/snapshot?environment=paper"
curl "http://localhost:8000/portfolio/history?environment=paper&limit=100"
curl -X POST "http://localhost:8000/portfolio/mark-to-market?environment=paper&timeframe=1Day"
```

Run the read-only paper analysis pipeline:

```bash
curl -X POST http://localhost:8000/pipeline/paper/run \
  -H "Content-Type: application/json" \
  -d '{
    "symbol": "AAPL",
    "timeframe": "1Day",
    "start": "2025-04-01T00:00:00Z",
    "end": "2025-05-01T23:59:59Z",
    "strategy_id": "trend_following_v1",
    "feature_set": "technical_v1",
    "limit": 300,
    "explain": false
  }'
```

Inspect local AI and explain a signal with Ollama when available:

```bash
curl "http://localhost:8000/ai/capabilities"

curl -X POST http://localhost:8000/ai/explain-signal \
  -H "Content-Type: application/json" \
  -d "{\"signal_id\": \"${SIGNAL_ID}\"}"
```

Run unit tests inside the API image:

```bash
docker run --rm -v "$PWD/tests:/app/tests:ro" rac/api:dev \
  python -m unittest discover -s /app/tests
```
