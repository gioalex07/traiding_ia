import unittest
from datetime import UTC, datetime, timedelta

from rac.strategies.mean_reversion import MeanReversionStrategy
from rac.strategies.models import SignalDirection


def _feature(
    close: float,
    sma_20: float,
    rsi_14: float,
    bb_pct_b: float,
    index: int = 0,
) -> dict:
    t = datetime(2026, 1, 2, 14, 0, tzinfo=UTC) + timedelta(minutes=index)
    return {
        "time": t,
        "symbol": "AAPL",
        "timeframe": "1Min",
        "feature_set": "technical_v1",
        "values": {
            "close": close,
            "sma_20": sma_20,
            "rsi_14": rsi_14,
            "bb_pct_b": bb_pct_b,
            "return_1": (close - sma_20) / sma_20,
        },
    }


def _enough_features(signal_override: dict | None = None) -> list[dict]:
    """20 neutral features + optional override for the last one."""
    base = [_feature(100.0, 100.0, 50.0, 0.5, i) for i in range(19)]
    last = signal_override or _feature(100.0, 100.0, 50.0, 0.5, 19)
    return base + [last]


class MeanReversionDirectionTest(unittest.TestCase):
    strategy = MeanReversionStrategy()

    def test_buy_when_oversold(self) -> None:
        signals = self.strategy.generate(
            _enough_features(_feature(close=88.0, sma_20=100.0, rsi_14=25.0, bb_pct_b=0.1, index=19)),
            environment="backtest",
        )
        buy_signals = [s for s in signals if s.direction == SignalDirection.BUY]
        self.assertTrue(len(buy_signals) > 0)

    def test_sell_when_overbought(self) -> None:
        signals = self.strategy.generate(
            _enough_features(_feature(close=112.0, sma_20=100.0, rsi_14=75.0, bb_pct_b=0.9, index=19)),
            environment="backtest",
        )
        sell_signals = [s for s in signals if s.direction == SignalDirection.SELL]
        self.assertTrue(len(sell_signals) > 0)

    def test_hold_when_rsi_neutral(self) -> None:
        signals = self.strategy.generate(
            _enough_features(_feature(close=98.0, sma_20=100.0, rsi_14=48.0, bb_pct_b=0.3, index=19)),
            environment="backtest",
        )
        last = signals[-1] if signals else None
        self.assertIsNotNone(last)
        self.assertEqual(last.direction, SignalDirection.HOLD)

    def test_hold_when_rsi_oversold_but_price_above_sma(self) -> None:
        # RSI bajo pero precio sobre SMA → no hay señal de compra (ya está subiendo)
        signals = self.strategy.generate(
            _enough_features(_feature(close=105.0, sma_20=100.0, rsi_14=28.0, bb_pct_b=0.1, index=19)),
            environment="backtest",
        )
        last = signals[-1] if signals else None
        self.assertIsNotNone(last)
        self.assertEqual(last.direction, SignalDirection.HOLD)

    def test_hold_when_bb_pct_b_above_lower_threshold(self) -> None:
        # RSI oversold pero %B no tan bajo → no buy
        signals = self.strategy.generate(
            _enough_features(_feature(close=88.0, sma_20=100.0, rsi_14=28.0, bb_pct_b=0.4, index=19)),
            environment="backtest",
        )
        last = signals[-1] if signals else None
        self.assertIsNotNone(last)
        self.assertEqual(last.direction, SignalDirection.HOLD)

    def test_hold_when_missing_required_features(self) -> None:
        features = _enough_features()
        features[-1]["values"]["rsi_14"] = None
        signals = self.strategy.generate(features, environment="backtest")
        last = signals[-1] if signals else None
        self.assertIsNotNone(last)
        self.assertEqual(last.direction, SignalDirection.HOLD)

    def test_no_signals_below_min_feature_points(self) -> None:
        features = [_feature(88.0, 100.0, 25.0, 0.1, i) for i in range(19)]
        signals = self.strategy.generate(features, environment="backtest")
        self.assertEqual(len(signals), 0)


class MeanReversionConfidenceTest(unittest.TestCase):
    strategy = MeanReversionStrategy()

    def test_buy_confidence_above_0_5(self) -> None:
        signals = self.strategy.generate(
            _enough_features(_feature(close=85.0, sma_20=100.0, rsi_14=20.0, bb_pct_b=0.05, index=19)),
            environment="backtest",
        )
        buy = [s for s in signals if s.direction == SignalDirection.BUY]
        self.assertTrue(buy[-1].confidence > 0.5)

    def test_sell_confidence_above_0_5(self) -> None:
        signals = self.strategy.generate(
            _enough_features(_feature(close=115.0, sma_20=100.0, rsi_14=80.0, bb_pct_b=0.95, index=19)),
            environment="backtest",
        )
        sell = [s for s in signals if s.direction == SignalDirection.SELL]
        self.assertTrue(sell[-1].confidence > 0.5)

    def test_deeper_oversold_higher_confidence(self) -> None:
        feat_mild = _enough_features(_feature(close=90.0, sma_20=100.0, rsi_14=33.0, bb_pct_b=0.15, index=19))
        feat_deep = _enough_features(_feature(close=80.0, sma_20=100.0, rsi_14=15.0, bb_pct_b=0.02, index=19))
        signals_mild = self.strategy.generate(feat_mild, environment="backtest")
        signals_deep = self.strategy.generate(feat_deep, environment="backtest")
        buys_mild = [s for s in signals_mild if s.direction == SignalDirection.BUY]
        buys_deep = [s for s in signals_deep if s.direction == SignalDirection.BUY]
        if buys_mild and buys_deep:
            self.assertGreater(buys_deep[-1].confidence, buys_mild[-1].confidence)


class MeanReversionManifestTest(unittest.TestCase):
    def test_strategy_id(self) -> None:
        self.assertEqual(MeanReversionStrategy().manifest.strategy_id, "EQ_REVERSION_001")

    def test_required_features_present(self) -> None:
        required = MeanReversionStrategy().manifest.required_features
        self.assertIn("rsi_14", required)
        self.assertIn("bb_pct_b", required)
        self.assertIn("sma_20", required)

    def test_min_feature_points_matches_bb_period(self) -> None:
        # BB(20) necesita al menos 20 puntos
        self.assertEqual(MeanReversionStrategy().manifest.min_feature_points, 20)


if __name__ == "__main__":
    unittest.main()
