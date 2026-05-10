import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


class StrategyPerformanceService:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def get_performance(self, environment: str = "paper") -> list[dict[str, object]]:
        """Returns realized P&L and fill counts grouped by strategy."""
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        o.strategy_id,
                        COUNT(*) FILTER (WHERE f.side = 'buy')  AS buys,
                        COUNT(*) FILTER (WHERE f.side = 'sell') AS sells,
                        COALESCE(SUM(f.notional) FILTER (WHERE f.side = 'buy'),  0) AS buy_notional,
                        COALESCE(SUM(f.notional) FILTER (WHERE f.side = 'sell'), 0) AS sell_notional,
                        COALESCE(SUM(f.notional) FILTER (WHERE f.side = 'sell'), 0)
                            - COALESCE(SUM(f.notional) FILTER (WHERE f.side = 'buy'), 0)
                            AS realized_pnl
                    FROM fills f
                    JOIN orders o ON o.id = f.order_id
                    WHERE f.environment = %s
                    GROUP BY o.strategy_id
                    ORDER BY o.strategy_id
                    """,
                    (environment,),
                )
                return [dict(row) for row in cursor.fetchall()]
