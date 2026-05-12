import unittest

from rac.ml.dataset import FEATURE_NAMES, extract_features
from rac.ml.labeler import label_signal


class LabelSignalTest(unittest.TestCase):

    def _bars(self, highs: list[float], lows: list[float], closes: list[float] | None = None) -> list[dict]:
        closes = closes or highs
        return [{"high": h, "low": lo, "close": c} for h, lo, c in zip(highs, lows, closes)]

    # ── BUY ──────────────────────────────────────────────────────────────

    def test_buy_hits_tp(self) -> None:
        # bar1: low=99.2 (above SL 99.0), bar2: high=104 hits TP 103
        bars = self._bars(highs=[101.0, 104.0], lows=[99.2, 100.0])
        result = label_signal(100.0, "buy", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "win")
        self.assertEqual(result["exit_bars"], 2)
        self.assertAlmostEqual(result["pnl_pct"], 3.0)

    def test_buy_hits_sl(self) -> None:
        bars = self._bars(highs=[100.5, 100.2], lows=[99.0, 98.9])
        result = label_signal(100.0, "buy", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "loss")
        self.assertAlmostEqual(result["pnl_pct"], -1.0)

    def test_buy_timeout_no_bars(self) -> None:
        result = label_signal(100.0, "buy", [], tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "timeout")

    def test_buy_timeout_within_range(self) -> None:
        bars = self._bars(highs=[101.0], lows=[99.5], closes=[100.5])
        result = label_signal(100.0, "buy", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "timeout")
        self.assertAlmostEqual(result["pnl_pct"], 0.5)

    def test_buy_tp_first_bar(self) -> None:
        bars = self._bars(highs=[103.5], lows=[99.0])
        result = label_signal(100.0, "buy", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "win")
        self.assertEqual(result["exit_bars"], 1)

    # ── SELL ─────────────────────────────────────────────────────────────

    def test_sell_hits_tp(self) -> None:
        # bar1: high=100.5 (below SL 101.0), bar2: low=96.5 hits TP 97.0
        bars = self._bars(highs=[100.5, 100.0], lows=[98.0, 96.5])
        result = label_signal(100.0, "sell", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "win")
        self.assertAlmostEqual(result["pnl_pct"], 3.0)

    def test_sell_hits_sl(self) -> None:
        bars = self._bars(highs=[101.5, 102.0], lows=[100.0, 100.5])
        result = label_signal(100.0, "sell", bars, tp_pct=3.0, sl_pct=1.0)
        self.assertEqual(result["outcome"], "loss")
        self.assertAlmostEqual(result["pnl_pct"], -1.0)

    # ── max_bars ─────────────────────────────────────────────────────────

    def test_max_bars_respected(self) -> None:
        bars = self._bars(highs=[101.0] * 300, lows=[99.5] * 300, closes=[100.0] * 300)
        result = label_signal(100.0, "buy", bars, tp_pct=3.0, sl_pct=1.0, max_bars=200)
        self.assertEqual(result["outcome"], "timeout")
        self.assertEqual(result["exit_bars"], 200)


class ExtractFeaturesTest(unittest.TestCase):
    def test_all_feature_names_present(self) -> None:
        values = {
            "rsi_14": 30.0, "bb_pct_b": 0.1, "sma_20": 100.0, "close": 98.0,
            "bb_upper": 102.0, "bb_lower": 96.0, "macd": -0.5,
            "macd_hist": -0.1, "return_1": -0.002, "volatility_5": 0.01,
        }
        features = extract_features(values, "buy")
        for name in FEATURE_NAMES:
            self.assertIn(name, features, f"missing feature: {name}")

    def test_sma_ratio_computed(self) -> None:
        values = {"close": 95.0, "sma_20": 100.0}
        features = extract_features(values, "buy")
        self.assertAlmostEqual(features["sma_ratio"], 0.95)

    def test_direction_buy_encoded(self) -> None:
        features = extract_features({"close": 100.0}, "buy")
        self.assertEqual(features["direction_buy"], 1.0)

    def test_direction_sell_encoded(self) -> None:
        features = extract_features({"close": 100.0}, "sell")
        self.assertEqual(features["direction_buy"], 0.0)

    def test_missing_values_get_defaults(self) -> None:
        features = extract_features({"close": 100.0}, "buy")
        self.assertEqual(features["rsi_14"], 50.0)
        self.assertEqual(features["macd"],   0.0)


if __name__ == "__main__":
    unittest.main()
