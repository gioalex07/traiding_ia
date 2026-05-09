import unittest
from datetime import UTC, datetime, timedelta

from rac.strategies.models import SignalDirection
from rac.strategies.trend_following import TrendFollowingStrategy


class TrendFollowingStrategyTest(unittest.TestCase):
    def test_generates_buy_signal_when_close_above_moving_averages(self) -> None:
        start = datetime(2026, 5, 9, 16, 0, tzinfo=UTC)
        features = [
            {
                "time": start + timedelta(minutes=index),
                "symbol": "AAPL",
                "timeframe": "1MIN",
                "feature_set": "technical_v1",
                "values": {
                    "close": 100 + index,
                    "sma_3": 99 + index,
                    "sma_5": 98 + index,
                    "return_1": 0.01,
                    "volatility_5": 0.001,
                },
            }
            for index in range(5)
        ]

        signals = TrendFollowingStrategy().generate(features, environment="paper")

        self.assertEqual(len(signals), 5)
        self.assertEqual(signals[-1].direction, SignalDirection.BUY)
        self.assertGreater(signals[-1].confidence, 0)
        self.assertGreater(signals[-1].stop_loss_pct, 0)
        self.assertGreater(signals[-1].take_profit_pct, 0)
        self.assertGreater(signals[-1].max_position_pct, 0)
        self.assertTrue(signals[-1].invalidation_rules)

    def test_does_not_generate_when_required_features_missing(self) -> None:
        start = datetime(2026, 5, 9, 16, 0, tzinfo=UTC)
        features = [
            {
                "time": start + timedelta(minutes=index),
                "symbol": "AAPL",
                "timeframe": "1MIN",
                "feature_set": "technical_v1",
                "values": {
                    "close": 100 + index,
                    "sma_3": 99 + index,
                    "sma_5": 98 + index,
                    "return_1": 0.01,
                    "volatility_5": None,
                },
            }
            for index in range(5)
        ]

        signals = TrendFollowingStrategy().generate(features, environment="paper")

        self.assertEqual(signals, [])


if __name__ == "__main__":
    unittest.main()
