import unittest
from datetime import UTC, datetime
from uuid import uuid4

from rac.config import load_settings
from rac.orders.executor import PaperOrderExecutor
from rac.orders.models import ExecuteSignalRequest, OrderStatus
from rac.risk.manager import RiskManager


class FakeSignalRepository:
    def __init__(self, signal: dict[str, object] | None) -> None:
        self.signal = signal

    def get_signal(self, signal_id: str) -> dict[str, object] | None:
        return self.signal


class FakeOrderRepository:
    def __init__(self) -> None:
        self.inserted = []

    def insert_paper_order(self, **kwargs: object) -> str:
        self.inserted.append(kwargs)
        return "order-1"


class FakePortfolioRepository:
    def __init__(self) -> None:
        self.fills = []

    def apply_paper_fill(self, **kwargs: object) -> None:
        self.fills.append(kwargs)


class PaperOrderExecutorTest(unittest.IsolatedAsyncioTestCase):
    async def test_executes_buy_signal_after_risk_approval(self) -> None:
        signal_id = str(uuid4())
        signal = {
            "id": signal_id,
            "time": datetime.now(UTC),
            "environment": "paper",
            "strategy_id": "EQ_TREND_001",
            "strategy_version": "0.1.0",
            "symbol": "AAPL",
            "timeframe": "1MIN",
            "direction": "buy",
            "confidence": 0.6,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
            "max_position_pct": 2.0,
            "invalidation_rules": ["close_crosses_below_sma_5_for_buy"],
            "raw_payload": {"values": {"close": 100}},
        }
        order_repository = FakeOrderRepository()
        portfolio_repository = FakePortfolioRepository()
        executor = PaperOrderExecutor(
            settings=load_settings(),
            signal_repository=FakeSignalRepository(signal),
            order_repository=order_repository,
            portfolio_repository=portfolio_repository,
            risk_manager=RiskManager(load_settings()),
        )

        result = await executor.execute_signal(
            ExecuteSignalRequest(signal_id=signal_id, portfolio_equity=10_000, portfolio_cash=10_000)
        )

        self.assertEqual(result.status, OrderStatus.PAPER_ACCEPTED)
        self.assertEqual(result.order_id, "order-1")
        self.assertEqual(len(order_repository.inserted), 1)
        self.assertEqual(len(portfolio_repository.fills), 1)

    async def test_rejects_hold_signal(self) -> None:
        signal_id = str(uuid4())
        signal = {
            "id": signal_id,
            "direction": "hold",
        }
        executor = PaperOrderExecutor(
            settings=load_settings(),
            signal_repository=FakeSignalRepository(signal),
            order_repository=FakeOrderRepository(),
            portfolio_repository=FakePortfolioRepository(),
            risk_manager=RiskManager(load_settings()),
        )

        result = await executor.execute_signal(
            ExecuteSignalRequest(signal_id=signal_id, portfolio_equity=10_000, portfolio_cash=10_000)
        )

        self.assertEqual(result.status, OrderStatus.REJECTED)
        self.assertEqual(result.reason, "hold_signal")

    async def test_rejects_when_kill_switch_is_active(self) -> None:
        signal_id = str(uuid4())
        signal = {
            "id": signal_id,
            "time": datetime.now(UTC),
            "environment": "paper",
            "strategy_id": "EQ_TREND_001",
            "strategy_version": "0.1.0",
            "symbol": "AAPL",
            "timeframe": "1MIN",
            "direction": "buy",
            "confidence": 0.6,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
            "max_position_pct": 2.0,
            "invalidation_rules": ["close_crosses_below_sma_5_for_buy"],
            "raw_payload": {"values": {"close": 100}},
        }
        order_repository = FakeOrderRepository()
        portfolio_repository = FakePortfolioRepository()
        executor = PaperOrderExecutor(
            settings=load_settings(),
            signal_repository=FakeSignalRepository(signal),
            order_repository=order_repository,
            portfolio_repository=portfolio_repository,
            risk_manager=RiskManager(load_settings()),
        )

        result = await executor.execute_signal(
            ExecuteSignalRequest(
                signal_id=signal_id,
                portfolio_equity=10_000,
                portfolio_cash=10_000,
                kill_switch_active=True,
            )
        )

        self.assertEqual(result.status, OrderStatus.REJECTED)
        self.assertEqual(result.reason, "risk_rejected")
        self.assertIn("kill_switch_active", result.risk_decision.reasons)
        self.assertEqual(len(order_repository.inserted), 0)
        self.assertEqual(len(portfolio_repository.fills), 0)


if __name__ == "__main__":
    unittest.main()
