import hashlib

from rac.brokers.base import BrokerAdapter, OrderRequest
from rac.config import Settings, TradingMode
from rac.orders.models import ExecuteSignalRequest, OrderExecutionResult, OrderStatus
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository
from rac.risk.manager import RiskManager
from rac.risk.models import OrderIntent, OrderSide, OrderType, PortfolioState, RiskDecision, RiskEvaluationRequest
from rac.strategies.repository import SignalRepository


class PaperOrderExecutor:
    def __init__(
        self,
        settings: Settings,
        signal_repository: SignalRepository,
        order_repository: OrderRepository,
        portfolio_repository: PortfolioRepository | None,
        risk_manager: RiskManager,
        broker_adapter: BrokerAdapter | None = None,
    ) -> None:
        self.settings = settings
        self.signal_repository = signal_repository
        self.order_repository = order_repository
        self.portfolio_repository = portfolio_repository
        self.risk_manager = risk_manager
        self.broker_adapter = broker_adapter

    async def execute_signal(self, request: ExecuteSignalRequest) -> OrderExecutionResult:
        if self.settings.trading_mode == TradingMode.LIVE:
            decision = self._rejected_decision("live_blocked")
            return OrderExecutionResult(
                status=OrderStatus.REJECTED,
                order_id=None,
                signal_id=request.signal_id,
                risk_decision=decision,
                reason="live_blocked",
            )

        signal = self.signal_repository.get_signal(request.signal_id)
        if signal is None:
            decision = self._rejected_decision("signal_not_found")
            return OrderExecutionResult(
                status=OrderStatus.REJECTED,
                order_id=None,
                signal_id=request.signal_id,
                risk_decision=decision,
                reason="signal_not_found",
            )

        if signal["direction"] == "hold":
            decision = self._rejected_decision("hold_signal")
            return OrderExecutionResult(
                status=OrderStatus.REJECTED,
                order_id=None,
                signal_id=request.signal_id,
                risk_decision=decision,
                reason="hold_signal",
            )

        order = self._build_order_intent(signal, request)
        portfolio = PortfolioState(
            equity=request.portfolio_equity,
            cash=request.portfolio_cash,
            daily_pnl_pct=request.daily_pnl_pct,
            weekly_pnl_pct=request.weekly_pnl_pct,
            drawdown_pct=request.drawdown_pct,
            current_asset_exposure_pct=request.current_asset_exposure_pct,
            consecutive_losses=request.consecutive_losses,
            kill_switch_active=request.kill_switch_active,
        )
        risk_request = RiskEvaluationRequest(order=order, portfolio=portfolio)
        risk_decision = self.risk_manager.evaluate(risk_request)
        if not risk_decision.approved:
            return OrderExecutionResult(
                status=OrderStatus.REJECTED,
                order_id=None,
                signal_id=request.signal_id,
                risk_decision=risk_decision,
                reason="risk_rejected",
            )

        idempotency_key = self._idempotency_key(signal, order)

        broker_order_id = None
        broker_name = "paper"
        mode = "paper_only"
        broker_ack_payload: dict[str, object] = {}
        if self.broker_adapter is not None:
            broker_request = OrderRequest(
                idempotency_key=idempotency_key,
                symbol=order.symbol,
                side=order.side.value,
                order_type=order.order_type.value,
                quantity=order.quantity,
            )
            ack = await self.broker_adapter.submit_order(broker_request)
            broker_order_id = ack.broker_order_id
            broker_name = "alpaca"
            mode = "alpaca_paper"
            broker_ack_payload = ack.raw_payload

        if self.broker_adapter is not None:
            # orden enviada a Alpaca — el fill real lo aplica ReconciliationService
            order_id = self.order_repository.insert_paper_order(
                broker=broker_name,
                order=order,
                signal_id=request.signal_id,
                idempotency_key=idempotency_key,
                risk_decision=risk_decision,
                broker_order_id=broker_order_id,
                status=OrderStatus.SUBMITTED,
                raw_payload={"signal": dict(signal), "mode": mode, "broker_ack": broker_ack_payload},
            )
            return OrderExecutionResult(
                status=OrderStatus.SUBMITTED,
                order_id=order_id,
                signal_id=request.signal_id,
                risk_decision=risk_decision,
            )

        # simulación interna sin broker — fill sintético inmediato
        order_id = self.order_repository.insert_paper_order(
            broker="paper",
            order=order,
            signal_id=request.signal_id,
            idempotency_key=idempotency_key,
            risk_decision=risk_decision,
            status=OrderStatus.PAPER_ACCEPTED,
            raw_payload={"signal": dict(signal), "mode": "paper_only", "broker_ack": {}},
        )
        if self.portfolio_repository:
            self.portfolio_repository.apply_paper_fill(
                environment="paper",
                order_id=order_id,
                symbol=order.symbol,
                side=order.side.value,
                quantity=order.quantity,
                price=order.estimated_price,
                starting_cash=request.portfolio_cash,
            )
        return OrderExecutionResult(
            status=OrderStatus.PAPER_ACCEPTED,
            order_id=order_id,
            signal_id=request.signal_id,
            risk_decision=risk_decision,
        )

    def _build_order_intent(self, signal: dict[str, object], request: ExecuteSignalRequest) -> OrderIntent:
        values = signal["raw_payload"]["values"]
        estimated_price = float(values["close"])
        max_position_pct = float(signal["max_position_pct"])
        notional = request.portfolio_equity * (max_position_pct / 100)
        quantity = notional / estimated_price
        side = OrderSide.BUY if signal["direction"] == "buy" else OrderSide.SELL

        stop_loss_pct = float(signal["stop_loss_pct"]) / 100
        take_profit_pct = float(signal["take_profit_pct"]) / 100
        if side == OrderSide.BUY:
            stop_loss_price = estimated_price * (1 - stop_loss_pct)
            take_profit_price = estimated_price * (1 + take_profit_pct)
        else:
            stop_loss_price = estimated_price * (1 + stop_loss_pct)
            take_profit_price = estimated_price * (1 - take_profit_pct)

        return OrderIntent(
            environment="paper",
            symbol=str(signal["symbol"]),
            side=side,
            order_type=OrderType(request.order_type),
            quantity=quantity,
            estimated_price=estimated_price,
            stop_loss_price=stop_loss_price,
            take_profit_price=take_profit_price,
            strategy_id=str(signal["strategy_id"]),
            signal_id=str(signal["id"]),
        )

    @staticmethod
    def _idempotency_key(signal: dict[str, object], order: OrderIntent) -> str:
        raw = f"{signal['id']}:{order.side}:{order.order_type}:{order.quantity:.8f}:{order.estimated_price:.8f}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _rejected_decision(reason: str) -> RiskDecision:
        return RiskDecision(
            status="rejected",
            approved=False,
            reasons=[reason],
            max_notional_allowed=0,
            requested_notional=0,
        )
