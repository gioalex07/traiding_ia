import math
from statistics import mean, pstdev
from typing import Any

from rac.backtest.models import BacktestMetrics, BacktestTrade


def compute_metrics(
    equity_curve: list[dict[str, Any]],
    trades: list[BacktestTrade],
    initial_cash: float,
) -> BacktestMetrics:
    final_equity = float(equity_curve[-1]["equity"]) if equity_curve else initial_cash
    total_return_pct = (final_equity - initial_cash) / initial_cash * 100.0

    max_drawdown_pct = _max_drawdown(equity_curve)
    sharpe = _sharpe(equity_curve)

    completed = [t for t in trades if t.pnl is not None]
    wins = [t for t in completed if t.pnl > 0]
    losses = [t for t in completed if t.pnl <= 0]

    win_rate = len(wins) / len(completed) * 100.0 if completed else 0.0
    avg_win = mean(t.pnl_pct for t in wins) if wins else 0.0
    avg_loss = mean(abs(t.pnl_pct) for t in losses) if losses else 0.0

    gross_profit = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0.0

    return BacktestMetrics(
        total_return_pct=round(total_return_pct, 4),
        max_drawdown_pct=round(max_drawdown_pct, 4),
        sharpe_ratio=round(sharpe, 4),
        win_rate_pct=round(win_rate, 4),
        profit_factor=round(profit_factor, 4),
        total_trades=len(completed),
        winning_trades=len(wins),
        losing_trades=len(losses),
        avg_win_pct=round(avg_win, 4),
        avg_loss_pct=round(avg_loss, 4),
    )


def _max_drawdown(equity_curve: list[dict[str, Any]]) -> float:
    if len(equity_curve) < 2:
        return 0.0
    peak = float(equity_curve[0]["equity"])
    max_dd = 0.0
    for point in equity_curve:
        eq = float(point["equity"])
        if eq > peak:
            peak = eq
        if peak > 0:
            dd = (peak - eq) / peak * 100.0
            max_dd = max(max_dd, dd)
    return max_dd


def _sharpe(equity_curve: list[dict[str, Any]], risk_free: float = 0.0) -> float:
    if len(equity_curve) < 2:
        return 0.0
    equities = [float(p["equity"]) for p in equity_curve]
    returns = [
        (equities[i] - equities[i - 1]) / equities[i - 1]
        for i in range(1, len(equities))
        if equities[i - 1] != 0
    ]
    if len(returns) < 2:
        return 0.0
    avg_r = mean(returns) - risk_free
    std_r = pstdev(returns)
    if std_r == 0:
        return 0.0
    # Annualise: sqrt(bars_per_year) — usar 252*390 para 1Min, 252 para 1Day
    bars_per_year = len(returns)  # simplificado: normalizar por raíz de la muestra
    return avg_r / std_r * math.sqrt(bars_per_year)
