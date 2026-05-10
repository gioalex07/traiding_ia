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
