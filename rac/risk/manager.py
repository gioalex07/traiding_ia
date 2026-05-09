from rac.config import Settings, TradingMode
from rac.risk.models import (
    OrderSide,
    RiskDecision,
    RiskDecisionStatus,
    RiskEvaluationRequest,
)


class RiskManager:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        order = request.order
        portfolio = request.portfolio
        reasons: list[str] = []
        requested_notional = order.quantity * order.estimated_price
        max_notional = portfolio.equity * (self.settings.max_position_pct / 100)

        if portfolio.kill_switch_active:
            reasons.append("kill_switch_active")
        if self.settings.trading_mode == TradingMode.LIVE and not self.settings.can_submit_live_orders:
            reasons.append("live_blocked")
        if order.environment == "live" and not self.settings.can_submit_live_orders:
            reasons.append("live_blocked")
        if portfolio.daily_pnl_pct <= -abs(self.settings.max_daily_loss_pct):
            reasons.append("limit_daily_loss")
        if portfolio.weekly_pnl_pct <= -abs(self.settings.max_weekly_loss_pct):
            reasons.append("limit_weekly_loss")
        if portfolio.drawdown_pct >= self.settings.max_drawdown_pct:
            reasons.append("limit_drawdown")
        if portfolio.consecutive_losses >= self.settings.cooldown_after_losses:
            reasons.append("cooldown_active")
        if requested_notional > max_notional:
            reasons.append("limit_position_size")
        if portfolio.current_asset_exposure_pct >= self.settings.max_asset_exposure_pct:
            reasons.append("limit_asset_exposure")
        if order.stop_loss_price is None:
            reasons.append("missing_stop_loss")
        if order.take_profit_price is None:
            reasons.append("missing_take_profit")
        if order.side == OrderSide.BUY and order.stop_loss_price and order.stop_loss_price >= order.estimated_price:
            reasons.append("invalid_stop_loss")
        if order.side == OrderSide.SELL and order.stop_loss_price and order.stop_loss_price <= order.estimated_price:
            reasons.append("invalid_stop_loss")

        approved = not reasons
        return RiskDecision(
            status=RiskDecisionStatus.APPROVED if approved else RiskDecisionStatus.REJECTED,
            approved=approved,
            reasons=reasons,
            max_notional_allowed=max_notional,
            requested_notional=requested_notional,
        )

