from enum import StrEnum

from pydantic import BaseModel, Field

from rac.risk.models import RiskDecision


class OrderStatus(StrEnum):
    SUBMITTED = "submitted"        # enviada al broker, esperando fill real
    PAPER_ACCEPTED = "paper_accepted"  # simulación interna sin broker
    FILLED = "filled"              # broker confirmó el fill
    CANCELLED = "cancelled"        # cancelada o rechazada por el broker
    REJECTED = "rejected"          # rechazada por risk manager


class ExecuteSignalRequest(BaseModel):
    signal_id: str = Field(min_length=1)
    portfolio_equity: float = Field(gt=0)
    portfolio_cash: float = Field(ge=0)
    daily_pnl_pct: float = 0.0
    weekly_pnl_pct: float = 0.0
    drawdown_pct: float = 0.0
    current_asset_exposure_pct: float = 0.0
    consecutive_losses: int = Field(default=0, ge=0)
    kill_switch_active: bool = False
    order_type: str = "market"


class OrderExecutionResult(BaseModel):
    status: OrderStatus
    order_id: str | None
    signal_id: str
    risk_decision: RiskDecision
    reason: str | None = None

