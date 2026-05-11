import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings
from rac.orders.models import OrderStatus
from rac.risk.models import OrderIntent, RiskDecision


class OrderRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def insert_paper_order(
        self,
        *,
        broker: str,
        order: OrderIntent,
        signal_id: str,
        idempotency_key: str,
        risk_decision: RiskDecision,
        raw_payload: dict[str, Any],
        broker_order_id: str | None = None,
        status: OrderStatus = OrderStatus.PAPER_ACCEPTED,
    ) -> str:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders (
                        environment,
                        status,
                        broker,
                        symbol,
                        side,
                        order_type,
                        quantity,
                        estimated_price,
                        stop_loss_price,
                        take_profit_price,
                        strategy_id,
                        signal_id,
                        idempotency_key,
                        risk_decision,
                        raw_payload,
                        broker_order_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (idempotency_key)
                    DO UPDATE SET raw_payload = orders.raw_payload
                    RETURNING id
                    """,
                    (
                        order.environment,
                        status.value,
                        broker,
                        order.symbol.upper(),
                        order.side.value,
                        order.order_type.value,
                        order.quantity,
                        order.estimated_price,
                        order.stop_loss_price,
                        order.take_profit_price,
                        order.strategy_id,
                        signal_id,
                        idempotency_key,
                        risk_decision.model_dump_json(),
                        json.dumps(raw_payload, default=str),
                        broker_order_id,
                    ),
                )
                order_id = str(cursor.fetchone()[0])
            conn.commit()
        return order_id

    def latest_filled_buy(self, symbol: str) -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, stop_loss_price, take_profit_price, quantity, estimated_price
                    FROM orders
                    WHERE symbol = %s AND side = 'buy' AND status = 'filled'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (symbol.upper(),),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def has_order_with_idempotency(self, idempotency_key: str) -> bool:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM orders WHERE idempotency_key = %s LIMIT 1",
                    (idempotency_key,),
                )
                return cursor.fetchone() is not None

    def insert_close_order(
        self,
        *,
        symbol: str,
        environment: str,
        quantity: float,
        estimated_price: float,
        idempotency_key: str,
        broker_order_id: str,
        parent_order_id: str,
        reason: str,
    ) -> str:
        risk_payload = json.dumps({
            "approved": True, "status": "approved",
            "reasons": [reason], "max_notional_allowed": 0, "requested_notional": 0,
        })
        raw_payload = json.dumps({"mode": "sl_tp_close", "reason": reason, "parent_order_id": parent_order_id})
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO orders (
                        environment, status, broker, symbol, side, order_type,
                        quantity, estimated_price, strategy_id, signal_id,
                        idempotency_key, risk_decision, raw_payload, broker_order_id
                    )
                    VALUES (%s, %s, 'alpaca', %s, 'sell', 'market',
                            %s, %s, 'sl_tp_close', %s::uuid,
                            %s, %s::jsonb, %s::jsonb, %s)
                    ON CONFLICT (idempotency_key) DO UPDATE SET raw_payload = orders.raw_payload
                    RETURNING id
                    """,
                    (
                        environment,
                        OrderStatus.SUBMITTED.value,
                        symbol.upper(),
                        quantity,
                        estimated_price,
                        parent_order_id,
                        idempotency_key,
                        risk_payload,
                        raw_payload,
                        broker_order_id,
                    ),
                )
                order_id = str(cursor.fetchone()[0])
            conn.commit()
        return order_id

    def has_order_for_signal(self, signal_id: str) -> bool:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT 1 FROM orders WHERE signal_id = %s AND status != 'rejected' LIMIT 1",
                    (signal_id,),
                )
                return cursor.fetchone() is not None

    def pending_broker_orders(self) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, environment, symbol, side, quantity, estimated_price,
                           broker_order_id, strategy_id, signal_id, raw_payload, created_at
                    FROM orders
                    WHERE status = 'submitted' AND broker_order_id IS NOT NULL
                    ORDER BY created_at ASC
                    """
                )
                return list(cursor.fetchall())

    def get_by_id(self, order_id: str) -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, environment, symbol, side, strategy_id, signal_id,
                           filled_price, filled_qty, filled_at, estimated_price,
                           quantity, created_at, raw_payload
                    FROM orders WHERE id = %s
                    """,
                    (order_id,),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def latest_filled_buy_full(self, symbol: str, environment: str) -> dict[str, object] | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, strategy_id, filled_price, filled_qty, created_at, filled_at
                    FROM orders
                    WHERE symbol = %s AND environment = %s
                      AND side = 'buy' AND status = 'filled'
                    ORDER BY filled_at DESC LIMIT 1
                    """,
                    (symbol.upper(), environment),
                )
                row = cursor.fetchone()
                return dict(row) if row else None

    def mark_filled(
        self,
        *,
        order_id: str,
        filled_price: float,
        filled_qty: float,
        filled_at: str,
    ) -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orders
                    SET status = %s, filled_price = %s, filled_qty = %s, filled_at = %s
                    WHERE id = %s AND status = 'submitted'
                    """,
                    (OrderStatus.FILLED.value, filled_price, filled_qty, filled_at, order_id),
                )
            conn.commit()

    def mark_cancelled(self, order_id: str, reason: str) -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE orders
                    SET status = %s
                    WHERE id = %s AND status = 'submitted'
                    """,
                    (OrderStatus.CANCELLED.value, order_id),
                )
            conn.commit()

    def recent_fills(self, days: int = 7, environment: str = "paper") -> list[dict[str, object]]:
        safe_days = max(1, min(days, 90))
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT symbol, side, quantity, price, notional, created_at
                    FROM fills
                    WHERE environment = %s
                      AND created_at >= now() - INTERVAL '1 day' * %s
                    ORDER BY created_at DESC
                    """,
                    (environment, safe_days),
                )
                return [dict(row) for row in cursor.fetchall()]

    def fills_today(self, environment: str = "paper") -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT symbol, side, quantity, price, notional, created_at
                    FROM fills
                    WHERE environment = %s AND created_at::date = now()::date
                    ORDER BY created_at DESC
                    """,
                    (environment,),
                )
                return [dict(row) for row in cursor.fetchall()]

    def latest_orders(self, symbol: str | None = None, limit: int = 100) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                if symbol:
                    cursor.execute(
                        """
                        SELECT *
                        FROM orders
                        WHERE symbol = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (symbol.upper(), limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT *
                        FROM orders
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                return list(cursor.fetchall())
