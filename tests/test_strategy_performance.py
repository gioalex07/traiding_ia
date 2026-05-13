import unittest

from rac.strategies.performance import aggregate_performance


class AggregatePerformanceTest(unittest.TestCase):
    def test_empty_fills_returns_empty(self) -> None:
        self.assertEqual(aggregate_performance([]), [])

    def test_single_buy_no_sell(self) -> None:
        fills = [{"strategy_id": "EQ_TREND_001", "side": "buy", "notional": "1750.00"}]
        result = aggregate_performance(fills)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["strategy_id"], "EQ_TREND_001")
        self.assertEqual(result[0]["buys"], 1)
        self.assertEqual(result[0]["sells"], 0)
        self.assertAlmostEqual(result[0]["buy_notional"], 1750.0)
        self.assertAlmostEqual(result[0]["sell_notional"], 0.0)
        self.assertAlmostEqual(result[0]["realized_pnl"], -1750.0)

    def test_buy_and_sell_profitable(self) -> None:
        fills = [
            {"strategy_id": "EQ_TREND_001", "side": "buy",  "notional": "1750.00"},
            {"strategy_id": "EQ_TREND_001", "side": "sell", "notional": "1900.00"},
        ]
        result = aggregate_performance(fills)
        self.assertEqual(result[0]["buys"], 1)
        self.assertEqual(result[0]["sells"], 1)
        self.assertAlmostEqual(result[0]["realized_pnl"], 150.0)

    def test_buy_and_sell_loss(self) -> None:
        fills = [
            {"strategy_id": "EQ_REVERSION_001", "side": "buy",  "notional": "2000.00"},
            {"strategy_id": "EQ_REVERSION_001", "side": "sell", "notional": "1800.00"},
        ]
        result = aggregate_performance(fills)
        self.assertAlmostEqual(result[0]["realized_pnl"], -200.0)

    def test_multiple_strategies_sorted(self) -> None:
        fills = [
            {"strategy_id": "EQ_TREND_001", "side": "buy",  "notional": "1000.00"},
            {"strategy_id": "EQ_REVERSION_001",  "side": "buy",  "notional": "500.00"},
        ]
        result = aggregate_performance(fills)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["strategy_id"], "EQ_REVERSION_001")
        self.assertEqual(result[1]["strategy_id"], "EQ_TREND_001")

    def test_multiple_buys_accumulate(self) -> None:
        fills = [
            {"strategy_id": "EQ_TREND_001", "side": "buy", "notional": "1000.00"},
            {"strategy_id": "EQ_TREND_001", "side": "buy", "notional": "2000.00"},
        ]
        result = aggregate_performance(fills)
        self.assertEqual(result[0]["buys"], 2)
        self.assertAlmostEqual(result[0]["buy_notional"], 3000.0)

    def test_flat_trade_zero_pnl(self) -> None:
        fills = [
            {"strategy_id": "EQ_REVERSION_001", "side": "buy",  "notional": "1500.00"},
            {"strategy_id": "EQ_REVERSION_001", "side": "sell", "notional": "1500.00"},
        ]
        result = aggregate_performance(fills)
        self.assertAlmostEqual(result[0]["realized_pnl"], 0.0)


if __name__ == "__main__":
    unittest.main()
