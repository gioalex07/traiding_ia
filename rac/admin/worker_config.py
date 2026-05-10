import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


class WorkerConfigRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def get(self, key: str) -> str | None:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT value FROM worker_config WHERE key = %s", (key,))
                row = cursor.fetchone()
                return str(row["value"]) if row else None

    def all(self) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT key, value, updated_at, updated_by FROM worker_config ORDER BY key"
                )
                return [dict(row) for row in cursor.fetchall()]

    def set(self, key: str, value: str, actor: str = "api") -> None:
        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO worker_config (key, value, updated_at, updated_by)
                    VALUES (%s, %s, now(), %s)
                    ON CONFLICT (key) DO UPDATE
                        SET value = EXCLUDED.value,
                            updated_at = EXCLUDED.updated_at,
                            updated_by = EXCLUDED.updated_by
                    """,
                    (key, value, actor),
                )
            conn.commit()

    def effective_confidence(self, env_default: float) -> float:
        raw = self.get("min_signal_confidence")
        if raw is None:
            return env_default
        try:
            val = float(raw)
            return max(0.0, min(1.0, val))
        except ValueError:
            return env_default

    def effective_symbols(self, env_default: tuple[str, ...]) -> tuple[str, ...]:
        raw = self.get("watched_symbols")
        if not raw:
            return env_default
        symbols = tuple(s.strip().upper() for s in raw.split(",") if s.strip())
        return symbols if symbols else env_default
