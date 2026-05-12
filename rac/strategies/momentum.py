from typing import Any

from rac.strategies.models import Signal, SignalDirection, StrategyManifest
from rac.strategies.validation import StrategyValidator

MOMENTUM_MANIFEST = StrategyManifest(
    strategy_id="momentum_v1",
    version="0.1.0",
    required_features=["close", "return_1", "macd", "macd_signal", "macd_hist", "rsi_14"],
    stop_loss_pct=1.5,
    take_profit_pct=4.0,
    max_position_pct=2.0,
    invalidation_rules=[
        "macd_hist_flips_negative_for_buy",
        "macd_hist_flips_positive_for_sell",
        "rsi_leaves_momentum_zone",
    ],
    min_feature_points=35,  # MACD signal line needs 26+9-1 bars
)

# RSI bounds for the "momentum zone"
_RSI_BUY_MIN = 45.0
_RSI_BUY_MAX = 72.0
_RSI_SELL_MIN = 28.0
_RSI_SELL_MAX = 55.0

# Normalized MACD histogram threshold: 0.1% of price = full score
_MACD_HIST_THRESHOLD = 0.001


class MomentumStrategy:
    def __init__(self, manifest: StrategyManifest = MOMENTUM_MANIFEST) -> None:
        self.manifest = manifest
        self.validator = StrategyValidator()

    def generate(self, features: list[dict[str, Any]], *, environment: str) -> list[Signal]:
        if self.validator.validate_manifest(self.manifest):
            return []

        ordered = sorted(features, key=lambda r: r["time"])
        if len(ordered) < self.manifest.min_feature_points:
            return []

        signals: list[Signal] = []
        for row in ordered:
            values = row["values"]
            if not isinstance(values, dict):
                continue
            if self.validator.validate_features(self.manifest, values):
                continue

            direction = self._direction(values)
            confidence = self._confidence(values, direction)
            signals.append(
                Signal(
                    time=row["time"],
                    environment=environment,
                    strategy_id=self.manifest.strategy_id,
                    strategy_version=self.manifest.version,
                    symbol=str(row["symbol"]),
                    timeframe=str(row["timeframe"]),
                    direction=direction,
                    confidence=confidence,
                    stop_loss_pct=self.manifest.stop_loss_pct,
                    take_profit_pct=self.manifest.take_profit_pct,
                    max_position_pct=self.manifest.max_position_pct,
                    invalidation_rules=self.manifest.invalidation_rules,
                    raw_payload={"feature_set": row["feature_set"], "values": values},
                )
            )
        return signals

    @staticmethod
    def _direction(values: dict[str, Any]) -> SignalDirection:
        macd = values.get("macd")
        macd_hist = values.get("macd_hist")
        rsi = values.get("rsi_14")
        return_1 = values.get("return_1")

        if any(v is None for v in [macd, macd_hist, rsi, return_1]):
            return SignalDirection.HOLD

        macd_f = float(macd)
        hist_f = float(macd_hist)
        rsi_f = float(rsi)
        ret_f = float(return_1)

        if hist_f > 0 and macd_f > 0 and _RSI_BUY_MIN <= rsi_f <= _RSI_BUY_MAX and ret_f > 0:
            return SignalDirection.BUY

        if hist_f < 0 and macd_f < 0 and _RSI_SELL_MIN <= rsi_f <= _RSI_SELL_MAX and ret_f < 0:
            return SignalDirection.SELL

        return SignalDirection.HOLD

    @staticmethod
    def _confidence(values: dict[str, Any], direction: SignalDirection) -> float:
        if direction == SignalDirection.HOLD:
            return 0.5

        close = float(values.get("close") or 0) or 1.0
        macd_hist = float(values.get("macd_hist") or 0)
        rsi = float(values.get("rsi_14") or 50)

        # MACD histogram normalized to price — stronger crossover = higher score
        hist_norm = abs(macd_hist) / close
        hist_score = min(1.0, hist_norm / _MACD_HIST_THRESHOLD)

        # RSI score: distance from 50 toward momentum center (60 buy / 40 sell)
        if direction == SignalDirection.BUY:
            rsi_score = max(0.0, (rsi - 50.0) / (_RSI_BUY_MAX - 50.0))
        else:
            rsi_score = max(0.0, (50.0 - rsi) / (50.0 - _RSI_SELL_MIN))

        return max(0.0, min(1.0, 0.5 + hist_score * 0.30 + rsi_score * 0.20))
