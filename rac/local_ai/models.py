from pydantic import BaseModel, Field


class LocalAICapabilities(BaseModel):
    runtime: str = "ollama"
    status: str
    base_url: str
    models: list[str] = []
    selected: dict[str, str | None] = {}
    reason: str | None = None


class ExplainSignalRequest(BaseModel):
    signal_id: str = Field(min_length=1)


class ExplainSignalResult(BaseModel):
    status: str
    signal_id: str
    model_name: str | None
    explanation: str | None
    reason: str | None = None

