from rac.audit.repository import AuditRepository
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.config import Settings, TradingMode
from rac.features.models import FeatureComputeRequest
from rac.features.repository import FeatureRepository
from rac.features.service import FeatureService
from rac.local_ai.repository import AIInteractionRepository
from rac.local_ai.service import LocalAIService
from rac.market_data.loader import HistoricalDataLoader
from rac.market_data.models import HistoricalFetchRequest
from rac.market_data.repository import MarketDataRepository
from rac.pipeline.models import PaperPipelineRequest, PaperPipelineResult
from rac.strategies.models import SignalGenerateRequest
from rac.strategies.repository import SignalRepository
from rac.strategies.service import StrategyEngine


class PaperAnalysisPipeline:
    """Runs market data, features, signals and local AI without order execution."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run(self, request: PaperPipelineRequest) -> PaperPipelineResult:
        if self.settings.trading_mode == TradingMode.LIVE:
            raise ValueError("live_mode_blocked_for_paper_pipeline")

        market_repository = MarketDataRepository(self.settings)
        feature_repository = FeatureRepository(self.settings)
        signal_repository = SignalRepository(self.settings)

        fetched = await HistoricalDataLoader(
            broker=AlpacaBrokerAdapter(self.settings),
            repository=market_repository,
        ).fetch_and_store(
            HistoricalFetchRequest(
                symbol=request.symbol,
                timeframe=request.timeframe,
                start=request.start,
                end=request.end,
            )
        )
        features = FeatureService(
            market_data_repository=market_repository,
            feature_repository=feature_repository,
        ).compute(
            FeatureComputeRequest(
                symbol=request.symbol,
                timeframe=request.timeframe,
                feature_set=request.feature_set,
                limit=request.limit,
            )
        )
        generated = StrategyEngine(
            settings=self.settings,
            feature_repository=feature_repository,
            signal_repository=signal_repository,
        ).generate(
            SignalGenerateRequest(
                symbol=request.symbol,
                timeframe=request.timeframe,
                feature_set=request.feature_set,
                strategy_id=request.strategy_id,
                limit=request.limit,
            )
        )

        latest_signal = generated.signals[-1] if generated.signals else None
        latest_signal_id: str | None = None
        latest_signal_direction: str | None = None
        if latest_signal:
            rows = signal_repository.latest_signals(
                symbol=request.symbol,
                timeframe=request.timeframe,
                limit=1,
                strategy_id=request.strategy_id,
            )
            if rows:
                latest_signal_id = str(rows[0]["id"])
                latest_signal_direction = str(rows[0]["direction"])

        ai_status = None
        ai_model_name = None
        ai_explanation = None
        if request.explain and latest_signal_id:
            explanation = LocalAIService(
                self.settings,
                repository=AIInteractionRepository(self.settings),
            ).explain_signal(
                signal_id=latest_signal_id,
                signal_repository=signal_repository,
            )
            ai_status = explanation.status
            ai_model_name = explanation.model_name
            ai_explanation = explanation.explanation

        result = PaperPipelineResult(
            status="ok",
            symbol=fetched.symbol,
            timeframe=fetched.timeframe,
            fetched=fetched.fetched,
            accepted=fetched.accepted,
            rejected=fetched.rejected,
            features_computed=features.computed,
            signals_generated=generated.generated,
            latest_signal_id=latest_signal_id,
            latest_signal_direction=latest_signal_direction,
            ai_status=ai_status,
            ai_model_name=ai_model_name,
            ai_explanation=ai_explanation,
        )
        AuditRepository(self.settings).record_event(
            event_type="pipeline.paper_analysis_run",
            environment=self.settings.trading_mode.value,
            correlation_id=f"pipeline:{request.symbol}:{request.timeframe}:{request.strategy_id}",
            actor="paper-analysis-pipeline",
            payload=result.model_dump(exclude={"ai_explanation"}),
        )
        return result
