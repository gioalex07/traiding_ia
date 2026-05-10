import unittest
from dataclasses import dataclass

from rac.config import load_settings
from rac.portfolio.service import PortfolioMarkToMarketService


@dataclass(frozen=True)
class FakeBar:
    close: float


class FakeBroker:
    async def get_latest_bars(self, symbol: str, timeframe: str, limit: int = 1) -> list[FakeBar]:
        return [FakeBar(close=110.0)]


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


if __name__ == "__main__":
    unittest.main()
