from datetime import datetime
from typing import Any

import psycopg
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

from rac.config import Settings


class KillSwitchActivateRequest(BaseModel):
    reason: str = Field(min_length=1)
    actor: str = Field(default="api", min_length=1)


class KillSwitchState(BaseModel):
    active: bool
    activated_at: datetime | None = None
    activated_by: str | None = None
    reason: str | None = None
    event_id: str | None = None


class KillSwitchRepository:
    def __init__(self, settings: Settings) -> None:
        self._url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")
        self._environment = settings.trading_mode.value

    def activate(self, reason: str, actor: str) -> str:
        return self._insert("activate", reason, actor)

    def deactivate(self, reason: str, actor: str) -> str:
        return self._insert("deactivate", reason, actor)

    def is_active(self) -> bool:
        state = self.current_state()
        return state.active

    def current_state(self) -> KillSwitchState:
        with psycopg.connect(self._url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, action, reason, actor, created_at
                    FROM kill_switch_events
                    WHERE environment = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (self._environment,),
                )
                row: dict[str, Any] | None = cursor.fetchone()

        if row is None or row["action"] == "deactivate":
            return KillSwitchState(active=False)

        return KillSwitchState(
            active=True,
            activated_at=row["created_at"],
            activated_by=row["actor"],
            reason=row["reason"],
            event_id=str(row["id"]),
        )

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        with psycopg.connect(self._url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, action, reason, actor, environment, created_at
                    FROM kill_switch_events
                    WHERE environment = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (self._environment, limit),
                )
                return list(cursor.fetchall())

    def _insert(self, action: str, reason: str, actor: str) -> str:
        with psycopg.connect(self._url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO kill_switch_events (action, reason, actor, environment)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id
                    """,
                    (action, reason, actor, self._environment),
                )
                event_id = str(cursor.fetchone()[0])
            conn.commit()
        return event_id
