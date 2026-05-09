from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import AsyncIterator


class BrokerEnvironment(StrEnum):
    PAPER = "paper"
    LIVE = "live"


@dataclass(frozen=True)
class BrokerCapabilities:
    name: str
    environment: BrokerEnvironment
    supports_market_orders: bool
    supports_limit_orders: bool
    supports_stop_orders: bool
    supports_streaming: bool
    live_trading_blocked: bool


@dataclass(frozen=True)
class AccountSnapshot:
    account_id: str
    cash: float
    equity: float
    buying_power: float


@dataclass(frozen=True)
class Position:
    symbol: str
    quantity: float
    market_value: float


@dataclass(frozen=True)
class OrderRequest:
    idempotency_key: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    limit_price: float | None = None
    stop_price: float | None = None


@dataclass(frozen=True)
class OrderAck:
    broker_order_id: str
    status: str
    raw_payload: dict[str, object]


@dataclass(frozen=True)
class CancelAck:
    broker_order_id: str
    status: str


@dataclass(frozen=True)
class FillEvent:
    broker_order_id: str
    symbol: str
    quantity: float
    price: float
    timestamp: str


class BrokerAdapter(ABC):
    @abstractmethod
    async def capabilities(self) -> BrokerCapabilities:
        raise NotImplementedError

    @abstractmethod
    async def get_account(self) -> AccountSnapshot:
        raise NotImplementedError

    @abstractmethod
    async def get_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    async def submit_order(self, order: OrderRequest) -> OrderAck:
        raise NotImplementedError

    @abstractmethod
    async def cancel_order(self, broker_order_id: str) -> CancelAck:
        raise NotImplementedError

    @abstractmethod
    async def stream_fills(self) -> AsyncIterator[FillEvent]:
        if False:
            yield FillEvent("", "", 0, 0, "")
        raise NotImplementedError

