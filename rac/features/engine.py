from decimal import Decimal
from statistics import fmean, pstdev

from rac.features.models import FeaturePoint


class FeatureEngine:
    def compute_technical_v1(
        self,
        bars: list[dict[str, object]],
        *,
        feature_set: str = "technical_v1",
    ) -> list[FeaturePoint]:
        ordered = sorted(bars, key=lambda row: row["time"])
        closes = [self._as_float(row["close"]) for row in ordered]
        points: list[FeaturePoint] = []

        for index, row in enumerate(ordered):
            close = closes[index]
            previous_close = closes[index - 1] if index > 0 else None
            returns_1 = None if previous_close in (None, 0) else (close / previous_close) - 1

            sma_3 = self._sma(closes, index, 3)
            sma_5 = self._sma(closes, index, 5)
            volatility_5 = self._volatility(closes, index, 5)

            points.append(
                FeaturePoint(
                    time=row["time"],
                    symbol=str(row["symbol"]),
                    timeframe=str(row["timeframe"]),
                    feature_set=feature_set,
                    values={
                        "close": close,
                        "return_1": returns_1,
                        "sma_3": sma_3,
                        "sma_5": sma_5,
                        "volatility_5": volatility_5,
                    },
                    source_bar_count=index + 1,
                )
            )

        return points

    @staticmethod
    def _as_float(value: object) -> float:
        if isinstance(value, Decimal):
            return float(value)
        return float(value)

    @staticmethod
    def _sma(values: list[float], index: int, window: int) -> float | None:
        if index + 1 < window:
            return None
        return fmean(values[index + 1 - window : index + 1])

    @staticmethod
    def _volatility(values: list[float], index: int, window: int) -> float | None:
        if index + 1 < window:
            return None
        window_values = values[index + 1 - window : index + 1]
        returns = [
            (window_values[i] / window_values[i - 1]) - 1
            for i in range(1, len(window_values))
            if window_values[i - 1] != 0
        ]
        if len(returns) < 2:
            return None
        return pstdev(returns)

