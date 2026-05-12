# Strategies

## How Strategies Work

Each strategy implements `generate(features, environment)` returning a list of `Signal` objects. The worker runs all configured strategies per symbol every cycle; the **first actionable signal wins** (priority order from `RAC_STRATEGIES`).

**One-position-per-symbol rule:** if a BUY signal arrives while a position is already open, the worker skips it (`already_in_position`). This prevents over-concentration from multiple entries.

A `Signal` carries:
- `direction` — BUY / SELL / HOLD
- `confidence` — 0.0 to 1.0 (must exceed `min_signal_confidence` to execute)
- `stop_loss_pct` / `take_profit_pct` — levels set at entry, monitored each cycle
- `max_position_pct` — max % of equity to allocate

Signals older than `signal_max_age_seconds` (default 1200s) are discarded as stale.

> **Note on IEX data delay:** Alpaca's free data feed (IEX) has ~15 minutes of delay. `signal_max_age_seconds=1200` (20 min) accommodates this. For real-time signals, upgrade to Alpaca SIP subscription.

---

## `trend_following_v1`

**Logic:** Buys when short-term price momentum is positive and price is above both fast moving averages.

### Entry conditions (BUY)
- `close > sma_3 > sma_5` — price above both short SMAs in order
- `return_1 > 0` — positive 1-bar return

### Entry conditions (SELL)
- `close < sma_3 < sma_5`
- `return_1 < 0`

### Confidence
Proportional to the magnitude of `return_1` (capped at 1.0).

### Parameters
| Parameter | Value |
|---|---|
| Min feature points | 5 |
| Stop loss | 2% |
| Take profit | 3% |
| Max position | 5% |
| Risk/reward ratio | 1.5 : 1 |

---

## `mean_reversion_v1` (v0.2.0)

**Logic:** Buys into extreme oversold conditions expecting price to revert to the mean. Sells into extreme overbought conditions.

**v0.2.0 change:** Stop loss tightened from 2% → **1%**, take profit widened from 1.5% → **3%**. This corrects the risk/reward to 3:1, requiring only a 25% win rate to break even (vs 57% with the old parameters).

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
- BUY: `0.5 + (rsi_score + bb_score) × 0.25` — deeper oversold = higher confidence
- SELL: mirror formula

### Parameters
| Parameter | Value |
|---|---|
| Min feature points | 20 (full BB-20 period) |
| Stop loss | **1%** |
| Take profit | **3%** |
| Max position | 2% |
| Risk/reward ratio | **3 : 1** |

---

## Strategy Performance

`GET /strategies/performance?environment=paper` returns realized P&L per strategy:

```bash
curl http://localhost:8000/strategies/performance
```

```json
[{
  "strategy_id": "mean_reversion_v1",
  "buys": 3, "sells": 2,
  "buy_notional": 5250.00,
  "sell_notional": 5400.00,
  "realized_pnl": 150.00
}]
```

`GET /trade-outcomes/summary` shows wins, losses, and average P&L per strategy from the `trade_outcomes` table (closed trades with full P&L accounting).

---

## Adding a Strategy

1. Create `rac/strategies/my_strategy.py`:

```python
from rac.strategies.models import Signal, SignalDirection, StrategyManifest

class MyStrategy:
    manifest = StrategyManifest(
        strategy_id="my_strategy_v1",
        version="1.0.0",
        required_features=["close", "rsi_14"],
        stop_loss_pct=1.0,
        take_profit_pct=3.0,   # always aim for TP > SL
        max_position_pct=2.0,
        min_feature_points=20,
    )

    def generate(self, features: list[dict], environment: str) -> list[Signal]:
        ...
```

2. Register in `rac/strategies/service.py` → `_load_strategy`.
3. Add to `RAC_STRATEGIES` in `.env` or via live config.
4. Write tests in `tests/test_my_strategy.py`.

---

## Signal Labeling for ML

The ML pipeline labels historical signals by simulating whether they would have been profitable:

- **win**: price reached TP (entry × 1.03) before SL
- **loss**: price hit SL (entry × 0.99) first
- **timeout**: neither triggered within 200 forward bars

```bash
# Label manually
curl -X POST "http://localhost:8000/ml/label?tp_pct=3.0&sl_pct=1.0&batch_size=2000"

# Check distribution
curl http://localhost:8000/ml/stats
```

Labels accumulate automatically every day at market close. After enough data (weeks/months), the confidence formula can be replaced by the trained model's probability output.
