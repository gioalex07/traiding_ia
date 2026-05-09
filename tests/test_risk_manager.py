import unittest

from rac.config import load_settings
from rac.risk.manager import RiskManager
from rac.risk.models import OrderIntent, PortfolioState, RiskEvaluationRequest


class RiskManagerTest(unittest.TestCase):
    def test_rejects_order_without_stop_and_take_profit(self) -> None:
        request = RiskEvaluationRequest(
            order=OrderIntent(
                symbol="AAPL",
                side="buy",
                order_type="market",
                quantity=1,
                estimated_price=100,
                strategy_id="test",
                signal_id="sig-1",
            ),
            portfolio=PortfolioState(equity=10_000, cash=10_000),
        )

        decision = RiskManager(load_settings()).evaluate(request)

        self.assertFalse(decision.approved)
        self.assertIn("missing_stop_loss", decision.reasons)
        self.assertIn("missing_take_profit", decision.reasons)

    def test_approves_bounded_paper_order(self) -> None:
        request = RiskEvaluationRequest(
            order=OrderIntent(
                symbol="AAPL",
                side="buy",
                order_type="limit",
                quantity=1,
                estimated_price=100,
                stop_loss_price=95,
                take_profit_price=110,
                strategy_id="test",
                signal_id="sig-2",
            ),
            portfolio=PortfolioState(equity=10_000, cash=10_000),
        )

        decision = RiskManager(load_settings()).evaluate(request)

        self.assertTrue(decision.approved)
        self.assertEqual(decision.reasons, [])


if __name__ == "__main__":
    unittest.main()
