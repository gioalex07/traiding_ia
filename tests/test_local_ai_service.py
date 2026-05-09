import unittest
from datetime import UTC, datetime
from uuid import uuid4

from rac.config import load_settings
from rac.local_ai.client import OllamaGenerateResult
from rac.local_ai.service import LocalAIService


class FakeOllamaClient:
    def __init__(self, models: list[str]) -> None:
        self.models = models

    def list_models(self) -> list[str]:
        return self.models

    def generate(self, *, model: str, prompt: str) -> OllamaGenerateResult:
        return OllamaGenerateResult(response=f"model={model}; prompt={len(prompt)}", latency_ms=1)


class FakeSignalRepository:
    def get_signal(self, signal_id: str) -> dict[str, object] | None:
        return {
            "id": signal_id,
            "time": datetime.now(UTC),
            "environment": "paper",
            "strategy_id": "trend_following_v1",
            "strategy_version": "0.1.0",
            "symbol": "AAPL",
            "timeframe": "1MIN",
            "direction": "buy",
            "confidence": 0.5,
            "stop_loss_pct": 1.5,
            "take_profit_pct": 3.0,
            "max_position_pct": 2.0,
            "raw_payload": {"values": {"close": 100}},
        }


class LocalAIServiceTest(unittest.TestCase):
    def test_reports_disabled_without_models(self) -> None:
        service = LocalAIService(load_settings(), client=FakeOllamaClient([]))

        capabilities = service.capabilities()

        self.assertEqual(capabilities.status, "disabled")
        self.assertEqual(capabilities.models, [])

    def test_explains_signal_with_selected_local_model(self) -> None:
        service = LocalAIService(load_settings(), client=FakeOllamaClient(["nomic-embed-text", "llama3.2"]))
        signal_id = str(uuid4())

        result = service.explain_signal(signal_id=signal_id, signal_repository=FakeSignalRepository())

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.model_name, "llama3.2")
        self.assertIn("model=llama3.2", result.explanation or "")


if __name__ == "__main__":
    unittest.main()
