import unittest
from datetime import UTC, datetime, timedelta

from rac.market_data.loader import HistoricalDataLoader
from rac.market_data.models import HistoricalFetchRequest, OHLCVBar


def _bar(t: datetime, close: float = 100.0) -> OHLCVBar:
    return OHLCVBar(
        time=t,
        broker="alpaca",
        symbol="AAPL",
        timeframe="1Day",
        open=close * 0.99,
        high=close * 1.01,
        low=close * 0.98,
        close=close,
        volume=1_000_000.0,
    )


class FakeBroker:
    """Simulates AlpacaBrokerAdapter.get_historical_bars with configurable pages."""

    def __init__(self, pages: list[list[OHLCVBar]]) -> None:
        self._pages = pages

    async def get_historical_bars(self, **_: object) -> tuple[list[OHLCVBar], int]:
        all_bars = [bar for page in self._pages for bar in page]
        return all_bars, len(self._pages)


class FakeMarketDataRepository:
    def __init__(self) -> None:
        self.stored: list[object] = []

    def upsert_ohlcv(self, bars: list[object]) -> int:
        self.stored.extend(bars)
        return len(bars)


class HistoricalLoaderTest(unittest.IsolatedAsyncioTestCase):
    def _request(self) -> HistoricalFetchRequest:
        start = datetime(2026, 1, 2, tzinfo=UTC)
        return HistoricalFetchRequest(
            symbol="AAPL",
            timeframe="1Day",
            start=start,
            end=start + timedelta(days=30),
        )

    def _make_bars(self, n: int) -> list[OHLCVBar]:
        base = datetime(2026, 1, 2, tzinfo=UTC)
        return [_bar(base + timedelta(days=i), 100.0 + i) for i in range(n)]

    async def test_single_page_fetched_and_stored(self) -> None:
        bars = self._make_bars(5)
        repo = FakeMarketDataRepository()
        broker = FakeBroker([bars])
        loader = HistoricalDataLoader(broker=broker, repository=repo)  # type: ignore[arg-type]

        result = await loader.fetch_and_store(self._request())

        self.assertEqual(result.fetched, 5)
        self.assertEqual(result.accepted, 5)
        self.assertEqual(result.rejected, 0)
        self.assertEqual(result.pages, 1)
        self.assertEqual(result.symbol, "AAPL")

    async def test_two_pages_accumulates_all_bars(self) -> None:
        page1 = self._make_bars(3)
        page2 = self._make_bars(2)
        repo = FakeMarketDataRepository()
        broker = FakeBroker([page1, page2])
        loader = HistoricalDataLoader(broker=broker, repository=repo)  # type: ignore[arg-type]

        result = await loader.fetch_and_store(self._request())

        self.assertEqual(result.fetched, 5)
        self.assertEqual(result.pages, 2)
        self.assertEqual(result.accepted, 5)

    async def test_empty_response_returns_zero(self) -> None:
        repo = FakeMarketDataRepository()
        broker = FakeBroker([[]])
        loader = HistoricalDataLoader(broker=broker, repository=repo)  # type: ignore[arg-type]

        result = await loader.fetch_and_store(self._request())

        self.assertEqual(result.fetched, 0)
        self.assertEqual(result.accepted, 0)
        self.assertEqual(result.pages, 1)

    async def test_large_batch_splits_into_chunks(self) -> None:
        # 6001 bars — debe dividirse en 2 batches de 5000 y 1001
        bars = self._make_bars(6001)
        repo = FakeMarketDataRepository()
        broker = FakeBroker([bars])
        loader = HistoricalDataLoader(broker=broker, repository=repo)  # type: ignore[arg-type]

        result = await loader.fetch_and_store(self._request())

        self.assertEqual(result.fetched, 6001)
        self.assertEqual(result.accepted, 6001)
        # El repo recibe las barras en dos llamadas pero el total es correcto
        self.assertEqual(len(repo.stored), 6001)


class HistoricalFetchRequestTest(unittest.TestCase):
    def test_rejects_start_after_end(self) -> None:
        with self.assertRaises(ValueError):
            HistoricalFetchRequest(
                symbol="AAPL",
                timeframe="1Day",
                start=datetime(2026, 5, 9, tzinfo=UTC),
                end=datetime(2026, 1, 1, tzinfo=UTC),
            )

    def test_rejects_start_equal_to_end(self) -> None:
        t = datetime(2026, 5, 9, tzinfo=UTC)
        with self.assertRaises(ValueError):
            HistoricalFetchRequest(symbol="AAPL", timeframe="1Day", start=t, end=t)

    def test_accepts_valid_range(self) -> None:
        req = HistoricalFetchRequest(
            symbol="AAPL",
            timeframe="1Day",
            start=datetime(2026, 1, 1, tzinfo=UTC),
            end=datetime(2026, 5, 9, tzinfo=UTC),
        )
        self.assertEqual(req.symbol, "AAPL")


if __name__ == "__main__":
    unittest.main()
