import json
from decimal import Decimal
from typing import Any

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


def _drawdown_pct(cursor: Any, environment: str, current_nav: Decimal) -> Decimal:
    """Returns current drawdown % from the all-time NAV peak (0 at new highs)."""
    cursor.execute(
        """
        SELECT COALESCE(MAX(nav), 0)
        FROM portfolio_snapshots
        WHERE environment = %s
        """,
        (environment,),
    )
    row = cursor.fetchone()
    peak = Decimal(str(row[0])) if row and row[0] else Decimal("0")
    if peak <= 0:
        return Decimal("0")
    return max(Decimal("0"), (peak - current_nav) / peak * Decimal("100"))


def _daily_pnl(cursor: Any, environment: str, current_nav: Decimal) -> Decimal:
    """Returns today's P&L vs the last snapshot recorded before today (UTC midnight)."""
    cursor.execute(
        """
        SELECT nav FROM portfolio_snapshots
        WHERE environment = %s
          AND time < now()::date
        ORDER BY time DESC
        LIMIT 1
        """,
        (environment,),
    )
    row = cursor.fetchone()
    if row is None:
        return Decimal("0")
    return current_nav - Decimal(str(row[0]))


class PortfolioRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def apply_paper_fill(
        self,
        *,
        environment: str,
        order_id: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        starting_cash: float,
    ) -> None:
        signed_quantity = Decimal(str(quantity if side == "buy" else -quantity))
        price_decimal = Decimal(str(price))
        notional = abs(signed_quantity) * price_decimal
        cash_delta = -notional if side == "buy" else notional

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO fills (environment, order_id, symbol, side, quantity, price, notional)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (order_id) DO NOTHING
                    RETURNING id
                    """,
                    (environment, order_id, symbol.upper(), side, abs(signed_quantity), price_decimal, notional),
                )
                if cursor.fetchone() is None:
                    conn.commit()
                    return
                cursor.execute(
                    """
                    INSERT INTO positions (environment, symbol, quantity, average_price, market_value)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (environment, symbol)
                    DO UPDATE SET
                        quantity = positions.quantity + EXCLUDED.quantity,
                        average_price = CASE
                            WHEN positions.quantity + EXCLUDED.quantity = 0 THEN 0
                            ELSE (
                                (positions.quantity * positions.average_price)
                                + (EXCLUDED.quantity * EXCLUDED.average_price)
                            ) / NULLIF(positions.quantity + EXCLUDED.quantity, 0)
                        END,
                        market_value = (positions.quantity + EXCLUDED.quantity) * EXCLUDED.average_price,
                        updated_at = now()
                    """,
                    (
                        environment,
                        symbol.upper(),
                        signed_quantity,
                        price_decimal,
                        signed_quantity * price_decimal,
                    ),
                )
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(quantity * average_price), 0)
                    FROM positions
                    WHERE environment = %s
                    """,
                    (environment,),
                )
                positions_value = Decimal(cursor.fetchone()[0])
                cash = Decimal(str(starting_cash)) + cash_delta
                nav = cash + positions_value
                pnl_daily = _daily_pnl(cursor, environment, nav)
                drawdown = _drawdown_pct(cursor, environment, nav)
                cursor.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        time, environment, nav, cash, pnl_daily, drawdown, exposure
                    )
                    VALUES (now(), %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        environment,
                        nav,
                        cash,
                        pnl_daily,
                        drawdown,
                        '{"positions_value": "' + str(positions_value) + '"}',
                    ),
                )
            conn.commit()

    def current_cash(self, environment: str = "paper") -> float:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT cash FROM portfolio_snapshots
                    WHERE environment = %s
                    ORDER BY time DESC LIMIT 1
                    """,
                    (environment,),
                )
                row = cursor.fetchone()
                return float(row["cash"]) if row else 100_000.0

    def latest_snapshot(self, environment: str = "paper") -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT time, environment, nav, cash, pnl_daily, drawdown, exposure
                    FROM portfolio_snapshots
                    WHERE environment = %s
                    ORDER BY time DESC
                    LIMIT 1
                    """,
                    (environment,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def history(self, environment: str = "paper", limit: int = 100) -> list[dict[str, object]]:
        safe_limit = max(1, min(limit, 1000))
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT time, environment, nav, cash, pnl_daily, drawdown, exposure
                    FROM portfolio_snapshots
                    WHERE environment = %s
                    ORDER BY time DESC
                    LIMIT %s
                    """,
                    (environment, safe_limit),
                )
                rows = [dict(row) for row in cursor.fetchall()]
                rows.reverse()
                return rows

    def record_mark_to_market(
        self,
        *,
        environment: str,
        cash: float,
        valuations: list[dict[str, object]],
        errors: list[str],
        source: str,
    ) -> None:
        cash_decimal = Decimal(str(cash))
        positions_value = Decimal("0")
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                for valuation in valuations:
                    market_value = Decimal(str(valuation["market_value"]))
                    positions_value += market_value
                    cursor.execute(
                        """
                        UPDATE positions
                        SET market_value = %s, updated_at = now()
                        WHERE environment = %s AND symbol = %s
                        """,
                        (market_value, environment, str(valuation["symbol"]).upper()),
                    )
                nav = cash_decimal + positions_value
                pnl_daily = _daily_pnl(cursor, environment, nav)
                drawdown = _drawdown_pct(cursor, environment, nav)
                exposure = {
                    "source": source,
                    "positions_value": str(positions_value),
                    "prices": {
                        str(valuation["symbol"]).upper(): str(valuation["latest_price"])
                        for valuation in valuations
                    },
                    "errors": errors,
                }
                cursor.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        time, environment, nav, cash, pnl_daily, drawdown, exposure
                    )
                    VALUES (now(), %s, %s, %s, %s, %s, %s::jsonb)
                    """,
                    (environment, nav, cash_decimal, pnl_daily, drawdown, json.dumps(exposure)),
                )
            conn.commit()

    def peak_nav(self, environment: str = "paper") -> float:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COALESCE(MAX(nav), 0)
                    FROM portfolio_snapshots
                    WHERE environment = %s
                    """,
                    (environment,),
                )
                return float(cursor.fetchone()[0])

    def positions(self, environment: str = "paper") -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT environment, symbol, quantity, average_price, market_value, updated_at
                    FROM positions
                    WHERE environment = %s
                    ORDER BY symbol
                    """,
                    (environment,),
                )
                return list(cursor.fetchall())
