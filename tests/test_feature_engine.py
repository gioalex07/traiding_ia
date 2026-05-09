import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from rac.features.engine import FeatureEngine


class FeatureEngineTest(unittest.TestCase):
    def test_computes_sma_and_returns(self) -> None:
        start = datetime(2026, 5, 9, 16, 0, tzinfo=UTC)
        bars = [
            {
                "time": start + timedelta(minutes=index),
                "symbol": "AAPL",
                "timeframe": "1MIN",
                "close": Decimal(str(100 + index)),
            }
            for index in range(5)
        ]

        points = FeatureEngine().compute_technical_v1(bars)

        self.assertEqual(len(points), 5)
        self.assertIsNone(points[0].values["return_1"])
        self.assertAlmostEqual(points[1].values["return_1"], 0.01)
        self.assertEqual(points[2].values["sma_3"], 101)
        self.assertEqual(points[4].values["sma_5"], 102)
        self.assertIsNotNone(points[4].values["volatility_5"])


if __name__ == "__main__":
    unittest.main()
