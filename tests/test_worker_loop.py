import unittest

from rac.brokers.base import Position
from rac.worker.loop import _skip_reason, _sl_tp_trigger


class SkipReasonTest(unittest.TestCase):
    def _pos(self, symbol: str = "AAPL", qty: float = 10.0, value: float = 2000.0) -> Position:
        return Position(symbol=symbol, quantity=qty, market_value=value)

    def test_fresh_buy_without_position_proceeds(self) -> None:
        self.assertIsNone(_skip_reason("buy", age_seconds=30, position=None))

    def test_fresh_buy_with_position_proceeds(self) -> None:
        self.assertIsNone(_skip_reason("buy", age_seconds=30, position=self._pos()))

    def test_fresh_sell_with_position_proceeds(self) -> None:
        self.assertIsNone(_skip_reason("sell", age_seconds=30, position=self._pos()))

    def test_sell_without_position_is_skipped(self) -> None:
        reason = _skip_reason("sell", age_seconds=30, position=None)
        self.assertEqual(reason, "no_position_to_sell")

    def test_stale_signal_is_skipped(self) -> None:
        reason = _skip_reason("buy", age_seconds=300, position=None)
        self.assertIsNotNone(reason)
        self.assertTrue(reason.startswith("stale:"))

    def test_stale_sell_without_position_reports_stale_first(self) -> None:
        # staleness se chequea antes que la posición
        reason = _skip_reason("sell", age_seconds=300, position=None)
        self.assertTrue(reason.startswith("stale:"))

    def test_boundary_exactly_at_max_age_proceeds(self) -> None:
        self.assertIsNone(_skip_reason("buy", age_seconds=120, position=None))

    def test_one_second_over_max_age_is_stale(self) -> None:
        reason = _skip_reason("buy", age_seconds=121, position=None)
        self.assertIsNotNone(reason)


class SlTpTriggerTest(unittest.TestCase):
    def test_no_trigger_within_range(self) -> None:
        self.assertIsNone(_sl_tp_trigger(100.0, stop_loss_price=95.0, take_profit_price=110.0))

    def test_stop_loss_triggered_at_exact_price(self) -> None:
        self.assertEqual(_sl_tp_trigger(95.0, stop_loss_price=95.0, take_profit_price=110.0), "stop_loss")

    def test_stop_loss_triggered_below_price(self) -> None:
        self.assertEqual(_sl_tp_trigger(93.0, stop_loss_price=95.0, take_profit_price=110.0), "stop_loss")

    def test_take_profit_triggered_at_exact_price(self) -> None:
        self.assertEqual(_sl_tp_trigger(110.0, stop_loss_price=95.0, take_profit_price=110.0), "take_profit")

    def test_take_profit_triggered_above_price(self) -> None:
        self.assertEqual(_sl_tp_trigger(115.0, stop_loss_price=95.0, take_profit_price=110.0), "take_profit")

    def test_stop_loss_takes_priority_when_both_would_trigger(self) -> None:
        # precio por debajo de ambos — stop_loss se evalúa primero
        self.assertEqual(_sl_tp_trigger(50.0, stop_loss_price=95.0, take_profit_price=40.0), "stop_loss")

    def test_no_trigger_without_levels(self) -> None:
        self.assertIsNone(_sl_tp_trigger(100.0, stop_loss_price=None, take_profit_price=None))

    def test_only_sl_defined_and_not_triggered(self) -> None:
        self.assertIsNone(_sl_tp_trigger(100.0, stop_loss_price=90.0, take_profit_price=None))

    def test_only_tp_defined_and_triggered(self) -> None:
        self.assertEqual(_sl_tp_trigger(120.0, stop_loss_price=None, take_profit_price=110.0), "take_profit")


if __name__ == "__main__":
    unittest.main()
