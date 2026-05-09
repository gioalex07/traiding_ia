from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class SignalDirection(StrEnum):
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"


class StrategyManifest(BaseModel):
    strategy_id: str = Field(min_length=1)
    version: str = Field(min_length=1)
    required_features: list[str] = Field(min_length=1)
    stop_loss_pct: float = Field(gt=0)
    take_profit_pct: float = Field(gt=0)
    max_position_pct: float = Field(gt=0)
    invalidation_rules: list[str] = Field(min_length=1)
    min_feature_points: int = Field(default=5, ge=1)

    @field_validator("required_features", "invalidation_rules")
    @classmethod
    def no_blank_values(cls, values: list[str]) -> list[str]:
        if any(not value.strip() for value in values):
            raise ValueError("blank values are not allowed")
        return values


class Signal(BaseModel):
    time: datetime
    environment: str
    strategy_id: str
    strategy_version: str
    symbol: str
    timeframe: str
    direction: SignalDirection
    confidence: float = Field(ge=0, le=1)
    stop_loss_pct: float = Field(gt=0)
    take_profit_pct: float = Field(gt=0)
    max_position_pct: float = Field(gt=0)
    invalidation_rules: list[str]
    raw_payload: dict[str, object]


class SignalGenerateRequest(BaseModel):
    symbol: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)
    feature_set: str = Field(default="technical_v1", min_length=1)
    strategy_id: str = Field(default="trend_following_v1", min_length=1)
    limit: int = Field(default=100, ge=5, le=1000)


class SignalGenerateResult(BaseModel):
    generated: int
    strategy_id: str
    symbol: str
    timeframe: str
    signals: list[Signal]

