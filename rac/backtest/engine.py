from datetime import datetime
from typing import Any

from rac.backtest.metrics import compute_metrics
from rac.backtest.models import BacktestRequest, BacktestResult
from rac.backtest.portfolio import BacktestPortfolio
from rac.features.engine import FeatureEngine
from rac.strategies.mean_reversion import MeanReversionStrategy
from rac.strategies.models import SignalDirection
from rac.strategies.trend_following import TrendFollowingStrategy


class BacktestEngine:
    def run(self, request: BacktestRequest, bars: list[dict[str, Any]]) -> BacktestResult:
        if len(bars) < 5:
            raise ValueError(f"insufficient_data: need at least 5 bars, got {len(bars)}")

        symbol = request.symbol.upper()
        strategy = self._load_strategy(request.strategy_id)
        feature_engine = FeatureEngine()
        portfolio = BacktestPortfolio(
            initial_cash=request.initial_cash,
            slippage_pct=request.slippage_pct,
            commission_per_trade=request.commission_per_trade,
        )

        for i, bar in enumerate(bars):
            current_price = float(bar["close"])
            bar_time = bar["time"] if isinstance(bar["time"], datetime) else datetime.fromisoformat(str(bar["time"]))

            # SL/TP check antes de generar señal (usa precio de cierre de la barra actual)
            trigger = portfolio.check_sl_tp(symbol, current_price)
            if trigger:
                portfolio.close_position(symbol, current_price, bar_time, trigger, i)

            # Features walk-forward: todos los bars hasta i (inclusive)
            window = bars[: i + 1]
            feature_points = feature_engine.compute_technical_v1(
                window, feature_set=request.feature_set
            )
            if not feature_points:
                portfolio.mark_to_market(symbol, current_price, bar_time)
                continue

            # La estrategia necesita min_feature_points; pasamos todos los puntos
            # del window y tomamos solo la señal del bar actual (el último)
            feature_dicts = [
                {
                    "time": fp.time,
                    "symbol": fp.symbol,
                    "timeframe": fp.timeframe,
                    "feature_set": fp.feature_set,
                    "values": fp.values,
                }
                for fp in feature_points
            ]
            signals = strategy.generate(feature_dicts, environment="backtest")

            if signals:
                signal = signals[-1]
                if signal.direction == SignalDirection.BUY and not portfolio.has_position(symbol):
                    portfolio.open_position(
                        symbol=symbol,
                        price=current_price,
                        max_position_pct=signal.max_position_pct,
                        stop_loss_pct=signal.stop_loss_pct,
                        take_profit_pct=signal.take_profit_pct,
                        entry_time=bar_time,
                        bar_index=i,
                    )
                elif signal.direction == SignalDirection.SELL and portfolio.has_position(symbol):
                    portfolio.close_position(symbol, current_price, bar_time, "sell_signal", i)

            portfolio.mark_to_market(symbol, current_price, bar_time)

        # Cierre forzado al final del backtest
        if portfolio.has_position(symbol) and bars:
            last_bar = bars[-1]
            last_price = float(last_bar["close"])
            raw_time = last_bar["time"]
            last_time = raw_time if isinstance(raw_time, datetime) else datetime.fromisoformat(str(raw_time))
            portfolio.close_position(symbol, last_price, last_time, "end_of_backtest", len(bars) - 1)

        final_equity = portfolio.equity_curve[-1]["equity"] if portfolio.equity_curve else request.initial_cash
        metrics = compute_metrics(portfolio.equity_curve, portfolio.trades, request.initial_cash)

        return BacktestResult(
            backtest_id="",  # el repositorio asigna el ID al persistir
            strategy_id=request.strategy_id,
            symbol=symbol,
            timeframe=request.timeframe.upper(),
            start=request.start,
            end=request.end,
            initial_cash=request.initial_cash,
            final_equity=float(final_equity),
            bars_processed=len(bars),
            metrics=metrics,
            equity_curve=portfolio.equity_curve,
            trades=portfolio.trades,
        )

    @staticmethod
    def _load_strategy(strategy_id: str) -> TrendFollowingStrategy | MeanReversionStrategy:
        if strategy_id == "EQ_TREND_001":
            return TrendFollowingStrategy()
        if strategy_id == "EQ_REVERSION_001":
            return MeanReversionStrategy()
        raise ValueError(f"unsupported_strategy:{strategy_id}")
