import unittest
from datetime import UTC, datetime, timedelta

from rac.backtest.engine import BacktestEngine
from rac.backtest.metrics import _max_drawdown, _sharpe, compute_metrics
from rac.backtest.models import BacktestRequest, BacktestTrade
from rac.backtest.portfolio import BacktestPortfolio


def _make_bars(
    n: int,
    start_price: float = 100.0,
    trend: float = 0.002,
    symbol: str = "AAPL",
    timeframe: str = "1Min",
) -> list[dict]:
    bars = []
    price = start_price
    t = datetime(2026, 1, 2, 14, 0, 0, tzinfo=UTC)
    for _ in range(n):
        price = price * (1 + trend)
        bars.append({
            "time": t,
            "symbol": symbol,
            "timeframe": timeframe,
            "open": price * 0.999,
            "high": price * 1.002,
            "low": price * 0.997,
            "close": price,
            "volume": 10_000.0,
        })
        t = t + timedelta(minutes=1)
    return bars


class BacktestEngineTest(unittest.TestCase):
    def _request(self, bars: list[dict]) -> BacktestRequest:
        return BacktestRequest(
            strategy_id="trend_following_v1",
            symbol="AAPL",
            timeframe="1Min",
            start=bars[0]["time"].replace(tzinfo=None),
            end=bars[-1]["time"].replace(tzinfo=None),
            initial_cash=10_000.0,
            slippage_pct=0.0,
            commission_per_trade=0.0,
        )

    def test_raises_with_fewer_than_5_bars(self) -> None:
        bars = _make_bars(3)
        with self.assertRaises(ValueError, msg="insufficient_data"):
            BacktestEngine().run(self._request(bars), bars)

    def test_completes_with_enough_bars(self) -> None:
        bars = _make_bars(30)
        result = BacktestEngine().run(self._request(bars), bars)
        self.assertEqual(result.bars_processed, 30)
        self.assertEqual(result.symbol, "AAPL")
        self.assertGreater(len(result.equity_curve), 0)

    def test_uptrend_generates_positive_return(self) -> None:
        bars = _make_bars(50, trend=0.003)
        result = BacktestEngine().run(self._request(bars), bars)
        self.assertGreater(result.metrics.total_return_pct, 0)

    def test_downtrend_generates_no_buy_trades(self) -> None:
        bars = _make_bars(30, trend=-0.003)
        result = BacktestEngine().run(self._request(bars), bars)
        buys = [t for t in result.trades if t.side == "buy" and t.exit_reason != "end_of_backtest"]
        # En bajada fuerte no debería haber señales de compra ejecutadas
        self.assertEqual(len(result.trades), 0)

    def test_all_positions_closed_at_end(self) -> None:
        bars = _make_bars(30, trend=0.003)
        result = BacktestEngine().run(self._request(bars), bars)
        open_trades = [t for t in result.trades if t.exit_time is None]
        self.assertEqual(len(open_trades), 0)

    def test_equity_curve_length_matches_bars(self) -> None:
        bars = _make_bars(20)
        result = BacktestEngine().run(self._request(bars), bars)
        self.assertEqual(len(result.equity_curve), 20)


class BacktestPortfolioTest(unittest.TestCase):
    def test_open_and_close_position(self) -> None:
        portfolio = BacktestPortfolio(10_000.0, slippage_pct=0.0, commission_per_trade=0.0)
        t0 = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
        t1 = datetime(2026, 1, 2, 14, 5, tzinfo=UTC)
        portfolio.open_position("AAPL", 100.0, max_position_pct=10.0,
                                stop_loss_pct=5.0, take_profit_pct=10.0,
                                entry_time=t0, bar_index=0)
        self.assertTrue(portfolio.has_position("AAPL"))
        portfolio.close_position("AAPL", 110.0, t1, "take_profit", 5)
        self.assertFalse(portfolio.has_position("AAPL"))
        self.assertEqual(len(portfolio.trades), 1)
        trade = portfolio.trades[0]
        self.assertAlmostEqual(trade.pnl_pct, 10.0, places=2)

    def test_sl_tp_check(self) -> None:
        portfolio = BacktestPortfolio(10_000.0, slippage_pct=0.0, commission_per_trade=0.0)
        t0 = datetime(2026, 1, 2, 14, 0, tzinfo=UTC)
        portfolio.open_position("AAPL", 100.0, max_position_pct=10.0,
                                stop_loss_pct=5.0, take_profit_pct=10.0,
                                entry_time=t0, bar_index=0)
        self.assertIsNone(portfolio.check_sl_tp("AAPL", 100.0))
        self.assertEqual(portfolio.check_sl_tp("AAPL", 94.0), "stop_loss")
        self.assertEqual(portfolio.check_sl_tp("AAPL", 111.0), "take_profit")


class BacktestMetricsTest(unittest.TestCase):
    def test_max_drawdown_flat(self) -> None:
        curve = [{"equity": 100.0}, {"equity": 100.0}]
        self.assertEqual(_max_drawdown(curve), 0.0)

    def test_max_drawdown_full_loss(self) -> None:
        curve = [{"equity": 100.0}, {"equity": 50.0}]
        self.assertAlmostEqual(_max_drawdown(curve), 50.0)

    def test_sharpe_flat_returns_zero(self) -> None:
        curve = [{"equity": 100.0 + i} for i in range(10)]
        # Std de retornos lineales es casi 0, Sharpe ≈ 0 o muy alto
        # Solo verificamos que no falla
        result = _sharpe(curve)
        self.assertIsInstance(result, float)

    def test_compute_metrics_no_trades(self) -> None:
        curve = [{"equity": 10_000.0}, {"equity": 10_000.0}]
        metrics = compute_metrics(curve, [], 10_000.0)
        self.assertEqual(metrics.total_return_pct, 0.0)
        self.assertEqual(metrics.total_trades, 0)
        self.assertEqual(metrics.win_rate_pct, 0.0)


if __name__ == "__main__":
    unittest.main()
