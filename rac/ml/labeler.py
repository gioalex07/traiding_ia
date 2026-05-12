"""Signal labeling — determines outcome of each historical signal.

Pure label_signal() function is testable without DB.
SignalLabelerService handles the DB integration.
"""
import logging
from typing import Any

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings

log = logging.getLogger("rac.ml.labeler")


def label_signal(
    entry_price: float,
    direction: str,
    forward_bars: list[dict[str, Any]],
    tp_pct: float = 3.0,
    sl_pct: float = 1.0,
    max_bars: int = 200,
) -> dict[str, Any]:
    """Label a signal by simulating it against forward price bars.

    Returns: outcome ('win'|'loss'|'timeout'), exit_bars, pnl_pct.
    """
    if entry_price <= 0 or not forward_bars:
        return {"outcome": "timeout", "exit_bars": 0, "pnl_pct": 0.0}

    bars = forward_bars[:max_bars]

    if direction == "buy":
        tp = entry_price * (1 + tp_pct / 100)
        sl = entry_price * (1 - sl_pct / 100)
        for i, bar in enumerate(bars):
            if float(bar["high"]) >= tp:
                return {"outcome": "win",  "exit_bars": i + 1, "pnl_pct": tp_pct}
            if float(bar["low"])  <= sl:
                return {"outcome": "loss", "exit_bars": i + 1, "pnl_pct": -sl_pct}

    elif direction == "sell":
        tp = entry_price * (1 - tp_pct / 100)
        sl = entry_price * (1 + sl_pct / 100)
        for i, bar in enumerate(bars):
            if float(bar["low"])  <= tp:
                return {"outcome": "win",  "exit_bars": i + 1, "pnl_pct": tp_pct}
            if float(bar["high"]) >= sl:
                return {"outcome": "loss", "exit_bars": i + 1, "pnl_pct": -sl_pct}

    last_price = float(bars[-1]["close"])
    raw_pnl = (last_price - entry_price) / entry_price * 100
    pnl = raw_pnl if direction == "buy" else -raw_pnl
    return {"outcome": "timeout", "exit_bars": len(bars), "pnl_pct": round(pnl, 4)}


class SignalLabelerService:
    """Labels historical signals by checking forward OHLCV bars."""

    def __init__(self, settings: Settings) -> None:
        self._db = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def run(
        self,
        tp_pct: float = 3.0,
        sl_pct: float = 1.0,
        max_bars: int = 200,
        batch_size: int = 500,
    ) -> dict[str, int]:
        """Label all unlabeled actionable signals. Returns counts."""
        counts = {"labeled": 0, "skipped": 0, "win": 0, "loss": 0, "timeout": 0}

        with psycopg.connect(self._db, row_factory=dict_row) as conn:
            # Signals that have forward bars and aren't labeled yet
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT s.id, s.symbol, s.timeframe, s.direction,
                           (s.raw_payload->'values'->>'close')::numeric AS entry_price,
                           s.time
                    FROM signals s
                    WHERE s.direction != 'hold'
                      AND s.raw_payload->'values'->>'close' IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1 FROM signal_labels sl WHERE sl.signal_id = s.id
                      )
                    ORDER BY s.time
                    LIMIT %s
                    """,
                    (batch_size,),
                )
                signals = list(cur.fetchall())

            log.info("labeling %d signals tp=%.1f%% sl=%.1f%%", len(signals), tp_pct, sl_pct)

            for sig in signals:
                entry = float(sig["entry_price"] or 0)
                if entry <= 0:
                    counts["skipped"] += 1
                    continue

                # Get forward bars
                with conn.cursor(row_factory=dict_row) as cur2:
                    cur2.execute(
                        """
                        SELECT high, low, close FROM market_data_ohlcv
                        WHERE symbol = %s AND timeframe = %s AND time > %s
                        ORDER BY time ASC LIMIT %s
                        """,
                        (sig["symbol"], sig["timeframe"], sig["time"], max_bars),
                    )
                    forward = list(cur2.fetchall())

                if not forward:
                    counts["skipped"] += 1
                    continue

                result = label_signal(entry, str(sig["direction"]), forward, tp_pct, sl_pct, max_bars)

                with conn.cursor() as cur3:
                    cur3.execute(
                        """
                        INSERT INTO signal_labels
                            (signal_id, symbol, timeframe, direction,
                             entry_price, outcome, exit_bars, pnl_pct, tp_pct, sl_pct)
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ON CONFLICT (signal_id) DO NOTHING
                        """,
                        (
                            sig["id"], sig["symbol"], sig["timeframe"], sig["direction"],
                            entry, result["outcome"], result["exit_bars"],
                            result["pnl_pct"], tp_pct, sl_pct,
                        ),
                    )
                counts["labeled"] += 1
                counts[result["outcome"]] += 1

            conn.commit()

        log.info("labeling done: %s", counts)
        return counts

    def stats(self) -> dict[str, Any]:
        with psycopg.connect(self._db, row_factory=dict_row) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        COUNT(*)                                              AS total,
                        SUM(CASE WHEN outcome='win'     THEN 1 ELSE 0 END)   AS wins,
                        SUM(CASE WHEN outcome='loss'    THEN 1 ELSE 0 END)   AS losses,
                        SUM(CASE WHEN outcome='timeout' THEN 1 ELSE 0 END)   AS timeouts,
                        ROUND(AVG(CASE WHEN outcome='win' THEN 1.0 ELSE 0 END)*100,1)
                                                                              AS win_rate_pct,
                        ROUND(AVG(pnl_pct)::numeric,3)                       AS avg_pnl_pct
                    FROM signal_labels
                    """
                )
                row = dict(cur.fetchone())

                cur.execute(
                    """
                    SELECT symbol, direction, outcome, COUNT(*) AS n,
                           ROUND(AVG(pnl_pct)::numeric,3) AS avg_pnl
                    FROM signal_labels
                    GROUP BY symbol, direction, outcome
                    ORDER BY symbol, direction, outcome
                    """
                )
                breakdown = [dict(r) for r in cur.fetchall()]
                row["breakdown"] = breakdown
                return row
