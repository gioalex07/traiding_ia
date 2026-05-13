"""LLM-based signal review layer.

Asks a local Gemma model to do a sanity-check on a trade signal before
execution. If Ollama is unavailable or too slow, falls back to passing
the signal through (execute=True).
"""
import json
import logging
import re
from dataclasses import dataclass
from typing import Any

from rac.local_ai.client import OllamaClient

log = logging.getLogger("rac.local_ai.reviewer")

_PREFERRED_MODELS = ["gemma3", "gemma", "qwen", "mistral", "llama"]

_PROMPT_TEMPLATE = """\
You are a risk filter for an algorithmic paper trading system.
Given a trade signal, decide whether to execute it based on the technical features.
Reply ONLY with valid JSON, no explanation outside the JSON.

Signal:
  symbol={symbol}  direction={direction}  ml_confidence={confidence:.2f}
  RSI={rsi:.1f}  MACD_hist={macd_hist:+.5f}  BB_%B={bb_pct_b:.2f}
  volatility_5={volatility:.5f}  return_1={return_1:+.4f}  close={close:.2f}

Rules you must apply:
- RSI > 75 → risky to BUY (overbought)
- RSI < 25 → risky to SELL (oversold)
- volatility_5 > 0.015 → high volatility, veto unless strong MACD
- MACD hist direction must align with signal direction
- If ml_confidence >= 0.85, trust the ML model unless a rule clearly vetoes

JSON format (execute must be true or false):
{{"execute": true, "reason": "one sentence"}}
"""


@dataclass(frozen=True)
class ReviewDecision:
    execute: bool
    reason: str
    model: str
    latency_ms: int
    source: str  # "llm" | "fallback"


class SignalReviewer:
    """Wraps OllamaClient to produce go/no-go decisions for signals."""

    def __init__(self, client: OllamaClient) -> None:
        self._client = client
        self._model: str | None = None

    def _resolve_model(self) -> str | None:
        if self._model:
            return self._model
        models = self._client.list_models()
        for keyword in _PREFERRED_MODELS:
            for m in models:
                if keyword in m.lower() and "embed" not in m.lower():
                    self._model = m
                    return m
        return None

    def review(self, values: dict[str, Any], direction: str, confidence: float, symbol: str) -> ReviewDecision:
        """Return a ReviewDecision. Falls back to execute=True on any error."""
        model = self._resolve_model()
        if not model:
            return ReviewDecision(execute=True, reason="no_llm_model", model="none", latency_ms=0, source="fallback")

        close = float(values.get("close") or 0)
        prompt = _PROMPT_TEMPLATE.format(
            symbol=symbol,
            direction=direction,
            confidence=confidence,
            rsi=float(values.get("rsi_14") or 50),
            macd_hist=float(values.get("macd_hist") or 0),
            bb_pct_b=float(values.get("bb_pct_b") or 0.5),
            volatility=float(values.get("volatility_5") or 0),
            return_1=float(values.get("return_1") or 0),
            close=close,
        )

        try:
            result = self._client.generate(model=model, prompt=prompt)
            decision = _parse_decision(result.response)
            log.info(
                "llm_review symbol=%s direction=%s execute=%s reason=%r latency=%dms model=%s",
                symbol, direction, decision["execute"], decision["reason"], result.latency_ms, model,
            )
            return ReviewDecision(
                execute=bool(decision["execute"]),
                reason=str(decision.get("reason", "")),
                model=model,
                latency_ms=result.latency_ms,
                source="llm",
            )
        except Exception as exc:
            log.warning("llm_review_error symbol=%s error=%s — passing through", symbol, exc)
            return ReviewDecision(execute=True, reason=str(exc), model=model, latency_ms=0, source="fallback")


def _parse_decision(response: str) -> dict[str, Any]:
    """Extract JSON from the LLM response, tolerating markdown fences."""
    text = response.strip()
    # Strip ```json ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.MULTILINE)
    text = re.sub(r"\s*```$", "", text, flags=re.MULTILINE)
    # Find the first {...} block
    match = re.search(r"\{[^{}]+\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"no_json_in_response: {text[:100]!r}")
    data = json.loads(match.group())
    if "execute" not in data:
        raise ValueError(f"missing_execute_key: {data}")
    return data
