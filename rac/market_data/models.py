from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class SourceQuality(StrEnum):
    RAW = "raw"
    VALIDATED = "validated"
    REJECTED = "rejected"


class OHLCVBar(BaseModel):
    time: datetime
    broker: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)
    source_quality: SourceQuality = SourceQuality.RAW

    @field_validator("symbol", "broker", "timeframe")
    @classmethod
    def normalize_upper(cls, value: str) -> str:
        return value.strip().upper()


class MarketDataIngestRequest(BaseModel):
    bars: list[OHLCVBar] = Field(min_length=1)


class MarketDataIngestResult(BaseModel):
    accepted: int
    rejected: int
    rejection_reasons: list[str]


class HistoricalFetchRequest(BaseModel):
    symbol: str = Field(min_length=1)
    timeframe: str = Field(default="1Day", min_length=1)
    start: datetime
    end: datetime

    def model_post_init(self, __context: object) -> None:
        if self.start >= self.end:
            raise ValueError("start must be before end")


class HistoricalFetchResult(BaseModel):
    symbol: str
    timeframe: str
    fetched: int
    accepted: int
    rejected: int
    pages: int

