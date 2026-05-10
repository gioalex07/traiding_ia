from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, RedirectResponse

from rac.admin.kill_switch import KillSwitchActivateRequest, KillSwitchRepository, KillSwitchState
from rac.audit.repository import AuditRepository
from rac.backtest.engine import BacktestEngine
from rac.backtest.models import BacktestRequest, BacktestResult
from rac.backtest.repository import BacktestRepository
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.config import load_settings
from rac.dashboard.html import DASHBOARD_HTML
from rac.dashboard.service import DashboardService
from rac.db.bootstrap import bootstrap_database
from rac.db.health import check_postgres, check_redis
from rac.discovery.service import EnvironmentDiscoveryService
from rac.features.models import FeatureComputeRequest, FeatureComputeResult
from rac.features.repository import FeatureRepository
from rac.features.service import FeatureService
from rac.local_ai.models import ExplainSignalRequest, ExplainSignalResult, LocalAICapabilities
from rac.local_ai.repository import AIInteractionRepository
from rac.local_ai.service import LocalAIService
from rac.market_data.loader import HistoricalDataLoader
from rac.market_data.models import (
    HistoricalFetchRequest,
    HistoricalFetchResult,
    MarketDataIngestRequest,
    MarketDataIngestResult,
)
from rac.market_data.repository import MarketDataRepository
from rac.market_data.service import MarketDataIngestor
from rac.orders.executor import PaperOrderExecutor
from rac.orders.models import ExecuteSignalRequest, OrderExecutionResult
from rac.orders.reconciliation import ReconciliationResult, ReconciliationService
from rac.orders.repository import OrderRepository
from rac.pipeline.models import PaperPipelineRequest, PaperPipelineResult
from rac.pipeline.service import PaperAnalysisPipeline
from rac.portfolio.models import MarkToMarketResult
from rac.portfolio.repository import PortfolioRepository
from rac.portfolio.service import PortfolioMarkToMarketService
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


@app.get("/")
async def root() -> RedirectResponse:
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(DASHBOARD_HTML)


@app.get("/dashboard/data")
async def dashboard_data() -> dict[str, object]:
    settings = load_settings()
    snapshot = await DashboardService(settings).snapshot()
    return jsonable_encoder(snapshot)


@app.get("/admin/kill-switch", response_model=KillSwitchState)
async def kill_switch_state() -> KillSwitchState:
    settings = load_settings()
    return KillSwitchRepository(settings).current_state()


@app.post("/admin/kill-switch", response_model=KillSwitchState)
async def activate_kill_switch(request: KillSwitchActivateRequest) -> KillSwitchState:
    settings = load_settings()
    ks = KillSwitchRepository(settings)
    event_id = ks.activate(reason=request.reason, actor=request.actor)
    AuditRepository(settings).record_event(
        event_type="kill_switch.activated",
        environment=settings.trading_mode.value,
        correlation_id=event_id,
        actor=request.actor,
        payload={"reason": request.reason},
    )
    return ks.current_state()


@app.post("/admin/kill-switch/reset", response_model=KillSwitchState)
async def deactivate_kill_switch(request: KillSwitchActivateRequest) -> KillSwitchState:
    settings = load_settings()
    ks = KillSwitchRepository(settings)
    event_id = ks.deactivate(reason=request.reason, actor=request.actor)
    AuditRepository(settings).record_event(
        event_type="kill_switch.deactivated",
        environment=settings.trading_mode.value,
        correlation_id=event_id,
        actor=request.actor,
        payload={"reason": request.reason},
    )
    return ks.current_state()


@app.get("/admin/kill-switch/history")
async def kill_switch_history(limit: int = 20) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 100))
    return KillSwitchRepository(settings).history(safe_limit)


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


@app.post("/market-data/fetch-historical", response_model=HistoricalFetchResult)
async def fetch_historical(request: HistoricalFetchRequest) -> HistoricalFetchResult:
    settings = load_settings()
    try:
        result = await HistoricalDataLoader(
            broker=AlpacaBrokerAdapter(settings),
            repository=MarketDataRepository(settings),
        ).fetch_and_store(request)
        AuditRepository(settings).record_event(
            event_type="market_data.historical_fetched",
            environment=settings.trading_mode.value,
            correlation_id=f"historical:{request.symbol.upper()}:{request.timeframe}",
            actor="historical-data-loader",
            payload=result.model_dump(),
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"historical_fetch_error:{exc}") from exc


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


@app.get("/portfolio/history")
async def portfolio_history(environment: str = "paper", limit: int = 100) -> list[dict[str, object]]:
    settings = load_settings()
    try:
        return PortfolioRepository(settings).history(environment=environment, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"portfolio_unavailable:{exc.__class__.__name__}") from exc


@app.post("/portfolio/mark-to-market", response_model=MarkToMarketResult)
async def mark_to_market(environment: str = "paper", timeframe: str = "1Day") -> MarkToMarketResult:
    settings = load_settings()
    try:
        result = await PortfolioMarkToMarketService(
            settings=settings,
            repository=PortfolioRepository(settings),
            broker=AlpacaBrokerAdapter(settings),
        ).run(environment=environment, timeframe=timeframe)
        AuditRepository(settings).record_event(
            event_type="portfolio.mark_to_market",
            environment=environment,
            correlation_id=f"mark-to-market:{environment}:{timeframe}",
            actor="portfolio-manager",
            payload=result.model_dump(),
        )
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"portfolio_mark_to_market_unavailable:{exc}") from exc


@app.post("/pipeline/paper/run", response_model=PaperPipelineResult)
async def run_paper_pipeline(request: PaperPipelineRequest) -> PaperPipelineResult:
    settings = load_settings()
    try:
        return await PaperAnalysisPipeline(settings).run(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"paper_pipeline_unavailable:{exc}") from exc


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


@app.post("/backtest/run", response_model=BacktestResult)
async def run_backtest(request: BacktestRequest) -> BacktestResult:
    settings = load_settings()
    try:
        bars = MarketDataRepository(settings).latest_ohlcv(
            symbol=request.symbol,
            timeframe=request.timeframe,
            limit=10_000,
        )
        in_range = [
            b for b in bars
            if request.start <= b["time"].replace(tzinfo=None) <= request.end  # type: ignore[union-attr]
        ]
        if not in_range:
            raise HTTPException(
                status_code=422,
                detail=f"no_data_for_range: ingest OHLCV bars for {request.symbol}/{request.timeframe} first",
            )
        result = BacktestEngine().run(request, in_range)
        repo = BacktestRepository(settings)
        backtest_id = repo.save(result)
        result.backtest_id = backtest_id
        return result
    except (ValueError, HTTPException):
        raise
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"backtest_error:{exc.__class__.__name__}") from exc


@app.get("/backtest/list")
async def list_backtests(limit: int = 20) -> list[dict[str, object]]:
    settings = load_settings()
    safe_limit = max(1, min(limit, 100))
    return BacktestRepository(settings).list_recent(safe_limit)


@app.get("/backtest/{backtest_id}")
async def get_backtest(backtest_id: str) -> dict[str, object]:
    settings = load_settings()
    result = BacktestRepository(settings).get(backtest_id)
    if result is None:
        raise HTTPException(status_code=404, detail="backtest_not_found")
    return result


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
