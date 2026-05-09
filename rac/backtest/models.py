from datetime import datetime

from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy_id: str = Field(default="trend_following_v1", min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(default="1Min", min_length=1)
    start: datetime
    end: datetime
    initial_cash: float = Field(default=100_000.0, gt=0)
    slippage_pct: float = Field(default=0.05, ge=0)   # 0.05 % por lado
    commission_per_trade: float = Field(default=0.0, ge=0)
    feature_set: str = Field(default="technical_v1", min_length=1)


class BacktestTrade(BaseModel):
    entry_time: datetime
    exit_time: datetime | None = None
    symbol: str
    side: str
    quantity: float
    entry_price: float
    exit_price: float | None = None
    pnl: float | None = None
    pnl_pct: float | None = None
    exit_reason: str | None = None
    bars_held: int = 0


class BacktestMetrics(BaseModel):
    total_return_pct: float
    max_drawdown_pct: float
    sharpe_ratio: float
    win_rate_pct: float
    profit_factor: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_win_pct: float
    avg_loss_pct: float


class BacktestResult(BaseModel):
    backtest_id: str
    strategy_id: str
    symbol: str
    timeframe: str
    start: datetime
    end: datetime
    initial_cash: float
    final_equity: float
    bars_processed: int
    metrics: BacktestMetrics
    equity_curve: list[dict[str, object]]
    trades: list[BacktestTrade]
    status: str = "completed"
