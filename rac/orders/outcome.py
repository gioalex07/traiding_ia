from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


class TradeOutcomeRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def record(
        self,
        *,
        environment: str,
        symbol: str,
        strategy_id: str,
        open_order_id: str,
        close_order_id: str | None,
        open_price: float,
        close_price: float,
        quantity: float,
        close_reason: str,
        opened_at: str,
        closed_at: str,
    ) -> None:
        open_notional  = Decimal(str(open_price))  * Decimal(str(quantity))
        close_notional = Decimal(str(close_price)) * Decimal(str(quantity))
        realized_pnl   = close_notional - open_notional
        pnl_pct        = (realized_pnl / open_notional * 100) if open_notional else Decimal("0")

        from datetime import datetime, timezone
        def _parse(ts: str) -> datetime:
            try:
                return datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                return datetime.now(timezone.utc)

        dt_open  = _parse(opened_at)
        dt_close = _parse(closed_at)
        duration = max(0, int((dt_close - dt_open).total_seconds()))

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO trade_outcomes (
                        environment, symbol, strategy_id,
                        open_order_id, close_order_id,
                        open_price, close_price, quantity,
                        open_notional, close_notional,
                        realized_pnl, pnl_pct,
                        close_reason, opened_at, closed_at, duration_seconds
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        environment, symbol.upper(), strategy_id,
                        open_order_id, close_order_id,
                        open_price, close_price, quantity,
                        open_notional, close_notional,
                        realized_pnl, pnl_pct,
                        close_reason, dt_open, dt_close, duration,
                    ),
                )
            conn.commit()

    def recent(self, environment: str = "paper", limit: int = 20) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, 500))
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, symbol, strategy_id, open_price, close_price,
                           quantity, realized_pnl, pnl_pct, close_reason,
                           opened_at, closed_at, duration_seconds
                    FROM trade_outcomes
                    WHERE environment = %s
                    ORDER BY closed_at DESC
                    LIMIT %s
                    """,
                    (environment, safe_limit),
                )
                return [dict(row) for row in cursor.fetchall()]

    def summary(self, environment: str = "paper") -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        strategy_id,
                        COUNT(*)                                           AS trades,
                        SUM(CASE WHEN realized_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                        SUM(CASE WHEN realized_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                        ROUND(SUM(realized_pnl)::numeric, 2)               AS total_pnl,
                        ROUND(AVG(pnl_pct)::numeric, 3)                    AS avg_pnl_pct,
                        ROUND(AVG(duration_seconds)::numeric, 0)           AS avg_duration_s
                    FROM trade_outcomes
                    WHERE environment = %s
                    GROUP BY strategy_id
                    ORDER BY strategy_id
                    """,
                    (environment,),
                )
                return [dict(row) for row in cursor.fetchall()]
