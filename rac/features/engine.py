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

            points.append(
                FeaturePoint(
                    time=row["time"],
                    symbol=str(row["symbol"]),
                    timeframe=str(row["timeframe"]),
                    feature_set=feature_set,
                    values={
                        "close": close,
                        "return_1": returns_1,
                        "sma_3": self._sma(closes, index, 3),
                        "sma_5": self._sma(closes, index, 5),
                        "sma_20": self._sma(closes, index, 20),
                        "volatility_5": self._volatility(closes, index, 5),
                        "rsi_14": self._rsi(closes, index, 14),
                        "bb_upper": self._bb_upper(closes, index, 20, 2.0),
                        "bb_lower": self._bb_lower(closes, index, 20, 2.0),
                        "bb_pct_b": self._bb_pct_b(closes, index, 20, 2.0),
                        "macd": self._macd(closes, index),
                        "macd_signal": self._macd_signal(closes, index),
                        "macd_hist": self._macd_hist(closes, index),
                    },
                    source_bar_count=index + 1,
                )
            )

        return points

    # ------------------------------------------------------------------
    # RSI (14)
    # ------------------------------------------------------------------
    @classmethod
    def _rsi(cls, closes: list[float], index: int, period: int = 14) -> float | None:
        if index < period:
            return None
        window = closes[index - period + 1 : index + 1]
        gains = [max(window[i] - window[i - 1], 0) for i in range(1, len(window))]
        losses = [max(window[i - 1] - window[i], 0) for i in range(1, len(window))]
        avg_gain = fmean(gains) if gains else 0.0
        avg_loss = fmean(losses) if losses else 0.0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    # ------------------------------------------------------------------
    # Bollinger Bands (20, 2σ)
    # ------------------------------------------------------------------
    @classmethod
    def _bb_middle(cls, closes: list[float], index: int, period: int) -> float | None:
        return cls._sma(closes, index, period)

    @classmethod
    def _bb_std(cls, closes: list[float], index: int, period: int) -> float | None:
        if index + 1 < period:
            return None
        window = closes[index + 1 - period : index + 1]
        return pstdev(window)

    @classmethod
    def _bb_upper(cls, closes: list[float], index: int, period: int, mult: float) -> float | None:
        mid = cls._bb_middle(closes, index, period)
        std = cls._bb_std(closes, index, period)
        return None if mid is None or std is None else mid + mult * std

    @classmethod
    def _bb_lower(cls, closes: list[float], index: int, period: int, mult: float) -> float | None:
        mid = cls._bb_middle(closes, index, period)
        std = cls._bb_std(closes, index, period)
        return None if mid is None or std is None else mid - mult * std

    @classmethod
    def _bb_pct_b(cls, closes: list[float], index: int, period: int, mult: float) -> float | None:
        """Posición del precio dentro de las bandas: 0=lower, 1=upper."""
        upper = cls._bb_upper(closes, index, period, mult)
        lower = cls._bb_lower(closes, index, period, mult)
        if upper is None or lower is None or upper == lower:
            return None
        return (closes[index] - lower) / (upper - lower)

    # ------------------------------------------------------------------
    # MACD (12, 26, 9)
    # ------------------------------------------------------------------
    @staticmethod
    def _ema(closes: list[float], end_index: int, period: int) -> float | None:
        if end_index + 1 < period:
            return None
        window = closes[: end_index + 1]
        k = 2.0 / (period + 1)
        ema = fmean(window[:period])
        for price in window[period:]:
            ema = price * k + ema * (1 - k)
        return ema

    @classmethod
    def _macd(cls, closes: list[float], index: int) -> float | None:
        fast = cls._ema(closes, index, 12)
        slow = cls._ema(closes, index, 26)
        return None if fast is None or slow is None else fast - slow

    @classmethod
    def _macd_signal(cls, closes: list[float], index: int) -> float | None:
        if index < 34:  # 26 + 9 - 1
            return None
        macd_series = [cls._macd(closes, i) for i in range(index - 8, index + 1)]
        if any(v is None for v in macd_series):
            return None
        k = 2.0 / (9 + 1)
        signal = fmean(macd_series[:9])
        for val in macd_series[9:]:
            signal = val * k + signal * (1 - k)
        return signal

    @classmethod
    def _macd_hist(cls, closes: list[float], index: int) -> float | None:
        macd = cls._macd(closes, index)
        sig = cls._macd_signal(closes, index)
        return None if macd is None or sig is None else macd - sig

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
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
