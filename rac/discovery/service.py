import json
import os
import platform
import shutil
import socket
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urlparse

from rac.config import BrokerName, Settings, TradingMode


@dataclass(frozen=True)
class CapabilityReport:
    environment: str
    trading_mode: str
    live_trading_enabled: bool
    live_trading_status: str
    broker_configured: str
    broker_status: str
    order_execution: str
    hardware: dict[str, object]
    services: dict[str, object]
    local_ai: dict[str, object]
    degraded_reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class EnvironmentDiscoveryService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def detect(self) -> CapabilityReport:
        degraded_reasons: list[str] = []
        hardware = self._detect_hardware()
        services = self._detect_services()
        local_ai = self._detect_ollama()
        broker, broker_status = self._detect_broker()

        if broker_status in {"not_configured", "live_blocked"}:
            degraded_reasons.append(f"broker:{broker_status}")
        if not services["database"]["configured"]:
            degraded_reasons.append("database:not_configured")
        if not services["cache"]["configured"]:
            degraded_reasons.append("cache:not_configured")
        if local_ai["status"] != "available":
            degraded_reasons.append(f"local_ai:{local_ai['status']}")

        order_execution = "disabled"
        if self.settings.trading_mode == TradingMode.PAPER and broker_status == "paper_configured":
            order_execution = "paper_only_after_risk_approval"
        elif self.settings.trading_mode == TradingMode.LIVE:
            order_execution = "blocked" if not self.settings.can_submit_live_orders else "requires_human_approval"

        return CapabilityReport(
            environment=self.settings.env,
            trading_mode=self.settings.trading_mode.value,
            live_trading_enabled=self.settings.live_trading_enabled,
            live_trading_status=self.settings.live_trading_status,
            broker_configured=broker.value,
            broker_status=broker_status,
            order_execution=order_execution,
            hardware=hardware,
            services=services,
            local_ai=local_ai,
            degraded_reasons=degraded_reasons,
        )

    def _detect_hardware(self) -> dict[str, Any]:
        ram_bytes = 0
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            pages = os.sysconf("SC_PHYS_PAGES")
            ram_bytes = int(page_size * pages)
        except (ValueError, OSError, AttributeError):
            pass

        gpu = {"available": False, "provider": None, "name": None}
        if shutil.which("nvidia-smi"):
            try:
                output = subprocess.check_output(
                    ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                    text=True,
                    timeout=2,
                ).strip()
                if output:
                    gpu = {"available": True, "provider": "nvidia", "name": output.splitlines()[0]}
            except (subprocess.SubprocessError, OSError):
                gpu = {"available": False, "provider": "nvidia", "name": None}

        return {
            "system": platform.system(),
            "release": platform.release(),
            "machine": platform.machine(),
            "cpu_count": os.cpu_count(),
            "ram_bytes": ram_bytes,
            "gpu": gpu,
        }

    def _detect_services(self) -> dict[str, Any]:
        return {
            "database": {
                "configured": bool(self.settings.database_url),
                "kind": self._classify_database(self.settings.database_url),
            },
            "cache": {
                "configured": bool(self.settings.redis_url),
                "kind": "redis" if self.settings.redis_url.startswith("redis://") else "unknown",
            },
            "event_bus": {
                "configured": bool(self.settings.event_bus_url),
                "kind": self._classify_event_bus(self.settings.event_bus_url),
            },
        }

    def _detect_ollama(self) -> dict[str, Any]:
        endpoint = self.settings.ollama_base_url.rstrip("/")
        try:
            with urllib.request.urlopen(f"{endpoint}/api/tags", timeout=1.5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            models = [model["name"] for model in payload.get("models", []) if model.get("name")]
            return {
                "runtime": "ollama",
                "status": "available" if models else "disabled",
                "base_url": endpoint,
                "models": models,
                "model_count": len(models),
            }
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
            return {
                "runtime": "ollama",
                "status": "disabled",
                "base_url": endpoint,
                "reason": "endpoint_unreachable",
            }

    def _detect_broker(self) -> tuple[BrokerName, str]:
        requested = self.settings.broker
        if requested == BrokerName.AUTO:
            requested = self._autodetect_broker()

        if requested == BrokerName.NONE:
            return requested, "not_configured"

        if self.settings.trading_mode == TradingMode.LIVE and not self.settings.live_trading_enabled:
            return requested, "live_blocked"

        if requested == BrokerName.ALPACA:
            paper_ready = bool(os.getenv("ALPACA_API_KEY")) and bool(os.getenv("ALPACA_API_SECRET"))
            return requested, "paper_configured" if paper_ready else "not_configured"

        return requested, "configured_not_implemented"

    def _autodetect_broker(self) -> BrokerName:
        if os.getenv("ALPACA_API_KEY") and os.getenv("ALPACA_API_SECRET"):
            return BrokerName.ALPACA
        if os.getenv("IBKR_HOST"):
            return BrokerName.IBKR
        if os.getenv("BINANCE_API_KEY"):
            return BrokerName.BINANCE
        if os.getenv("COINBASE_API_KEY"):
            return BrokerName.COINBASE
        if os.getenv("OANDA_API_TOKEN"):
            return BrokerName.OANDA
        return BrokerName.NONE

    @staticmethod
    def _classify_database(url: str) -> str:
        parsed = urlparse(url)
        if "postgres" in parsed.scheme:
            return "postgresql/timescale"
        if "clickhouse" in parsed.scheme:
            return "clickhouse"
        return "unknown"

    @staticmethod
    def _classify_event_bus(url: str) -> str:
        if not url:
            return "none"
        host = url.split(":", 1)[0].lower()
        if "redpanda" in host:
            return "redpanda"
        if "kafka" in host:
            return "kafka"
        if "nats" in host:
            return "nats"
        try:
            socket.gethostbyname(host)
        except OSError:
            return "configured_unresolved"
        return "unknown"
