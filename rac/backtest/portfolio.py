from dataclasses import dataclass, field
from datetime import datetime

from rac.backtest.models import BacktestTrade


@dataclass
class _OpenPosition:
    symbol: str
    quantity: float
    entry_price: float
    entry_time: datetime
    stop_loss: float | None
    take_profit: float | None
    entry_bar: int


class BacktestPortfolio:
    def __init__(
        self,
        initial_cash: float,
        slippage_pct: float,
        commission_per_trade: float,
    ) -> None:
        self.cash = initial_cash
        self.initial_cash = initial_cash
        self._slippage = slippage_pct / 100.0
        self._commission = commission_per_trade
        self._position: _OpenPosition | None = None
        self.trades: list[BacktestTrade] = []
        self.equity_curve: list[dict[str, object]] = []

    # ------------------------------------------------------------------
    def has_position(self, symbol: str) -> bool:
        return self._position is not None and self._position.symbol == symbol

    def open_position(
        self,
        symbol: str,
        price: float,
        max_position_pct: float,
        stop_loss_pct: float,
        take_profit_pct: float,
        entry_time: datetime,
        bar_index: int,
    ) -> None:
        fill_price = price * (1 + self._slippage)
        notional = self.cash * (max_position_pct / 100.0)
        quantity = notional / fill_price
        cost = notional + self._commission

        if cost > self.cash or quantity <= 0:
            return

        self.cash -= cost
        sl = fill_price * (1 - stop_loss_pct / 100.0)
        tp = fill_price * (1 + take_profit_pct / 100.0)
        self._position = _OpenPosition(
            symbol=symbol,
            quantity=quantity,
            entry_price=fill_price,
            entry_time=entry_time,
            stop_loss=sl,
            take_profit=tp,
            entry_bar=bar_index,
        )

    def close_position(
        self,
        symbol: str,
        price: float,
        exit_time: datetime,
        reason: str,
        bar_index: int,
    ) -> None:
        pos = self._position
        if pos is None or pos.symbol != symbol:
            return

        fill_price = price * (1 - self._slippage)
        proceeds = fill_price * pos.quantity - self._commission
        self.cash += proceeds

        cost_basis = pos.entry_price * pos.quantity
        pnl = proceeds - cost_basis
        pnl_pct = pnl / cost_basis * 100.0 if cost_basis else 0.0

        self.trades.append(BacktestTrade(
            entry_time=pos.entry_time,
            exit_time=exit_time,
            symbol=symbol,
            side="buy",
            quantity=pos.quantity,
            entry_price=pos.entry_price,
            exit_price=fill_price,
            pnl=pnl,
            pnl_pct=pnl_pct,
            exit_reason=reason,
            bars_held=bar_index - pos.entry_bar,
        ))
        self._position = None

    def check_sl_tp(self, symbol: str, current_price: float) -> str | None:
        pos = self._position
        if pos is None or pos.symbol != symbol:
            return None
        if pos.stop_loss and current_price <= pos.stop_loss:
            return "stop_loss"
        if pos.take_profit and current_price >= pos.take_profit:
            return "take_profit"
        return None

    def mark_to_market(self, symbol: str, price: float, time: datetime) -> float:
        pos_value = 0.0
        if self._position and self._position.symbol == symbol:
            pos_value = self._position.quantity * price
        equity = self.cash + pos_value
        self.equity_curve.append({"time": time.isoformat(), "equity": equity})
        return equity
