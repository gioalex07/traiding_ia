from typing import Any

from rac.strategies.models import Signal, SignalDirection, StrategyManifest
from rac.strategies.validation import StrategyValidator

MEAN_REVERSION_MANIFEST = StrategyManifest(
    strategy_id="EQ_REVERSION_001",
    version="0.2.0",
    required_features=["close", "sma_20", "rsi_14", "bb_pct_b"],
    stop_loss_pct=1.0,
    take_profit_pct=2.0,
    max_position_pct=2.0,
    invalidation_rules=[
        "rsi_exits_oversold_for_buy",
        "rsi_exits_overbought_for_sell",
        "bb_pct_b_normalizes",
    ],
    min_feature_points=20,  # necesita 20 barras para BB(20)
)

# Umbrales ajustables por manifest futuro
_RSI_OVERSOLD = 35.0
_RSI_OVERBOUGHT = 65.0
_BB_LOWER = 0.2   # %B por debajo → precio cerca de banda inferior
_BB_UPPER = 0.8   # %B por encima → precio cerca de banda superior


class MeanReversionStrategy:
    def __init__(self, manifest: StrategyManifest = MEAN_REVERSION_MANIFEST) -> None:
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
        rsi = values.get("rsi_14")
        pct_b = values.get("bb_pct_b")
        sma_20 = values.get("sma_20")
        close = values.get("close")

        if any(v is None for v in [rsi, pct_b, sma_20, close]):
            return SignalDirection.HOLD

        rsi_f = float(rsi)
        pct_b_f = float(pct_b)
        close_f = float(close)
        sma_f = float(sma_20)

        # Oversold: RSI bajo + precio cerca de banda inferior + precio bajo SMA
        if rsi_f < _RSI_OVERSOLD and pct_b_f < _BB_LOWER and close_f < sma_f:
            return SignalDirection.BUY

        # Overbought: RSI alto + precio cerca de banda superior + precio sobre SMA
        if rsi_f > _RSI_OVERBOUGHT and pct_b_f > _BB_UPPER and close_f > sma_f:
            return SignalDirection.SELL

        return SignalDirection.HOLD

    @staticmethod
    def _confidence(values: dict[str, Any], direction: SignalDirection) -> float:
        rsi = values.get("rsi_14")
        pct_b = values.get("bb_pct_b")
        if rsi is None or pct_b is None:
            return 0.5

        rsi_f = float(rsi)
        pct_b_f = float(pct_b)

        if direction == SignalDirection.BUY:
            rsi_score = max(0.0, (_RSI_OVERSOLD - rsi_f) / _RSI_OVERSOLD)
            bb_score = max(0.0, (_BB_LOWER - pct_b_f) / _BB_LOWER) if pct_b_f < _BB_LOWER else 0.0
            return max(0.0, min(1.0, 0.5 + (rsi_score + bb_score) * 0.25))

        if direction == SignalDirection.SELL:
            rsi_score = max(0.0, (rsi_f - _RSI_OVERBOUGHT) / (100.0 - _RSI_OVERBOUGHT))
            bb_score = max(0.0, (pct_b_f - _BB_UPPER) / (1.0 - _BB_UPPER)) if pct_b_f > _BB_UPPER else 0.0
            return max(0.0, min(1.0, 0.5 + (rsi_score + bb_score) * 0.25))

        return 0.5
