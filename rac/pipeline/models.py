from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class PaperPipelineRequest(BaseModel):
    symbol: str = Field(default="AAPL", min_length=1)
    timeframe: str = Field(default="1Day", min_length=1)
    start: datetime
    end: datetime
    feature_set: str = Field(default="technical_v1", min_length=1)
    strategy_id: str = Field(default="trend_following_v1", min_length=1)
    limit: int = Field(default=300, ge=5, le=1000)
    explain: bool = True

    @field_validator("symbol")
    @classmethod
    def normalize_symbol(cls, value: str) -> str:
        return value.strip().upper()

    @field_validator("timeframe")
    @classmethod
    def normalize_timeframe(cls, value: str) -> str:
        return value.strip()

    def model_post_init(self, __context: object) -> None:
        if self.start >= self.end:
            raise ValueError("start must be before end")


class PaperPipelineResult(BaseModel):
    status: str
    symbol: str
    timeframe: str
    fetched: int
    accepted: int
    rejected: int
    features_computed: int
    signals_generated: int
    latest_signal_id: str | None = None
    latest_signal_direction: str | None = None
    ai_status: str | None = None
    ai_model_name: str | None = None
    ai_explanation: str | None = None
    order_execution: str = "not_requested"
