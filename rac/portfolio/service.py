from typing import Any, cast

from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.brokers.base import Position
from rac.config import Settings, TradingMode
from rac.portfolio.models import (
    MarkToMarketPosition,
    MarkToMarketResult,
    PortfolioConsistencyDiff,
    PortfolioConsistencyResult,
)
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
            quantity = float(cast(Any, position["quantity"]))
            average_price = float(cast(Any, position["average_price"]))
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


class PortfolioConsistencyService:
    def __init__(
        self,
        repository: PortfolioRepository,
        broker: AlpacaBrokerAdapter,
    ) -> None:
        self.repository = repository
        self.broker = broker

    async def check(
        self,
        *,
        environment: str = "paper",
        quantity_tolerance: float = 0.000001,
        market_value_tolerance: float = 1.0,
    ) -> PortfolioConsistencyResult:
        rac_positions = {
            str(position["symbol"]).upper(): position
            for position in self.repository.positions(environment=environment)
        }
        broker_positions = {
            position.symbol.upper(): position
            for position in await self.broker.get_positions()
        }

        diffs: list[PortfolioConsistencyDiff] = []
        for symbol in sorted(set(rac_positions) | set(broker_positions)):
            rac_position = rac_positions.get(symbol)
            broker_position = broker_positions.get(symbol)
            diff = self._diff(
                symbol=symbol,
                rac_position=rac_position,
                broker_position=broker_position,
                quantity_tolerance=quantity_tolerance,
                market_value_tolerance=market_value_tolerance,
            )
            if diff.reasons:
                diffs.append(diff)

        has_blocking_diff = any(diff.severity == "blocked" for diff in diffs)
        status = "blocked" if has_blocking_diff else "degraded" if diffs else "ok"
        return PortfolioConsistencyResult(
            status=status,
            environment=environment,
            quantity_tolerance=quantity_tolerance,
            market_value_tolerance=market_value_tolerance,
            diffs=diffs,
            block_order_execution=has_blocking_diff,
        )

    @staticmethod
    def _diff(
        *,
        symbol: str,
        rac_position: dict[str, object] | None,
        broker_position: Position | None,
        quantity_tolerance: float,
        market_value_tolerance: float,
    ) -> PortfolioConsistencyDiff:
        rac_quantity = float(cast(Any, rac_position["quantity"])) if rac_position else 0.0
        rac_market_value = float(cast(Any, rac_position["market_value"])) if rac_position else 0.0
        broker_quantity = broker_position.quantity if broker_position else 0.0
        broker_market_value = broker_position.market_value if broker_position else 0.0
        quantity_diff = rac_quantity - broker_quantity
        market_value_diff = rac_market_value - broker_market_value
        reasons: list[str] = []

        if rac_position is None:
            reasons.append("missing_in_rac")
        if broker_position is None:
            reasons.append("missing_in_broker")
        if abs(quantity_diff) > quantity_tolerance:
            reasons.append("quantity_mismatch")
        if abs(market_value_diff) > market_value_tolerance:
            reasons.append("market_value_mismatch")

        severity = "blocked" if any(
            reason in {"missing_in_rac", "missing_in_broker", "quantity_mismatch"}
            for reason in reasons
        ) else "degraded" if reasons else "ok"
        return PortfolioConsistencyDiff(
            symbol=symbol,
            rac_quantity=rac_quantity,
            broker_quantity=broker_quantity,
            quantity_diff=quantity_diff,
            rac_market_value=rac_market_value,
            broker_market_value=broker_market_value,
            market_value_diff=market_value_diff,
            severity=severity,
            reasons=reasons,
        )
