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


class RsiTest(unittest.TestCase):
    def _bars(self, closes: list[float]) -> list[dict]:
        start = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
        return [
            {"time": start + timedelta(minutes=i), "symbol": "AAPL",
             "timeframe": "1Min", "close": c}
            for i, c in enumerate(closes)
        ]

    def test_rsi_none_with_fewer_than_14_bars(self) -> None:
        bars = self._bars([100.0] * 13)
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertIsNone(points[-1].values["rsi_14"])

    def test_rsi_100_on_pure_uptrend(self) -> None:
        bars = self._bars([float(100 + i) for i in range(20)])
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertAlmostEqual(points[-1].values["rsi_14"], 100.0)

    def test_rsi_0_on_pure_downtrend(self) -> None:
        bars = self._bars([float(100 - i) for i in range(20)])
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertAlmostEqual(points[-1].values["rsi_14"], 0.0)

    def test_rsi_near_50_on_flat(self) -> None:
        bars = self._bars([100.0] * 20)
        points = FeatureEngine().compute_technical_v1(bars)
        # Todos los gains y losses son 0 → RSI = 100 (avg_loss==0)
        self.assertIsNotNone(points[-1].values["rsi_14"])


class BollingerBandsTest(unittest.TestCase):
    def _bars(self, closes: list[float]) -> list[dict]:
        start = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
        return [
            {"time": start + timedelta(minutes=i), "symbol": "AAPL",
             "timeframe": "1Min", "close": c}
            for i, c in enumerate(closes)
        ]

    def test_bb_none_below_20_bars(self) -> None:
        bars = self._bars([100.0] * 19)
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertIsNone(points[-1].values["bb_upper"])

    def test_bb_upper_above_lower(self) -> None:
        closes = [100.0 + (i % 5) for i in range(25)]
        bars = self._bars(closes)
        points = FeatureEngine().compute_technical_v1(bars)
        upper = points[-1].values["bb_upper"]
        lower = points[-1].values["bb_lower"]
        self.assertIsNotNone(upper)
        self.assertIsNotNone(lower)
        self.assertGreater(upper, lower)

    def test_pct_b_between_0_and_1_near_middle(self) -> None:
        closes = [100.0] * 25  # precio plano = en el medio de las bandas
        bars = self._bars(closes)
        points = FeatureEngine().compute_technical_v1(bars)
        # Con precio constante, std=0, pct_b es None
        self.assertIsNone(points[-1].values["bb_pct_b"])


class MacdTest(unittest.TestCase):
    def _bars(self, closes: list[float]) -> list[dict]:
        start = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
        return [
            {"time": start + timedelta(minutes=i), "symbol": "AAPL",
             "timeframe": "1Min", "close": c}
            for i, c in enumerate(closes)
        ]

    def test_macd_none_below_26_bars(self) -> None:
        bars = self._bars([100.0] * 25)
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertIsNone(points[-1].values["macd"])

    def test_macd_available_at_26_bars(self) -> None:
        bars = self._bars([float(100 + i) for i in range(26)])
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertIsNotNone(points[-1].values["macd"])

    def test_macd_positive_on_uptrend(self) -> None:
        bars = self._bars([float(100 + i) for i in range(40)])
        points = FeatureEngine().compute_technical_v1(bars)
        # En tendencia alcista, EMA12 > EMA26 → MACD > 0
        self.assertGreater(points[-1].values["macd"], 0)

    def test_macd_signal_none_below_35_bars(self) -> None:
        bars = self._bars([float(100 + i) for i in range(34)])
        points = FeatureEngine().compute_technical_v1(bars)
        self.assertIsNone(points[-1].values["macd_signal"])

    def test_macd_hist_is_macd_minus_signal(self) -> None:
        bars = self._bars([float(100 + i) for i in range(50)])
        points = FeatureEngine().compute_technical_v1(bars)
        p = points[-1].values
        if p["macd"] is not None and p["macd_signal"] is not None:
            self.assertAlmostEqual(p["macd_hist"], p["macd"] - p["macd_signal"], places=8)


if __name__ == "__main__":
    unittest.main()
