"""Build training dataset from labeled signals."""
import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings

FEATURE_NAMES = [
    "rsi_14",
    "bb_pct_b",
    "sma_ratio",      # close / sma_20
    "bb_width",       # (bb_upper - bb_lower) / close
    "macd",
    "macd_hist",
    "return_1",
    "volatility_5",
    "direction_buy",  # 1 if buy, 0 if sell
]


def extract_features(values: dict[str, Any], direction: str) -> dict[str, float]:
    """Convert raw feature values from signals.raw_payload into a flat vector."""
    close  = float(values.get("close")  or 0) or 1.0
    sma_20 = float(values.get("sma_20") or 0) or close
    bb_up  = float(values.get("bb_upper") or 0)
    bb_lo  = float(values.get("bb_lower") or 0)

    return {
        "rsi_14":       float(values.get("rsi_14")      or 50),
        "bb_pct_b":     float(values.get("bb_pct_b")    or 0.5),
        "sma_ratio":    close / sma_20,
        "bb_width":     (bb_up - bb_lo) / close if close else 0.0,
        "macd":         float(values.get("macd")        or 0),
        "macd_hist":    float(values.get("macd_hist")   or 0),
        "return_1":     float(values.get("return_1")    or 0),
        "volatility_5": float(values.get("volatility_5") or 0),
        "direction_buy": 1.0 if direction == "buy" else 0.0,
    }


class TrainingDatasetBuilder:
    def __init__(self, settings: Settings) -> None:
        self._db = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def build(
        self,
        include_timeout: bool = False,
        limit: int = 50_000,
    ) -> tuple[list[dict[str, float]], list[int], list[str]]:
        """Returns (X, y, signal_ids).

        y=1 means win (profitable), y=0 means loss.
        Timeouts are excluded by default (ambiguous outcome).
        """
        outcomes_filter = "('win','loss')" if not include_timeout else "('win','loss','timeout')"
        # SPY and MSFT excluded: SPY buy win rate ~4%, MSFT ~8% with TP=2%,
        # both poison the model toward predicting loss for all signals.
        with psycopg.connect(self._db, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT sl.signal_id, sl.direction, sl.outcome,
                           s.raw_payload->'values' AS values
                    FROM signal_labels sl
                    JOIN signals s ON s.id = sl.signal_id
                    WHERE sl.outcome IN {outcomes_filter}
                      AND s.raw_payload->'values' IS NOT NULL
                      AND s.symbol NOT IN ('SPY', 'MSFT')
                    ORDER BY sl.labeled_at
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = list(cur.fetchall())

        X: list[dict[str, float]] = []
        y: list[int] = []
        ids: list[str] = []

        for row in rows:
            values = row["values"]
            if isinstance(values, str):
                values = json.loads(values)
            if not isinstance(values, dict):
                continue
            try:
                features = extract_features(values, str(row["direction"]))
                X.append(features)
                y.append(1 if row["outcome"] == "win" else 0)
                ids.append(str(row["signal_id"]))
            except (TypeError, ValueError):
                continue

        return X, y, ids
