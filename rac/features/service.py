from rac.features.engine import FeatureEngine
from rac.features.models import FeatureComputeRequest, FeatureComputeResult
from rac.features.repository import FeatureRepository
from rac.market_data.repository import MarketDataRepository


class FeatureService:
    def __init__(
        self,
        market_data_repository: MarketDataRepository,
        feature_repository: FeatureRepository,
        engine: FeatureEngine | None = None,
    ) -> None:
        self.market_data_repository = market_data_repository
        self.feature_repository = feature_repository
        self.engine = engine or FeatureEngine()

    def compute(self, request: FeatureComputeRequest) -> FeatureComputeResult:
        bars = self.market_data_repository.latest_ohlcv(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=request.limit,
        )
        points = self.engine.compute_technical_v1(bars, feature_set=request.feature_set)
        inserted = self.feature_repository.upsert_features(points)
        return FeatureComputeResult(
            computed=inserted,
            feature_set=request.feature_set,
            symbol=request.symbol.upper(),
            timeframe=request.timeframe.upper(),
        )

