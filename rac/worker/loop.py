import asyncio
import hashlib
import logging
from datetime import UTC, datetime
from typing import Any

from rac.admin.kill_switch import KillSwitchRepository
from rac.audit.repository import AuditRepository
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.brokers.base import OrderRequest, Position
from rac.config import Settings, load_settings
from rac.db.bootstrap import bootstrap_database
from rac.features.models import FeatureComputeRequest
from rac.features.repository import FeatureRepository
from rac.features.service import FeatureService
from rac.market_data.models import MarketDataIngestRequest
from rac.market_data.repository import MarketDataRepository
from rac.market_data.service import MarketDataIngestor
from rac.notifications.service import AlertService
from rac.notifications.telegram import TelegramClient
from rac.orders.executor import PaperOrderExecutor
from rac.orders.models import ExecuteSignalRequest
from rac.orders.reconciliation import ReconciliationService
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository
from rac.portfolio.service import PortfolioMarkToMarketService
from rac.reports.daily import DailyReportService
from rac.risk.manager import RiskManager
from rac.strategies.models import SignalGenerateRequest
from rac.strategies.repository import SignalRepository
from rac.strategies.service import StrategyEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("rac.worker")

_FEATURE_SET = "technical_v1"
_SIGNAL_MAX_AGE_SECONDS = 120


# --- funciones puras (testeables sin dependencias) ---

def _skip_reason(
    direction: str,
    age_seconds: float,
    position: Position | None,
) -> str | None:
    """Devuelve el motivo para saltarse la señal, o None si debe ejecutarse."""
    if age_seconds > _SIGNAL_MAX_AGE_SECONDS:
        return f"stale:{age_seconds:.0f}s"
    if direction == "sell" and position is None:
        return "no_position_to_sell"
    return None


def _sl_tp_trigger(
    current_price: float,
    stop_loss_price: float | None,
    take_profit_price: float | None,
) -> str | None:
    """Devuelve 'stop_loss', 'take_profit', o None si no hay trigger."""
    if stop_loss_price and current_price <= stop_loss_price:
        return "stop_loss"
    if take_profit_price and current_price >= take_profit_price:
        return "take_profit"
    return None


# --- lógica del ciclo ---

async def run_cycle(settings: Settings, broker: AlpacaBrokerAdapter, alerts: AlertService) -> None:
    market_repo = MarketDataRepository(settings)
    feature_repo = FeatureRepository(settings)
    signal_repo = SignalRepository(settings)
    order_repo = OrderRepository(settings)
    portfolio_repo = PortfolioRepository(settings)
    audit = AuditRepository(settings)

    # 1. Reconciliar órdenes pendientes
    try:
        recon = await ReconciliationService(broker, order_repo, portfolio_repo, alerts).reconcile_pending()
        if recon.checked:
            log.info(
                "reconcile checked=%d filled=%d pending=%d cancelled=%d errors=%d",
                recon.checked, recon.filled, recon.pending, recon.cancelled, len(recon.errors),
            )
            _audit(audit, "worker.reconcile", settings, recon.model_dump())
    except Exception as exc:
        log.warning("reconcile_error: %s", exc)

    # 2. Mark to market + drawdown alert
    try:
        mtm = await PortfolioMarkToMarketService(settings, portfolio_repo, broker).run(
            environment="paper",
            timeframe="1Day",
        )
        log.info(
            "mark_to_market nav=%.2f positions_value=%.2f errors=%d",
            mtm.nav, mtm.positions_value, len(mtm.errors),
        )
        peak = portfolio_repo.peak_nav("paper")
        if peak > 0:
            drawdown_pct = max(0.0, (peak - mtm.nav) / peak * 100.0)
            alerts.on_drawdown(drawdown_pct, settings.max_drawdown_pct)
    except Exception as exc:
        log.warning("mark_to_market_error: %s", exc)

    # 3. Reporte diario (una vez al día después de las 21:00 UTC)
    if alerts.should_send_daily_report():
        try:
            report = DailyReportService(portfolio_repo, order_repo).build("paper")
            alerts.on_daily_report(
                report_date=report.date,
                nav=report.nav,
                pnl_daily=report.pnl_daily,
                drawdown_pct=report.drawdown_pct,
                cash=report.cash,
                positions=report.positions,
                fills_today=report.fills_today,
                strategies=settings.watched_strategies,
            )
            log.info("daily_report_sent date=%s nav=%.2f pnl=%.2f", report.date, report.nav, report.pnl_daily)
        except Exception as exc:
            log.warning("daily_report_error: %s", exc)

    # 4. Kill switch — bloquea ejecución de órdenes (reconciliación y MTM ya corrieron)
    ks_repo = KillSwitchRepository(settings)
    if ks_repo.is_active():
        ks_state = ks_repo.current_state()
        alerts.on_kill_switch_active(ks_state.reason if ks_state and ks_state.reason else "unknown")
        log.warning("KILL_SWITCH_ACTIVE — order execution blocked this cycle")
        _audit(audit, "worker.kill_switch_blocked", settings, {"cycle_skipped": True})
        return
    alerts.on_kill_switch_reset()

    # 5. Estado de cuenta y posiciones desde Alpaca
    try:
        account = await broker.get_account()
    except Exception as exc:
        log.error("account_fetch_error: %s — skipping cycle", exc)
        return

    try:
        raw_positions = await broker.get_positions()
        positions_by_symbol: dict[str, Position] = {p.symbol.upper(): p for p in raw_positions}
    except Exception as exc:
        log.warning("positions_fetch_error: %s — exposure tracking disabled", exc)
        positions_by_symbol = {}

    log.info(
        "account equity=%.2f cash=%.2f open_positions=%d",
        account.equity, account.cash, len(positions_by_symbol),
    )

    # 6. Ciclo por símbolo: fetch → ingest → features → señales → SL/TP → ejecutar
    for symbol in settings.watched_symbols:
        try:
            await _process_symbol(
                settings=settings,
                broker=broker,
                symbol=symbol,
                market_repo=market_repo,
                feature_repo=feature_repo,
                signal_repo=signal_repo,
                order_repo=order_repo,
                portfolio_repo=portfolio_repo,
                audit=audit,
                portfolio_equity=account.equity,
                portfolio_cash=account.cash,
                position=positions_by_symbol.get(symbol.upper()),
            )
        except Exception as exc:
            log.error("symbol_error symbol=%s error=%s", symbol, exc)


async def _process_symbol(
    *,
    settings: Settings,
    broker: AlpacaBrokerAdapter,
    symbol: str,
    market_repo: MarketDataRepository,
    feature_repo: FeatureRepository,
    signal_repo: SignalRepository,
    order_repo: OrderRepository,
    portfolio_repo: PortfolioRepository,
    audit: AuditRepository,
    portfolio_equity: float,
    portfolio_cash: float,
    position: Position | None,
) -> None:
    timeframe = settings.watched_timeframe

    bars = await broker.get_latest_bars(symbol, timeframe, limit=20)
    if not bars:
        log.debug("no_bars symbol=%s timeframe=%s", symbol, timeframe)
        return

    log.info("fetched symbol=%s bars=%d latest_close=%.4f", symbol, len(bars), bars[-1].close)

    MarketDataIngestor(market_repo).ingest(MarketDataIngestRequest(bars=bars))

    FeatureService(market_repo, feature_repo).compute(
        FeatureComputeRequest(symbol=symbol, timeframe=timeframe, feature_set=_FEATURE_SET)
    )

    # Monitoreo SL/TP para posición abierta (antes de generar nuevas señales)
    if position is not None:
        await _maybe_close_position(
            symbol=symbol,
            current_price=bars[-1].close,
            position=position,
            order_repo=order_repo,
            broker=broker,
            settings=settings,
            audit=audit,
        )

    current_asset_exposure_pct = (
        (position.market_value / portfolio_equity) * 100.0 if position else 0.0
    )

    # Ejecutar estrategias en orden — primera señal accionable gana
    for strategy_id in settings.watched_strategies:
        StrategyEngine(settings, feature_repo, signal_repo).generate(
            SignalGenerateRequest(symbol=symbol, timeframe=timeframe, strategy_id=strategy_id)
        )

        latest = signal_repo.latest_signals(symbol, timeframe, strategy_id=strategy_id, limit=1)
        if not latest:
            continue

        signal = latest[0]
        direction = str(signal["direction"])

        if direction == "hold":
            log.info("hold symbol=%s strategy=%s confidence=%.4f", symbol, strategy_id, float(signal["confidence"]))
            continue

        confidence = float(signal["confidence"])
        if confidence < settings.min_signal_confidence:
            log.info(
                "low_confidence symbol=%s strategy=%s direction=%s confidence=%.4f threshold=%.2f",
                symbol, strategy_id, direction, confidence, settings.min_signal_confidence,
            )
            continue

        raw_time = signal["time"]
        signal_time: datetime = raw_time if isinstance(raw_time, datetime) else datetime.fromisoformat(str(raw_time))
        if signal_time.tzinfo is None:
            signal_time = signal_time.replace(tzinfo=UTC)
        age_seconds = (datetime.now(UTC) - signal_time).total_seconds()

        skip = _skip_reason(direction, age_seconds, position)
        if skip:
            log.info("skip symbol=%s strategy=%s direction=%s reason=%s", symbol, strategy_id, direction, skip)
            continue

        signal_id = str(signal["id"])
        if order_repo.has_order_for_signal(signal_id):
            log.info("already_executed symbol=%s strategy=%s signal_id=%s", symbol, strategy_id, signal_id)
            continue

        log.info(
            "executing symbol=%s strategy=%s direction=%s confidence=%.4f exposure=%.2f%%",
            symbol, strategy_id, direction, float(signal["confidence"]), current_asset_exposure_pct,
        )
        result = await PaperOrderExecutor(
            settings=settings,
            signal_repository=signal_repo,
            order_repository=order_repo,
            portfolio_repository=portfolio_repo,
            risk_manager=RiskManager(settings),
            broker_adapter=broker,
        ).execute_signal(
            ExecuteSignalRequest(
                signal_id=signal_id,
                portfolio_equity=portfolio_equity,
                portfolio_cash=portfolio_cash,
                current_asset_exposure_pct=current_asset_exposure_pct,
            )
        )
        log.info("order status=%s order_id=%s reason=%s", result.status, result.order_id, result.reason)
        _audit(audit, "worker.order_executed", settings, {
            "symbol": symbol,
            "strategy_id": strategy_id,
            "direction": direction,
            "status": result.status,
            "order_id": result.order_id,
            "reason": result.reason,
        })
        break  # ejecutó una señal para este símbolo — no intentar más estrategias


async def _maybe_close_position(
    *,
    symbol: str,
    current_price: float,
    position: Position,
    order_repo: OrderRepository,
    broker: AlpacaBrokerAdapter,
    settings: Settings,
    audit: AuditRepository,
) -> None:
    raw_order = order_repo.latest_filled_buy(symbol)
    if not raw_order:
        return
    buy_order: dict[str, Any] = dict(raw_order)

    sl = float(buy_order["stop_loss_price"]) if buy_order.get("stop_loss_price") else None
    tp = float(buy_order["take_profit_price"]) if buy_order.get("take_profit_price") else None

    trigger = _sl_tp_trigger(current_price, sl, tp)
    if not trigger:
        return

    parent_id = str(buy_order["id"])
    close_key = hashlib.sha256(f"close:{parent_id}:{trigger}".encode()).hexdigest()

    if order_repo.has_order_with_idempotency(close_key):
        return  # ya se envió la orden de cierre

    log.warning(
        "SL_TP_TRIGGERED symbol=%s reason=%s current=%.4f sl=%s tp=%s",
        symbol, trigger, current_price, sl, tp,
    )

    try:
        ack = await broker.submit_order(OrderRequest(
            idempotency_key=close_key[:48],
            symbol=symbol,
            side="sell",
            order_type="market",
            quantity=position.quantity,
        ))
        order_repo.insert_close_order(
            symbol=symbol,
            environment=settings.trading_mode.value,
            quantity=position.quantity,
            estimated_price=current_price,
            idempotency_key=close_key,
            broker_order_id=ack.broker_order_id,
            parent_order_id=parent_id,
            reason=trigger,
        )
        log.info("close_submitted symbol=%s reason=%s broker_order_id=%s", symbol, trigger, ack.broker_order_id)
        _audit(audit, "worker.sl_tp_close", settings, {
            "symbol": symbol,
            "reason": trigger,
            "current_price": current_price,
            "stop_loss_price": sl,
            "take_profit_price": tp,
            "broker_order_id": ack.broker_order_id,
        })
    except Exception as exc:
        log.error("close_submit_error symbol=%s reason=%s error=%s", symbol, trigger, exc)


def _audit(audit: AuditRepository, event_type: str, settings: Settings, payload: dict) -> None:
    try:
        audit.record_event(
            event_type=event_type,
            environment=settings.trading_mode.value,
            correlation_id=f"worker:{datetime.now(UTC).isoformat()}",
            actor="rac.worker",
            payload=payload,
        )
    except Exception as exc:
        log.warning("audit_error event=%s error=%s", event_type, exc)


async def main() -> None:
    settings = load_settings()

    # P1: auto-bootstrap — garantiza migraciones antes de arrancar el loop
    log.info("bootstrapping database...")
    bootstrap_database(settings)
    log.info("database ready")

    broker = AlpacaBrokerAdapter(settings)
    alerts = AlertService(TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id))
    interval = settings.loop_interval_seconds

    log.info(
        "worker started symbols=%s timeframe=%s interval=%ds telegram=%s",
        list(settings.watched_symbols), settings.watched_timeframe, interval,
        alerts._client.configured,
    )

    while True:
        started = asyncio.get_event_loop().time()
        try:
            await run_cycle(settings, broker, alerts)
        except Exception as exc:
            log.error("cycle_error: %s", exc, exc_info=True)
        elapsed = asyncio.get_event_loop().time() - started
        sleep_time = max(0.0, interval - elapsed)
        log.info("cycle_done elapsed=%.1fs sleeping=%.1fs", elapsed, sleep_time)
        await asyncio.sleep(sleep_time)


if __name__ == "__main__":
    asyncio.run(main())
