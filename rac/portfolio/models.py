from pydantic import BaseModel


class PortfolioSnapshot(BaseModel):
    environment: str
    nav: float
    cash: float
    pnl_daily: float
    drawdown: float
    exposure: dict[str, float]

