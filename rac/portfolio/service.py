from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.config import Settings, TradingMode
from rac.portfolio.models import MarkToMarketPosition, MarkToMarketResult
from rac.portfolio.repository import PortfolioRepository


class PortfolioMarkToMarketService:
    def __init__(
        self,
        settings: Settings,
        repository: PortfolioRepository,
        broker: AlpacaBrokerAdapter,
    ) -> None:
        self.settings = settings
        self.repository = repository
        self.broker = broker

    async def run(self, *, environment: str = "paper", timeframe: str = "1Day") -> MarkToMarketResult:
        if self.settings.trading_mode == TradingMode.LIVE:
            raise ValueError("live_mode_blocked_for_mark_to_market")

        cash = self.repository.current_cash(environment=environment)
        positions = self.repository.positions(environment=environment)
        if not positions:
            nav = cash
            self.repository.record_mark_to_market(
                environment=environment,
                cash=cash,
                valuations=[],
                errors=[],
                source="empty_portfolio",
            )
            return MarkToMarketResult(
                status="ok",
                environment=environment,
                cash=cash,
                nav=nav,
                positions_value=0.0,
                positions=[],
                errors=[],
            )

        valued: list[MarkToMarketPosition] = []
        errors: list[str] = []
        for position in positions:
            symbol = str(position["symbol"])
            quantity = float(position["quantity"])
            average_price = float(position["average_price"])
            try:
                bars = await self.broker.get_latest_bars(symbol=symbol, timeframe=timeframe, limit=1)
                if not bars:
                    raise RuntimeError("no_latest_bar")
                latest_price = float(bars[-1].close)
                market_value = quantity * latest_price
                valued.append(
                    MarkToMarketPosition(
                        symbol=symbol,
                        quantity=quantity,
                        average_price=average_price,
                        latest_price=latest_price,
                        market_value=market_value,
                        unrealized_pnl=(latest_price - average_price) * quantity,
                    )
                )
            except Exception as exc:
                error = f"{symbol}:{exc}"
                errors.append(error)
                valued.append(
                    MarkToMarketPosition(
                        symbol=symbol,
                        quantity=quantity,
                        average_price=average_price,
                        error=exc.__class__.__name__,
                    )
                )

        priced = [position for position in valued if position.market_value is not None]
        positions_value = sum(position.market_value or 0.0 for position in priced)
        nav = cash + positions_value
        if priced:
            self.repository.record_mark_to_market(
                environment=environment,
                cash=cash,
                valuations=[position.model_dump() for position in priced],
                errors=errors,
                source="alpaca_latest_bar",
            )
        return MarkToMarketResult(
            status="ok" if not errors else "degraded",
            environment=environment,
            cash=cash,
            nav=nav,
            positions_value=positions_value,
            positions=valued,
            errors=errors,
        )
