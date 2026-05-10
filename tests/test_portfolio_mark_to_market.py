import unittest
from dataclasses import dataclass
from decimal import Decimal

from rac.brokers.base import Position
from rac.config import load_settings
from rac.portfolio.repository import _daily_pnl, _drawdown_pct
from rac.portfolio.service import PortfolioConsistencyService, PortfolioMarkToMarketService


@dataclass(frozen=True)
class FakeBar:
    close: float


class FakeBroker:
    async def get_latest_bars(self, symbol: str, timeframe: str, limit: int = 1) -> list[FakeBar]:
        return [FakeBar(close=110.0)]

    async def get_positions(self) -> list[Position]:
        return [Position(symbol="AAPL", quantity=2.0, market_value=200.0)]


class FakePortfolioRepository:
    def __init__(self) -> None:
        self.recorded = None

    def current_cash(self, environment: str = "paper") -> float:
        return 1_000.0

    def positions(self, environment: str = "paper") -> list[dict[str, object]]:
        return [
            {
                "symbol": "AAPL",
                "quantity": 2.0,
                "average_price": 100.0,
                "market_value": 200.0,
            }
        ]

    def record_mark_to_market(self, **kwargs: object) -> None:
        self.recorded = kwargs


class PortfolioMarkToMarketServiceTest(unittest.IsolatedAsyncioTestCase):
    async def test_values_positions_without_order_execution(self) -> None:
        repository = FakePortfolioRepository()
        result = await PortfolioMarkToMarketService(
            settings=load_settings(),
            repository=repository,  # type: ignore[arg-type]
            broker=FakeBroker(),  # type: ignore[arg-type]
        ).run(environment="paper", timeframe="1Day")

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.nav, 1220.0)
        self.assertEqual(result.positions_value, 220.0)
        self.assertEqual(result.positions[0].unrealized_pnl, 20.0)
        self.assertIsNotNone(repository.recorded)

    async def test_consistency_ok_when_quantities_match(self) -> None:
        result = await PortfolioConsistencyService(
            repository=FakePortfolioRepository(),  # type: ignore[arg-type]
            broker=FakeBroker(),  # type: ignore[arg-type]
        ).check(environment="paper")

        self.assertEqual(result.status, "ok")
        self.assertFalse(result.block_order_execution)
        self.assertEqual(result.diffs, [])

    async def test_consistency_blocks_missing_broker_position(self) -> None:
        class EmptyBroker(FakeBroker):
            async def get_positions(self) -> list[Position]:
                return []

        result = await PortfolioConsistencyService(
            repository=FakePortfolioRepository(),  # type: ignore[arg-type]
            broker=EmptyBroker(),  # type: ignore[arg-type]
        ).check(environment="paper")

        self.assertEqual(result.status, "blocked")
        self.assertTrue(result.block_order_execution)
        self.assertEqual(result.diffs[0].symbol, "AAPL")
        self.assertIn("missing_in_broker", result.diffs[0].reasons)


class DailyPnlTest(unittest.TestCase):
    """Tests for _daily_pnl — uses a fake cursor to avoid DB dependency."""

    def _cursor(self, baseline_nav: float | None) -> object:
        class FakeCursor:
            def __init__(self, nav: float | None) -> None:
                self._nav = nav

            def execute(self, *_: object, **__: object) -> None:
                pass

            def fetchone(self) -> tuple | None:
                return (self._nav,) if self._nav is not None else None

        return FakeCursor(baseline_nav)

    def test_no_prior_snapshot_returns_zero(self) -> None:
        result = _daily_pnl(self._cursor(None), "paper", Decimal("100000"))
        self.assertEqual(result, Decimal("0"))

    def test_gain_day(self) -> None:
        result = _daily_pnl(self._cursor(100_000.0), "paper", Decimal("101500"))
        self.assertEqual(result, Decimal("1500"))

    def test_loss_day(self) -> None:
        result = _daily_pnl(self._cursor(100_000.0), "paper", Decimal("98000"))
        self.assertEqual(result, Decimal("-2000"))

    def test_flat_day(self) -> None:
        result = _daily_pnl(self._cursor(100_000.0), "paper", Decimal("100000"))
        self.assertEqual(result, Decimal("0"))


class DrawdownPctTest(unittest.TestCase):
    """Tests for _drawdown_pct — uses a fake cursor to avoid DB dependency."""

    def _cursor(self, peak_nav: float | None) -> object:
        class FakeCursor:
            def __init__(self, nav: float | None) -> None:
                self._nav = nav

            def execute(self, *_: object, **__: object) -> None:
                pass

            def fetchone(self) -> tuple | None:
                return (self._nav,) if self._nav is not None else None

        return FakeCursor(peak_nav)

    def test_no_history_returns_zero(self) -> None:
        result = _drawdown_pct(self._cursor(None), "paper", Decimal("100000"))
        self.assertEqual(result, Decimal("0"))

    def test_at_peak_returns_zero(self) -> None:
        result = _drawdown_pct(self._cursor(100_000.0), "paper", Decimal("100000"))
        self.assertEqual(result, Decimal("0"))

    def test_new_high_returns_zero(self) -> None:
        result = _drawdown_pct(self._cursor(100_000.0), "paper", Decimal("105000"))
        self.assertEqual(result, Decimal("0"))

    def test_ten_percent_drawdown(self) -> None:
        result = _drawdown_pct(self._cursor(100_000.0), "paper", Decimal("90000"))
        self.assertAlmostEqual(float(result), 10.0, places=4)

    def test_zero_peak_returns_zero(self) -> None:
        result = _drawdown_pct(self._cursor(0.0), "paper", Decimal("50000"))
        self.assertEqual(result, Decimal("0"))


if __name__ == "__main__":
    unittest.main()
