import json

import psycopg
from psycopg.rows import dict_row

from rac.backtest.models import BacktestResult
from rac.config import Settings


class BacktestRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def save(self, result: BacktestResult) -> str:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO backtests (
                        strategy_id, symbol, timeframe, start_time, end_time,
                        initial_cash, final_equity, bars_processed,
                        params, metrics, status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    RETURNING id
                    """,
                    (
                        result.strategy_id,
                        result.symbol,
                        result.timeframe,
                        result.start,
                        result.end,
                        result.initial_cash,
                        result.final_equity,
                        result.bars_processed,
                        json.dumps({"slippage_pct": 0.05, "commission_per_trade": 0.0}),
                        result.metrics.model_dump_json(),
                        result.status,
                    ),
                )
                backtest_id = str(cursor.fetchone()[0])
            conn.commit()
        return backtest_id

    def get(self, backtest_id: str) -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT * FROM backtests WHERE id = %s",
                    (backtest_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def list_recent(self, limit: int = 20) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, strategy_id, symbol, timeframe, start_time, end_time,
                           initial_cash, final_equity, bars_processed, metrics, status, created_at
                    FROM backtests
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(cursor.fetchall())
