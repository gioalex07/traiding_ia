import os
from dataclasses import dataclass
from enum import StrEnum


class TradingMode(StrEnum):
    DEV = "dev"
    BACKTEST = "backtest"
    PAPER = "paper"
    LIVE = "live"


class BrokerName(StrEnum):
    AUTO = "auto"
    ALPACA = "alpaca"
    IBKR = "ibkr"
    BINANCE = "binance"
    COINBASE = "coinbase"
    OANDA = "oanda"
    NONE = "none"


def bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value == "":
        return default
    return float(value)


@dataclass(frozen=True)
class Settings:
    env: str
    trading_mode: TradingMode
    live_trading_enabled: bool
    broker: BrokerName
    database_url: str
    redis_url: str
    event_bus_url: str
    ollama_base_url: str
    max_daily_loss_pct: float
    max_weekly_loss_pct: float
    max_position_pct: float
    max_asset_exposure_pct: float
    max_drawdown_pct: float
    cooldown_after_losses: int
    watched_symbols: tuple[str, ...]
    watched_timeframe: str
    watched_strategies: tuple[str, ...]
    loop_interval_seconds: int
    telegram_bot_token: str
    telegram_chat_id: str
    min_signal_confidence: float

    @property
    def live_trading_status(self) -> str:
        if self.trading_mode != TradingMode.LIVE:
            return "not_requested"
        if not self.live_trading_enabled:
            return "blocked"
        return "requires_human_approval"

    @property
    def can_submit_live_orders(self) -> bool:
        return self.trading_mode == TradingMode.LIVE and self.live_trading_enabled


def load_settings() -> Settings:
    return Settings(
        env=os.getenv("RAC_ENV", "dev"),
        trading_mode=TradingMode(os.getenv("RAC_TRADING_MODE", "paper")),
        live_trading_enabled=bool_env("RAC_LIVE_TRADING_ENABLED", False),
        broker=BrokerName(os.getenv("RAC_BROKER", "auto")),
        database_url=os.getenv("DATABASE_URL", ""),
        redis_url=os.getenv("REDIS_URL", ""),
        event_bus_url=os.getenv("EVENT_BUS_URL", ""),
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        max_daily_loss_pct=float_env("RAC_MAX_DAILY_LOSS_PCT", 1.0),
        max_weekly_loss_pct=float_env("RAC_MAX_WEEKLY_LOSS_PCT", 3.0),
        max_position_pct=float_env("RAC_MAX_POSITION_PCT", 5.0),
        max_asset_exposure_pct=float_env("RAC_MAX_ASSET_EXPOSURE_PCT", 10.0),
        max_drawdown_pct=float_env("RAC_MAX_DRAWDOWN_PCT", 5.0),
        cooldown_after_losses=int(os.getenv("RAC_COOLDOWN_AFTER_LOSSES", "3")),
        watched_symbols=tuple(
            s.strip().upper()
            for s in os.getenv("RAC_SYMBOLS", "AAPL").split(",")
            if s.strip()
        ),
        watched_timeframe=os.getenv("RAC_TIMEFRAME", "1Min"),
        watched_strategies=tuple(
            s.strip()
            for s in os.getenv("RAC_STRATEGIES", "trend_following_v1,mean_reversion_v1").split(",")
            if s.strip()
        ),
        loop_interval_seconds=int(os.getenv("RAC_LOOP_INTERVAL", "60")),
        telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
        min_signal_confidence=float_env("RAC_MIN_SIGNAL_CONFIDENCE", 0.6),
    )

