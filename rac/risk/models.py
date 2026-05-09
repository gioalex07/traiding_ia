from enum import StrEnum

from pydantic import BaseModel, Field


class OrderSide(StrEnum):
    BUY = "buy"
    SELL = "sell"


class OrderType(StrEnum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class RiskDecisionStatus(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class OrderIntent(BaseModel):
    environment: str = "paper"
    symbol: str = Field(min_length=1)
    side: OrderSide
    order_type: OrderType
    quantity: float = Field(gt=0)
    estimated_price: float = Field(gt=0)
    stop_loss_price: float | None = Field(default=None, gt=0)
    take_profit_price: float | None = Field(default=None, gt=0)
    strategy_id: str = Field(min_length=1)
    signal_id: str = Field(min_length=1)


class PortfolioState(BaseModel):
    equity: float = Field(gt=0)
    cash: float = Field(ge=0)
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    current_asset_exposure_pct: float = 0.0
    consecutive_losses: int = Field(default=0, ge=0)
    kill_switch_active: bool = False


class RiskEvaluationRequest(BaseModel):
    order: OrderIntent
    portfolio: PortfolioState


class RiskDecision(BaseModel):
    status: RiskDecisionStatus
    approved: bool
    reasons: list[str]
    max_notional_allowed: float
    requested_notional: float

