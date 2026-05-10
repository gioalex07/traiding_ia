from decimal import Decimal

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


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
                cursor.execute(
                    """
                    INSERT INTO portfolio_snapshots (
                        time, environment, nav, cash, pnl_daily, drawdown, exposure
                    )
                    VALUES (now(), %s, %s, %s, 0, 0, %s::jsonb)
                    """,
                    (
                        environment,
                        nav,
                        cash,
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
