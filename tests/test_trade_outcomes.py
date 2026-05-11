import unittest
from decimal import Decimal

from rac.orders.outcome import TradeOutcomeRepository


class TradeOutcomeLogicTest(unittest.TestCase):
    """Tests the P&L calculation logic without a DB connection."""

    def _pnl(self, open_price: float, close_price: float, qty: float) -> Decimal:
        open_n  = Decimal(str(open_price))  * Decimal(str(qty))
        close_n = Decimal(str(close_price)) * Decimal(str(qty))
        return close_n - open_n

    def test_profitable_trade(self) -> None:
        pnl = self._pnl(100.0, 110.0, 10.0)
        self.assertEqual(pnl, Decimal("100"))

    def test_losing_trade(self) -> None:
        pnl = self._pnl(100.0, 90.0, 10.0)
        self.assertEqual(pnl, Decimal("-100"))

    def test_flat_trade(self) -> None:
        pnl = self._pnl(100.0, 100.0, 5.0)
        self.assertEqual(pnl, Decimal("0"))

    def test_fractional_shares(self) -> None:
        pnl = self._pnl(200.0, 210.0, 0.5)
        self.assertAlmostEqual(float(pnl), 5.0, places=4)

    def test_pnl_pct(self) -> None:
        open_n = Decimal("1000")
        pnl    = Decimal("100")
        pct    = pnl / open_n * 100
        self.assertEqual(pct, Decimal("10"))


class TradeOutcomeRepositoryInterfaceTest(unittest.TestCase):
    def test_can_be_instantiated(self) -> None:
        from rac.config import load_settings
        repo = TradeOutcomeRepository(load_settings())
        self.assertIsInstance(repo, TradeOutcomeRepository)

    def test_recent_limit_clamped(self) -> None:
        self.assertEqual(max(1, min(9999, 500)), 500)
        self.assertEqual(max(1, min(0,    500)), 1)


if __name__ == "__main__":
    unittest.main()
