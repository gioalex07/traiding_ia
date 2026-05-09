from rac.config import Settings
from rac.local_ai.client import OllamaClient
from rac.local_ai.models import ExplainSignalResult, LocalAICapabilities
from rac.local_ai.repository import AIInteractionRepository
from rac.strategies.repository import SignalRepository


PROMPT_TEMPLATE_ID = "explain_signal_v1"
PROMPT_VERSION = "0.1.0"


class LocalAIService:
    def __init__(
        self,
        settings: Settings,
        client: OllamaClient | None = None,
        repository: AIInteractionRepository | None = None,
    ) -> None:
        self.settings = settings
        self.client = client or OllamaClient(settings.ollama_base_url, timeout_seconds=120)
        self.repository = repository

    def capabilities(self) -> LocalAICapabilities:
        models = self.client.list_models()
        if not models:
            return LocalAICapabilities(
                status="disabled",
                base_url=self.settings.ollama_base_url.rstrip("/"),
                reason="no_ollama_models_detected",
            )
        selected = {
            "analysis": self._select_model(models),
            "summary": self._select_model(models),
            "classification": self._select_model(models),
            "technical_reasoning": self._select_model(models),
            "embeddings": self._select_embedding_model(models),
        }
        return LocalAICapabilities(
            status="available",
            base_url=self.settings.ollama_base_url.rstrip("/"),
            models=models,
            selected=selected,
        )

    def explain_signal(self, *, signal_id: str, signal_repository: SignalRepository) -> ExplainSignalResult:
        capabilities = self.capabilities()
        model_name = capabilities.selected.get("analysis") if capabilities.selected else None
        signal = signal_repository.get_signal(signal_id)
        if signal is None:
            return ExplainSignalResult(
                status="not_found",
                signal_id=signal_id,
                model_name=model_name,
                explanation=None,
                reason="signal_not_found",
            )
        prompt = self._build_signal_prompt(signal)
        if capabilities.status != "available" or not model_name:
            self._record(
                signal_id=signal_id,
                model_name=model_name,
                prompt=prompt,
                response=None,
                status="disabled",
                error=capabilities.reason,
            )
            return ExplainSignalResult(
                status="disabled",
                signal_id=signal_id,
                model_name=model_name,
                explanation=None,
                reason=capabilities.reason,
            )
        try:
            generated = self.client.generate(model=model_name, prompt=prompt)
        except Exception as exc:
            self._record(
                signal_id=signal_id,
                model_name=model_name,
                prompt=prompt,
                response=None,
                status="error",
                error=exc.__class__.__name__,
            )
            return ExplainSignalResult(
                status="error",
                signal_id=signal_id,
                model_name=model_name,
                explanation=None,
                reason=exc.__class__.__name__,
            )
        self._record(
            signal_id=signal_id,
            model_name=model_name,
            prompt=prompt,
            response=generated.response,
            status="ok",
            latency_ms=generated.latency_ms,
        )
        return ExplainSignalResult(
            status="ok",
            signal_id=signal_id,
            model_name=model_name,
            explanation=generated.response,
        )

    def _record(
        self,
        *,
        signal_id: str,
        model_name: str | None,
        prompt: str,
        response: str | None,
        status: str,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        if not self.repository:
            return
        self.repository.record(
            environment=self.settings.trading_mode.value,
            interaction_type="explain_signal",
            prompt_template_id=PROMPT_TEMPLATE_ID,
            prompt_version=PROMPT_VERSION,
            model_name=model_name,
            input_ref=signal_id,
            prompt=prompt,
            response=response,
            status=status,
            latency_ms=latency_ms,
            error=error,
        )

    @staticmethod
    def _select_model(models: list[str]) -> str | None:
        preferred_keywords = ["llama", "qwen", "mistral", "gemma"]
        for keyword in preferred_keywords:
            for model in models:
                if keyword in model.lower() and "embed" not in model.lower():
                    return model
        return next((model for model in models if "embed" not in model.lower()), models[0] if models else None)

    @staticmethod
    def _select_embedding_model(models: list[str]) -> str | None:
        return next((model for model in models if "embed" in model.lower()), None)

    @staticmethod
    def _build_signal_prompt(signal: dict[str, object]) -> str:
        return (
            "Eres un asistente local de analisis financiero para RAC. "
            "Explica esta senal para revision humana. No recomiendes ejecutar dinero real, "
            "no prometas rentabilidad, no modifiques reglas de riesgo y no inventes condiciones "
            "que no esten en los datos de entrada.\n\n"
            f"Signal ID: {signal['id']}\n"
            f"Environment: {signal['environment']}\n"
            f"Strategy: {signal['strategy_id']} {signal['strategy_version']}\n"
            f"Symbol: {signal['symbol']} {signal['timeframe']}\n"
            f"Direction: {signal['direction']}\n"
            f"Confidence: {signal['confidence']}\n"
            f"Risk: stop_loss_pct={signal['stop_loss_pct']}, "
            f"take_profit_pct={signal['take_profit_pct']}, max_position_pct={signal['max_position_pct']}\n"
            f"Features: {signal['raw_payload']}\n\n"
            "Devuelve un resumen breve con: razon de la senal, riesgos, condiciones de invalidacion "
            "copiadas solo desde invalidation_rules si existen, y controles humanos recomendados. "
            "Si falta informacion, dilo explicitamente."
        )
