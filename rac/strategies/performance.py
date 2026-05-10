from decimal import Decimal
from typing import Any, cast

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings


def aggregate_performance(fills: list[dict[str, object]]) -> list[dict[str, object]]:
    """Pure aggregation: group fills by strategy_id and compute P&L totals.

    Each fill dict must have: strategy_id, side ('buy'|'sell'), notional.
    Used by StrategyPerformanceService and directly testable without a DB.
    """
    groups: dict[str, dict[str, object]] = {}
    for f in fills:
        sid = str(f["strategy_id"])
        if sid not in groups:
            groups[sid] = {
                "strategy_id": sid,
                "buys": 0,
                "sells": 0,
                "buy_notional": Decimal("0"),
                "sell_notional": Decimal("0"),
            }
        notional = Decimal(str(f["notional"]))
        if f["side"] == "buy":
            groups[sid]["buys"] = cast(Any, groups[sid]["buys"]) + 1
            groups[sid]["buy_notional"] = Decimal(str(groups[sid]["buy_notional"])) + notional
        else:
            groups[sid]["sells"] = cast(Any, groups[sid]["sells"]) + 1
            groups[sid]["sell_notional"] = Decimal(str(groups[sid]["sell_notional"])) + notional

    result = []
    for row in sorted(groups.values(), key=lambda r: str(r["strategy_id"])):
        buy_n = Decimal(str(row["buy_notional"]))
        sell_n = Decimal(str(row["sell_notional"]))
        result.append({
            "strategy_id": row["strategy_id"],
            "buys": row["buys"],
            "sells": row["sells"],
            "buy_notional": float(buy_n),
            "sell_notional": float(sell_n),
            "realized_pnl": float(sell_n - buy_n),
        })
    return result


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
                        f.side,
                        f.notional
                    FROM fills f
                    JOIN orders o ON o.id = f.order_id
                    WHERE f.environment = %s
                    """,
                    (environment,),
                )
                return aggregate_performance([dict(row) for row in cursor.fetchall()])
