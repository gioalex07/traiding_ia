from typing import Any

from rac.strategies.models import Signal, SignalDirection, StrategyManifest
from rac.strategies.validation import StrategyValidator

TREND_FOLLOWING_MANIFEST = StrategyManifest(
    strategy_id="EQ_TREND_001",
    version="0.2.0",
    required_features=["close", "sma_3", "sma_5", "return_1", "volatility_5"],
    stop_loss_pct=1.5,
    take_profit_pct=3.0,
    max_position_pct=2.0,
    invalidation_rules=[
        "close_crosses_below_sma_5_for_buy",
        "close_crosses_above_sma_5_for_sell",
        "volatility_spike_above_threshold",
    ],
    min_feature_points=5,
)


class TrendFollowingStrategy:
    def __init__(self, manifest: StrategyManifest = TREND_FOLLOWING_MANIFEST) -> None:
        self.manifest = manifest
        self.validator = StrategyValidator()

    def generate(self, features: list[dict[str, Any]], *, environment: str) -> list[Signal]:
        manifest_reasons = self.validator.validate_manifest(self.manifest)
        if manifest_reasons:
            return []

        ordered = sorted(features, key=lambda row: row["time"])
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
            confidence = self._confidence(values)
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
                    raw_payload={
                        "feature_set": row["feature_set"],
                        "values": values,
                    },
                )
            )
        return signals

    @staticmethod
    def _direction(values: dict[str, object]) -> SignalDirection:
        close = float(values["close"])
        sma_3 = float(values["sma_3"])
        sma_5 = float(values["sma_5"])
        return_1 = float(values["return_1"])

        if close > sma_3 > sma_5 and return_1 > 0:
            return SignalDirection.BUY
        if close < sma_3 < sma_5 and return_1 < 0:
            return SignalDirection.SELL
        return SignalDirection.HOLD

    @staticmethod
    def _confidence(values: dict[str, object]) -> float:
        close     = float(values.get("close")       or 0) or 1.0
        sma_3     = float(values.get("sma_3")       or 0) or close
        sma_5     = float(values.get("sma_5")       or 0) or close
        vol       = float(values.get("volatility_5") or 0)

        # Normalize price distance and SMA spread relative to price scale.
        # Thresholds tuned for 5-minute bars (0.3% move = meaningful trend).
        price_gap   = abs(close - sma_5) / sma_5 if sma_5 else 0
        sma_spread  = abs(sma_3 - sma_5) / sma_5 if sma_5 else 0
        price_score = min(1.0, price_gap  / 0.003)   # 0.3% gap → score 1
        spread_score = min(1.0, sma_spread / 0.002)  # 0.2% spread → score 1
        vol_penalty = min(0.3, vol * 50)              # cap penalty at 0.3

        return max(0.0, min(1.0, 0.5 + price_score * 0.35 + spread_score * 0.25 - vol_penalty))

