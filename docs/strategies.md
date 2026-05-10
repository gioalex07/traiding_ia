# Strategies

## How Strategies Work

Each strategy implements a `generate(features, environment)` method that receives a list of feature points and returns a list of `Signal` objects. The worker runs all configured strategies per symbol on every cycle; the first strategy that produces an actionable signal (BUY or SELL) wins for that symbol and cycle.

A `Signal` carries:
- `direction` — BUY / SELL / HOLD
- `confidence` — 0.0 to 1.0
- `stop_loss_pct` — % below entry to close on loss
- `take_profit_pct` — % above entry to close on profit
- `max_position_pct` — max % of equity to allocate

Signals older than `_SIGNAL_MAX_AGE_SECONDS` (120s) are discarded by the worker.

---

## `trend_following_v1`

**Logic:** Buys when price shows upward momentum relative to short-term moving averages.

### Entry conditions (BUY)
- `close > sma_3 > sma_5` — price above both short SMAs in order
- `return_1 > 0` — positive 1-bar return

### Entry conditions (SELL)
- `close < sma_3 < sma_5` — price below both short SMAs in order
- `return_1 < 0` — negative 1-bar return

### Confidence
Proportional to the magnitude of `return_1` (capped at 1.0).

### Parameters
| Parameter | Value |
|---|---|
| Min feature points | 5 |
| Stop loss | 2% |
| Take profit | 3% |
| Max position | 5% |

---

## `mean_reversion_v1`

**Logic:** Buys into extreme oversold conditions expecting price to revert to the mean. Sells into extreme overbought conditions.

### Entry conditions (BUY)
All three must be true:
- `rsi_14 < 35` — oversold
- `bb_pct_b < 0.2` — price near the lower Bollinger Band
- `close < sma_20` — price below the 20-period mean

### Entry conditions (SELL)
All three must be true:
- `rsi_14 > 65` — overbought
- `bb_pct_b > 0.8` — price near the upper Bollinger Band
- `close > sma_20` — price above the 20-period mean

### Confidence
- BUY: `(35 - rsi_14)/35 * 0.4 + (0.2 - bb_pct_b)/0.2 * 0.4 + deviation_from_sma * 0.2`
- SELL: mirror formula

### Parameters
| Parameter | Value |
|---|---|
| Min feature points | 20 (full BB-20 period) |
| Stop loss | 2% |
| Take profit | 1.5% |
| Max position | 2% |

---

## Adding a Strategy

1. Create `rac/strategies/my_strategy.py`:

```python
from rac.strategies.models import Signal, SignalDirection, StrategyManifest

class MyStrategy:
    manifest = StrategyManifest(
        strategy_id="my_strategy_v1",
        strategy_version="1.0.0",
        required_features=["close", "sma_20"],
        min_feature_points=20,
    )

    def generate(self, features: list[dict], environment: str) -> list[Signal]:
        ...
```

2. Register in `rac/strategies/service.py` → `_load_strategy`.

3. Add to `RAC_STRATEGIES` in `.env`:
```
RAC_STRATEGIES=trend_following_v1,my_strategy_v1
```

4. Write tests in `tests/test_my_strategy.py` — see `test_mean_reversion_strategy.py` for patterns.

---

## Strategy Performance

The `/strategies/performance` API endpoint returns realized P&L per strategy by joining fills with orders:

```bash
curl http://localhost:8000/strategies/performance?environment=paper
```

Response:
```json
[
  {
    "strategy_id": "trend_following_v1",
    "buys": 3,
    "sells": 2,
    "buy_notional": 5250.00,
    "sell_notional": 5400.00,
    "realized_pnl": 150.00
  }
]
```

Note: `realized_pnl` reflects closed trades only (sell notional minus buy notional). Open positions show unrealized P&L on the portfolio snapshot.
