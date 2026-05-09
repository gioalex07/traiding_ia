from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException

from rac.audit.repository import AuditRepository
from rac.config import load_settings
from rac.db.bootstrap import bootstrap_database
from rac.db.health import check_postgres, check_redis
from rac.discovery.service import EnvironmentDiscoveryService
from rac.features.models import FeatureComputeRequest, FeatureComputeResult
from rac.features.repository import FeatureRepository
from rac.features.service import FeatureService
from rac.market_data.models import MarketDataIngestRequest, MarketDataIngestResult
from rac.market_data.repository import MarketDataRepository
from rac.market_data.service import MarketDataIngestor
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.local_ai.models import ExplainSignalRequest, ExplainSignalResult, LocalAICapabilities
from rac.local_ai.repository import AIInteractionRepository
from rac.local_ai.service import LocalAIService
from rac.orders.executor import PaperOrderExecutor
from rac.orders.models import ExecuteSignalRequest, OrderExecutionResult
from rac.orders.reconciliation import ReconciliationResult, ReconciliationService
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository
from rac.risk.manager import RiskManager
from rac.risk.models import RiskDecision, RiskEvaluationRequest
from rac.strategies.models import SignalGenerateRequest, SignalGenerateResult
from rac.strategies.repository import SignalRepository
from rac.strategies.service import StrategyEngine


app = FastAPI(
    title="RAC API",
    version="0.1.0",
    description="Robo Advisor / Autonomous Capital control plane.",
)


@app.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat(),
    }


@app.post("/admin/bootstrap")
async def bootstrap() -> dict[str, str]:
    settings = load_settings()
    try:
        bootstrap_database(settings)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=exc.__class__.__name__) from exc
    return {"status": "ok"}


@app.get("/ready")
async def ready() -> dict[str, str]:
    settings = load_settings()
    report = EnvironmentDiscoveryService(settings).detect()
    postgres_status = check_postgres(settings)
    redis_status = check_redis(settings)
    if report.trading_mode == "live" and report.live_trading_status != "requires_human_approval":
        return {"status": "blocked", "reason": "live trading is not enabled"}
    infrastructure_reasons = []
    if not postgres_status["ok"]:
        infrastructure_reasons.append("postgres:not_ready")
    if not redis_status["ok"]:
        infrastructure_reasons.append("redis:not_ready")
    reasons = [*report.degraded_reasons, *infrastructure_reasons]
    return {
        "status": "ready" if not reasons else "degraded",
        "reason": ",".join(reasons) if reasons else "ok",
    }


@app.get("/capabilities")
async def capabilities() -> dict[str, object]:
    return EnvironmentDiscoveryService(load_settings()).detect().to_dict()


@app.get("/broker/capabilities")
async def broker_capabilities() -> dict[str, object]:
    settings = load_settings()
    try:
        capabilities = await AlpacaBrokerAdapter(settings).capabilities()
        return capabilities.__dict__
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"broker_unavailable:{exc.__class__.__name__}") from exc


@app.get("/broker/account")
async def broker_account() -> dict[str, object]:
    settings = load_settings()
    try:
        account = await AlpacaBrokerAdapter(settings).get_account()
        return account.__dict__
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"broker_unavailable:{exc}") from exc


@app.get("/broker/positions")
async def broker_positions() -> list[dict[str, object]]:
    settings = load_settings()
    try:
        positions = await AlpacaBrokerAdapter(settings).get_positions()
        return [position.__dict__ for position in positions]
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"broker_unavailable:{exc}") from exc


@app.post("/market-data/ohlcv", response_model=MarketDataIngestResult)
async def ingest_ohlcv(request: MarketDataIngestRequest) -> MarketDataIngestResult:
    settings = load_settings()
    try:
        result = MarketDataIngestor(MarketDataRepository(settings)).ingest(request)
        AuditRepository(settings).record_event(
            event_type="market_data.ohlcv_ingested",
            environment=settings.trading_mode.value,
            correlation_id=f"ohlcv:{datetime.now(UTC).isoformat()}",
            actor="market-data-ingestor",
            payload={
                "accepted": result.accepted,
                "rejected": result.rejected,
                "rejection_reasons": result.rejection_reasons,
            },
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"market_data_unavailable:{exc.__class__.__name__}") from exc


@app.get("/market-data/ohlcv/{symbol}/{timeframe}")
async def latest_ohlcv(symbol: str, timeframe: str, limit: int = 100) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 1000))
    try:
        return MarketDataRepository(settings).latest_ohlcv(symbol=symbol, timeframe=timeframe, limit=safe_limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"market_data_unavailable:{exc.__class__.__name__}") from exc


@app.post("/features/compute", response_model=FeatureComputeResult)
async def compute_features(request: FeatureComputeRequest) -> FeatureComputeResult:
    settings = load_settings()
    try:
        result = FeatureService(
            market_data_repository=MarketDataRepository(settings),
            feature_repository=FeatureRepository(settings),
        ).compute(request)
        AuditRepository(settings).record_event(
            event_type="features.computed",
            environment=settings.trading_mode.value,
            correlation_id=f"features:{request.symbol.upper()}:{request.timeframe.upper()}",
            actor="feature-engine",
            payload=result.model_dump(),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"feature_engine_unavailable:{exc.__class__.__name__}") from exc


@app.get("/features/{symbol}/{timeframe}")
async def latest_features(
    symbol: str,
    timeframe: str,
    feature_set: str = "technical_v1",
    limit: int = 100,
) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 1000))
    try:
        return FeatureRepository(settings).latest_features(
            symbol=symbol,
            timeframe=timeframe,
            feature_set=feature_set,
            limit=safe_limit,
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"feature_engine_unavailable:{exc.__class__.__name__}") from exc


@app.post("/signals/generate", response_model=SignalGenerateResult)
async def generate_signals(request: SignalGenerateRequest) -> SignalGenerateResult:
    settings = load_settings()
    try:
        result = StrategyEngine(
            settings=settings,
            feature_repository=FeatureRepository(settings),
            signal_repository=SignalRepository(settings),
        ).generate(request)
        AuditRepository(settings).record_event(
            event_type="signals.generated",
            environment=settings.trading_mode.value,
            correlation_id=f"signals:{request.strategy_id}:{request.symbol.upper()}:{request.timeframe.upper()}",
            actor="strategy-engine",
            payload={
                "generated": result.generated,
                "strategy_id": result.strategy_id,
                "symbol": result.symbol,
                "timeframe": result.timeframe,
            },
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"strategy_engine_unavailable:{exc.__class__.__name__}") from exc


@app.get("/signals/{symbol}/{timeframe}")
async def latest_signals(symbol: str, timeframe: str, limit: int = 100) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 1000))
    try:
        return SignalRepository(settings).latest_signals(symbol=symbol, timeframe=timeframe, limit=safe_limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"strategy_engine_unavailable:{exc.__class__.__name__}") from exc


@app.post("/orders/execute-signal", response_model=OrderExecutionResult)
async def execute_signal(request: ExecuteSignalRequest) -> OrderExecutionResult:
    settings = load_settings()
    try:
        result = await PaperOrderExecutor(
            settings=settings,
            signal_repository=SignalRepository(settings),
            order_repository=OrderRepository(settings),
            portfolio_repository=PortfolioRepository(settings),
            risk_manager=RiskManager(settings),
            broker_adapter=AlpacaBrokerAdapter(settings),
        ).execute_signal(request)
        audit = AuditRepository(settings)
        audit.record_event(
            event_type="orders.paper_execution_attempted",
            environment=settings.trading_mode.value,
            correlation_id=request.signal_id,
            actor="order-executor",
            payload=result.model_dump(),
        )
        if result.risk_decision.reasons and result.reason == "risk_rejected":
            audit.record_event(
                event_type="risk.decision",
                environment=settings.trading_mode.value,
                correlation_id=request.signal_id,
                actor="risk-manager",
                payload=result.risk_decision.model_dump(),
            )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"order_executor_unavailable:{exc.__class__.__name__}") from exc


@app.post("/orders/reconcile", response_model=ReconciliationResult)
async def reconcile_orders() -> ReconciliationResult:
    settings = load_settings()
    try:
        result = await ReconciliationService(
            broker_adapter=AlpacaBrokerAdapter(settings),
            order_repository=OrderRepository(settings),
            portfolio_repository=PortfolioRepository(settings),
        ).reconcile_pending()
        AuditRepository(settings).record_event(
            event_type="orders.reconciliation_run",
            environment=settings.trading_mode.value,
            correlation_id=f"reconcile:{datetime.now(UTC).isoformat()}",
            actor="reconciliation-service",
            payload=result.model_dump(),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"reconciliation_unavailable:{exc.__class__.__name__}") from exc


@app.get("/orders")
async def latest_orders(symbol: str | None = None, limit: int = 100) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 1000))
    try:
        return OrderRepository(settings).latest_orders(symbol=symbol, limit=safe_limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"order_executor_unavailable:{exc.__class__.__name__}") from exc


@app.get("/portfolio/snapshot")
async def portfolio_snapshot(environment: str = "paper") -> dict[str, object]:
    settings = load_settings()
    try:
        snapshot = PortfolioRepository(settings).latest_snapshot(environment=environment)
        return snapshot or {"environment": environment, "status": "empty"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"portfolio_unavailable:{exc.__class__.__name__}") from exc


@app.get("/portfolio/positions")
async def portfolio_positions(environment: str = "paper") -> list[dict[str, object]]:
    settings = load_settings()
    try:
        return PortfolioRepository(settings).positions(environment=environment)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"portfolio_unavailable:{exc.__class__.__name__}") from exc


@app.get("/ai/capabilities", response_model=LocalAICapabilities)
async def ai_capabilities() -> LocalAICapabilities:
    settings = load_settings()
    return LocalAIService(settings).capabilities()


@app.post("/ai/explain-signal", response_model=ExplainSignalResult)
async def explain_signal(request: ExplainSignalRequest) -> ExplainSignalResult:
    settings = load_settings()
    try:
        result = LocalAIService(
            settings,
            repository=AIInteractionRepository(settings),
        ).explain_signal(
            signal_id=request.signal_id,
            signal_repository=SignalRepository(settings),
        )
        AuditRepository(settings).record_event(
            event_type="ai.explain_signal",
            environment=settings.trading_mode.value,
            correlation_id=request.signal_id,
            actor="local-ai-service",
            payload=result.model_dump(),
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"local_ai_unavailable:{exc.__class__.__name__}") from exc


@app.post("/risk/evaluate", response_model=RiskDecision)
async def evaluate_risk(request: RiskEvaluationRequest) -> RiskDecision:
    settings = load_settings()
    decision = RiskManager(settings).evaluate(request)
    try:
        audit = AuditRepository(settings)
        audit.record_risk_decision(request, decision)
        audit.record_event(
            event_type="risk.decision",
            environment=request.order.environment,
            correlation_id=request.order.signal_id,
            actor="risk-manager",
            payload={
                "strategy_id": request.order.strategy_id,
                "symbol": request.order.symbol,
                "approved": decision.approved,
                "reasons": decision.reasons,
            },
        )
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"audit_unavailable:{exc.__class__.__name__}") from exc
    return decision
