from collections.abc import Callable
from typing import Any

from rac.admin.kill_switch import KillSwitchRepository
from rac.backtest.repository import BacktestRepository
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.config import Settings
from rac.discovery.service import EnvironmentDiscoveryService
from rac.local_ai.service import LocalAIService
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository
from rac.strategies.repository import SignalRepository


class DashboardService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def snapshot(self) -> dict[str, Any]:
        broker = AlpacaBrokerAdapter(self.settings)
        portfolio = PortfolioRepository(self.settings)
        return {
            "capabilities": self._safe(lambda: EnvironmentDiscoveryService(self.settings).detect().to_dict()),
            "kill_switch": self._safe(lambda: KillSwitchRepository(self.settings).current_state().model_dump()),
            "ai": self._safe(lambda: LocalAIService(self.settings).capabilities().model_dump()),
            "broker_account": await self._safe_async(lambda: broker.get_account()),
            "broker_positions": await self._safe_async(lambda: broker.get_positions()),
            "portfolio_snapshot": self._safe(lambda: portfolio.latest_snapshot("paper") or {}),
            "portfolio_positions": self._safe(lambda: portfolio.positions("paper")),
            "orders": self._safe(lambda: OrderRepository(self.settings).latest_orders(limit=10)),
            "signals": self._safe(lambda: SignalRepository(self.settings).latest_all(limit=10)),
            "backtests": self._safe(lambda: BacktestRepository(self.settings).list_recent(5)),
        }

    @staticmethod
    def _safe(fn: Callable[[], Any]) -> dict[str, Any]:
        try:
            value = fn()
            return {"ok": True, "data": DashboardService._to_plain(value)}
        except Exception as exc:
            return {"ok": False, "error": exc.__class__.__name__}

    @staticmethod
    async def _safe_async(fn: Callable[[], Any]) -> dict[str, Any]:
        try:
            value = await fn()
            return {"ok": True, "data": DashboardService._to_plain(value)}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    @staticmethod
    def _to_plain(value: Any) -> Any:
        if hasattr(value, "__dict__"):
            return {k: DashboardService._to_plain(v) for k, v in value.__dict__.items()}
        if isinstance(value, list):
            return [DashboardService._to_plain(item) for item in value]
        if isinstance(value, dict):
            return {str(k): DashboardService._to_plain(v) for k, v in value.items()}
        return value

