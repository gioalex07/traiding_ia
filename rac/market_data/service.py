from rac.market_data.models import MarketDataIngestRequest, MarketDataIngestResult, SourceQuality
from rac.market_data.repository import MarketDataRepository
from rac.market_data.validation import MarketDataValidator


class MarketDataIngestor:
    def __init__(self, repository: MarketDataRepository, validator: MarketDataValidator | None = None) -> None:
        self.repository = repository
        self.validator = validator or MarketDataValidator()

    def ingest(self, request: MarketDataIngestRequest) -> MarketDataIngestResult:
        accepted = []
        rejection_reasons: list[str] = []

        for bar in request.bars:
            reasons = self.validator.validate_bar(bar)
            if reasons:
                rejection_reasons.extend([f"{bar.symbol}:{bar.time.isoformat()}:{reason}" for reason in reasons])
                continue
            accepted.append(bar.model_copy(update={"source_quality": SourceQuality.VALIDATED}))

        inserted = self.repository.upsert_ohlcv(accepted)
        return MarketDataIngestResult(
            accepted=inserted,
            rejected=len(request.bars) - inserted,
            rejection_reasons=rejection_reasons,
        )

