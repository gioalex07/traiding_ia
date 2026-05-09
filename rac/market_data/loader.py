
from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.market_data.models import (
    HistoricalFetchRequest,
    HistoricalFetchResult,
    MarketDataIngestRequest,
)
from rac.market_data.repository import MarketDataRepository
from rac.market_data.service import MarketDataIngestor

_INGEST_BATCH = 5_000


class HistoricalDataLoader:
    """Fetches historical bars from Alpaca (paginated) and ingests them into the DB."""

    def __init__(self, broker: AlpacaBrokerAdapter, repository: MarketDataRepository) -> None:
        self.broker = broker
        self.repository = repository

    async def fetch_and_store(self, request: HistoricalFetchRequest) -> HistoricalFetchResult:
        bars, pages = await self.broker.get_historical_bars(
            symbol=request.symbol,
            timeframe=request.timeframe,
            start=request.start,
            end=request.end,
        )

        ingestor = MarketDataIngestor(self.repository)
        total_accepted = total_rejected = 0

        for i in range(0, max(len(bars), 1), _INGEST_BATCH):
            batch = bars[i : i + _INGEST_BATCH]
            if not batch:
                break
            result = ingestor.ingest(MarketDataIngestRequest(bars=batch))
            total_accepted += result.accepted
            total_rejected += result.rejected

        return HistoricalFetchResult(
            symbol=request.symbol.upper(),
            timeframe=request.timeframe.upper(),
            fetched=len(bars),
            accepted=total_accepted,
            rejected=total_rejected,
            pages=pages,
        )
