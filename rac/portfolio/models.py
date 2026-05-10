from pydantic import BaseModel


class MarkToMarketPosition(BaseModel):
    symbol: str
    quantity: float
    average_price: float
    latest_price: float | None = None
    market_value: float | None = None
    unrealized_pnl: float | None = None
    error: str | None = None


class MarkToMarketResult(BaseModel):
    status: str
    environment: str
    cash: float
    nav: float
    positions_value: float
    positions: list[MarkToMarketPosition]
    errors: list[str]


class PortfolioConsistencyDiff(BaseModel):
    symbol: str
    rac_quantity: float
    broker_quantity: float
    quantity_diff: float
    rac_market_value: float
    broker_market_value: float
    market_value_diff: float
    severity: str
    reasons: list[str]


class PortfolioConsistencyResult(BaseModel):
    status: str
    environment: str
    quantity_tolerance: float
    market_value_tolerance: float
    diffs: list[PortfolioConsistencyDiff]
    block_order_execution: bool
