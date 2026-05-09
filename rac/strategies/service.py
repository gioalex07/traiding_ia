from rac.config import Settings
from rac.features.repository import FeatureRepository
from rac.strategies.mean_reversion import MeanReversionStrategy
from rac.strategies.models import SignalGenerateRequest, SignalGenerateResult
from rac.strategies.repository import SignalRepository
from rac.strategies.trend_following import TrendFollowingStrategy


class StrategyEngine:
    def __init__(
        self,
        settings: Settings,
        feature_repository: FeatureRepository,
        signal_repository: SignalRepository,
    ) -> None:
        self.settings = settings
        self.feature_repository = feature_repository
        self.signal_repository = signal_repository

    def generate(self, request: SignalGenerateRequest) -> SignalGenerateResult:
        strategy = self._load_strategy(request.strategy_id)
        features = self.feature_repository.latest_features(
            symbol=request.symbol,
            timeframe=request.timeframe,
            feature_set=request.feature_set,
            limit=request.limit,
        )
        signals = strategy.generate(features, environment=self.settings.trading_mode.value)
        inserted = self.signal_repository.insert_signals(signals)
        return SignalGenerateResult(
            generated=inserted,
            strategy_id=request.strategy_id,
            symbol=request.symbol.upper(),
            timeframe=request.timeframe.upper(),
            signals=signals,
        )

    @staticmethod
    def _load_strategy(strategy_id: str) -> TrendFollowingStrategy | MeanReversionStrategy:
        if strategy_id == "trend_following_v1":
            return TrendFollowingStrategy()
        if strategy_id == "mean_reversion_v1":
            return MeanReversionStrategy()
        raise ValueError(f"unsupported_strategy:{strategy_id}")
