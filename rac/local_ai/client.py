import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass


@dataclass(frozen=True)
class OllamaGenerateResult:
    response: str
    latency_ms: int


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: float = 10) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def list_models(self) -> list[str]:
        try:
            with urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=self.timeout_seconds) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            return []
        return [model["name"] for model in payload.get("models", []) if model.get("name")]

    def generate(self, *, model: str, prompt: str) -> OllamaGenerateResult:
        started = time.perf_counter()
        payload = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
            body = json.loads(response.read().decode("utf-8"))
        latency_ms = int((time.perf_counter() - started) * 1000)
        return OllamaGenerateResult(response=str(body.get("response", "")), latency_ms=latency_ms)

