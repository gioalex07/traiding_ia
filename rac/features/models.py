from datetime import datetime

from pydantic import BaseModel, Field


class FeatureComputeRequest(BaseModel):
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    limit: int = Field(default=100, ge=3, le=1000)
    feature_set: str = Field(default="technical_v1", min_length=1)


class FeaturePoint(BaseModel):
    time: datetime
    symbol: str
    timeframe: str
    feature_set: str
    values: dict[str, float | None]
    source_bar_count: int


class FeatureComputeResult(BaseModel):
    computed: int
    feature_set: str
    symbol: str
    timeframe: str

