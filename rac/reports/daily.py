from dataclasses import dataclass, field
from typing import Any

from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository


@dataclass
class DailyReport:
    date: str
    nav: float
    pnl_daily: float
    drawdown_pct: float
    cash: float
    positions: list[dict[str, Any]] = field(default_factory=list)
    fills_today: list[dict[str, Any]] = field(default_factory=list)


class DailyReportService:
    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        order_repository: OrderRepository,
    ) -> None:
        self._portfolio = portfolio_repository
        self._orders = order_repository

    def build(self, environment: str = "paper") -> DailyReport:
        from datetime import UTC, datetime

        snapshot = self._portfolio.latest_snapshot(environment) or {}
        positions = self._portfolio.positions(environment)
        fills = self._orders.fills_today(environment)

        return DailyReport(
            date=datetime.now(UTC).strftime("%Y-%m-%d"),
            nav=float(snapshot.get("nav") or 0),
            pnl_daily=float(snapshot.get("pnl_daily") or 0),
            drawdown_pct=float(snapshot.get("drawdown") or 0),
            cash=float(snapshot.get("cash") or 0),
            positions=[dict(p) for p in positions],
            fills_today=[dict(f) for f in fills],
        )
