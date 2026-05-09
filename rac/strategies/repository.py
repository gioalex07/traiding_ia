import json
from collections.abc import Iterable

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings
from rac.strategies.models import Signal


class SignalRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def insert_signals(self, signals: Iterable[Signal]) -> int:
        rows = list(signals)
        if not rows:
            return 0

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO signals (
                        time,
                        environment,
                        strategy_id,
                        strategy_version,
                        symbol,
                        timeframe,
                        direction,
                        confidence,
                        stop_loss_pct,
                        take_profit_pct,
                        max_position_pct,
                        invalidation_rules,
                        raw_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    [
                        (
                            signal.time,
                            signal.environment,
                            signal.strategy_id,
                            signal.strategy_version,
                            signal.symbol.upper(),
                            signal.timeframe.upper(),
                            signal.direction.value,
                            signal.confidence,
                            signal.stop_loss_pct,
                            signal.take_profit_pct,
                            signal.max_position_pct,
                            json.dumps(signal.invalidation_rules),
                            json.dumps(signal.raw_payload),
                        )
                        for signal in rows
                    ],
                )
            conn.commit()
        return len(rows)

    def latest_signals(self, symbol: str, timeframe: str, limit: int = 100) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        time,
                        environment,
                        strategy_id,
                        strategy_version,
                        symbol,
                        timeframe,
                        direction,
                        confidence,
                        stop_loss_pct,
                        take_profit_pct,
                        max_position_pct,
                        invalidation_rules,
                        raw_payload,
                        created_at
                    FROM signals
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (symbol.upper(), timeframe.upper(), limit),
                )
                return list(cursor.fetchall())

    def get_signal(self, signal_id: str) -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        id,
                        time,
                        environment,
                        strategy_id,
                        strategy_version,
                        symbol,
                        timeframe,
                        direction,
                        confidence,
                        stop_loss_pct,
                        take_profit_pct,
                        max_position_pct,
                        invalidation_rules,
                        raw_payload,
                        created_at
                    FROM signals
                    WHERE id = %s
                    """,
                    (signal_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

