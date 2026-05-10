import json
from typing import Any

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


class AuditRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def record_event(
        self,
        *,
        event_type: str,
        environment: str,
        correlation_id: str,
        actor: str,
        payload: dict[str, Any],
    ) -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events (event_type, environment, correlation_id, actor, payload)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (event_type, environment, correlation_id, actor, json.dumps(payload, default=str)),
                )
            conn.commit()

    def recent_events(
        self,
        *,
        environment: str = "paper",
        event_type: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        safe_limit = max(1, min(limit, 500))
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                if event_type:
                    cursor.execute(
                        """
                        SELECT id, event_type, environment, correlation_id,
                               actor, payload, created_at
                        FROM audit_events
                        WHERE environment = %s AND event_type = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (environment, event_type, safe_limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, event_type, environment, correlation_id,
                               actor, payload, created_at
                        FROM audit_events
                        WHERE environment = %s
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (environment, safe_limit),
                    )
                return [dict(row) for row in cursor.fetchall()]

    def record_risk_decision(self, request: Any, decision: Any) -> None:
        order = request.order
        portfolio = request.portfolio
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO risk_decisions (
                        environment,
                        strategy_id,
                        signal_id,
                        symbol,
                        decision_status,
                        approved,
                        reasons,
                        requested_notional,
                        max_notional_allowed,
                        order_payload,
                        portfolio_payload
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s::jsonb, %s::jsonb)
                    """,
                    (
                        order.environment,
                        order.strategy_id,
                        order.signal_id,
                        order.symbol,
                        decision.status.value,
                        decision.approved,
                        json.dumps(decision.reasons),
                        decision.requested_notional,
                        decision.max_notional_allowed,
                        order.model_dump_json(),
                        portfolio.model_dump_json(),
                    ),
                )
            conn.commit()
