#!/usr/bin/env python3
"""Load historical bars, compute features, generate signals, label, retrain.

Usage:
    set -a && source .env && set +a
    python scripts/load_history.py
"""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime, timedelta

BASE = "http://localhost:8000"

TARGETS = [
    # (symbol, timeframe, months_back)
    ("AAPL", "5Min", 6),
    ("MSFT", "5Min", 3),
    ("SPY",  "5Min", 3),
    ("NVDA", "5Min", 3),
    ("QQQ",  "5Min", 3),
    ("TSLA", "5Min", 3),
]

STRATEGIES = ["EQ_TREND_001", "EQ_REVERSION_001", "EQ_MOMENTUM_001"]
LABEL_BATCH = 5000
LABEL_ROUNDS = 20  # up to 100k labels


def api(method: str, path: str, body: dict | None = None) -> dict:
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body else None
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method=method,
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read())


def log(msg: str) -> None:
    print(f"[{datetime.now(UTC).strftime('%H:%M:%S')}] {msg}", flush=True)


def fetch_bars(symbol: str, timeframe: str, months: int) -> None:
    end = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    start = end - timedelta(days=months * 30)
    log(f"Fetching {symbol} {timeframe} from {start.date()} to {end.date()}…")
    try:
        result = api("POST", "/market-data/fetch-historical", {
            "symbol": symbol,
            "timeframe": timeframe,
            "start": start.strftime("%Y-%m-%dT00:00:00Z"),
            "end":   end.strftime("%Y-%m-%dT00:00:00Z"),
        })
        log(f"  → fetched={result.get('fetched',0)} accepted={result.get('accepted',0)} pages={result.get('pages',0)}")
    except urllib.error.HTTPError as e:
        log(f"  ✗ HTTP {e.code}: {e.read().decode()[:200]}")
    except Exception as exc:
        log(f"  ✗ Error: {exc}")


def compute_features(symbol: str, timeframe: str, limit: int = 15_000) -> None:
    log(f"Computing features {symbol} {timeframe} (limit={limit})…")
    try:
        result = api("POST", "/features/compute", {
            "symbol": symbol,
            "timeframe": timeframe,
            "feature_set": "technical_v1",
            "limit": limit,
        })
        log(f"  → computed={result.get('computed',0)}")
    except Exception as exc:
        log(f"  ✗ {exc}")


def generate_signals(symbol: str, timeframe: str, strategy_id: str, limit: int = 15_000) -> None:
    log(f"Generating signals {symbol} {timeframe} {strategy_id}…")
    try:
        result = api("POST", "/signals/generate", {
            "symbol": symbol,
            "timeframe": timeframe,
            "strategy_id": strategy_id,
            "feature_set": "technical_v1",
            "limit": limit,
        })
        log(f"  → generated={result.get('generated',0)}")
    except Exception as exc:
        log(f"  ✗ {exc}")


def label_signals(round_n: int) -> int:
    log(f"Labeling batch {round_n}…")
    try:
        result = api("POST", f"/ml/label?tp_pct=2.0&sl_pct=1.0&batch_size={LABEL_BATCH}")
        labeled = result.get("labeled", 0)
        log(f"  → labeled={labeled} win={result.get('win',0)} loss={result.get('loss',0)} skipped={result.get('skipped',0)}")
        return labeled
    except Exception as exc:
        log(f"  ✗ {exc}")
        return 0


def retrain() -> None:
    log("Training ML model…")
    try:
        result = api("POST", "/ml/train?n_estimators=200")
        if "error" in result:
            log(f"  ✗ {result['error']}")
            return
        log(
            f"  → samples={result.get('samples_train',0)+result.get('samples_test',0)}"
            f" accuracy={result.get('accuracy',0):.3f}"
            f" roc_auc={result.get('cv_roc_auc_mean',0):.3f}"
            f" win_rate={result.get('win_rate_pct',0):.1f}%"
        )
        fi = result.get("feature_importance", {})
        top = list(fi.items())[:3]
        log(f"  Top features: " + " · ".join(f"{k}={v:.3f}" for k, v in top))
    except Exception as exc:
        log(f"  ✗ {exc}")


def main() -> None:
    log("=== RAC Historical Data Loader ===")

    # 1. Fetch bars
    log("\n── Step 1: Fetch historical bars ──")
    for symbol, timeframe, months in TARGETS:
        fetch_bars(symbol, timeframe, months)
        time.sleep(2)  # be kind to Alpaca rate limits

    # 2. Compute features
    log("\n── Step 2: Compute features ──")
    for symbol, timeframe, _ in TARGETS:
        compute_features(symbol, timeframe)

    # 3. Generate signals
    log("\n── Step 3: Generate signals ──")
    for symbol, timeframe, _ in TARGETS:
        for strategy_id in STRATEGIES:
            generate_signals(symbol, timeframe, strategy_id)
            time.sleep(1)

    # 4. Label in batches
    log("\n── Step 4: Label signals ──")
    for i in range(1, LABEL_ROUNDS + 1):
        labeled = label_signals(i)
        if labeled == 0:
            log("  All signals labeled.")
            break
        time.sleep(1)

    # 5. Check ML stats
    log("\n── Step 5: ML stats ──")
    try:
        stats = api("GET", "/ml/stats")
        log(f"  total={stats.get('total',0)} wins={stats.get('wins',0)} losses={stats.get('losses',0)} win_rate={stats.get('win_rate_pct',0)}%")
    except Exception as exc:
        log(f"  ✗ {exc}")

    # 6. Retrain
    log("\n── Step 6: Retrain model ──")
    retrain()

    log("\n=== Done ===")


if __name__ == "__main__":
    main()
