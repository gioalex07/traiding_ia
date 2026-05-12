import json
import logging
import os
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from rac.brokers.base import (
    AccountSnapshot,
    BrokerAdapter,
    BrokerCapabilities,
    BrokerEnvironment,
    CancelAck,
    FillEvent,
    OrderAck,
    OrderRequest,
    Position,
)
from rac.config import Settings, TradingMode
from rac.market_data.models import OHLCVBar

log = logging.getLogger("rac.brokers.alpaca")


class AlpacaBrokerAdapter(BrokerAdapter):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def capabilities(self) -> BrokerCapabilities:
        is_live = self.settings.trading_mode == TradingMode.LIVE
        environment = BrokerEnvironment.LIVE if is_live else BrokerEnvironment.PAPER
        return BrokerCapabilities(
            name="alpaca",
            environment=environment,
            supports_market_orders=True,
            supports_limit_orders=True,
            supports_stop_orders=True,
            supports_streaming=True,
            live_trading_blocked=not self.settings.can_submit_live_orders,
        )

    async def get_account(self) -> AccountSnapshot:
        payload = self._request_json("/account")
        return AccountSnapshot(
            account_id=str(payload["id"]),
            cash=float(payload["cash"]),
            equity=float(payload["equity"]),
            buying_power=float(payload["buying_power"]),
        )

    async def get_positions(self) -> list[Position]:
        payload = self._request_json("/positions")
        return [
            Position(
                symbol=str(item["symbol"]),
                quantity=float(item["qty"]),
                market_value=float(item["market_value"]),
            )
            for item in payload
        ]

    async def submit_order(self, order: OrderRequest) -> OrderAck:
        body: dict[str, object] = {
            "symbol": order.symbol,
            "qty": str(round(order.quantity, 8)),
            "side": order.side,
            "type": order.order_type,
            "time_in_force": "day",
            "client_order_id": order.idempotency_key[:48],
        }
        if order.order_type == "limit" and order.limit_price is not None:
            body["limit_price"] = str(order.limit_price)
        if order.order_type == "stop" and order.stop_price is not None:
            body["stop_price"] = str(order.stop_price)
        payload = self._post_json("/orders", body)
        return OrderAck(
            broker_order_id=str(payload["id"]),
            status=str(payload["status"]),
            raw_payload=dict(payload),
        )

    async def get_historical_bars(
        self,
        symbol: str,
        timeframe: str,
        start: datetime,
        end: datetime,
        page_size: int = 10_000,
    ) -> tuple[list[OHLCVBar], int]:
        """Fetches all bars in the range, paginating automatically. Returns (bars, pages)."""
        all_bars: list[OHLCVBar] = []
        page_token: str | None = None
        pages = 0

        while True:
            params: dict[str, str] = {
                "timeframe": timeframe,
                "start": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "end": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "limit": str(page_size),
                "sort": "asc",
                "feed": "iex",
            }
            if page_token:
                params["page_token"] = page_token

            payload = self._data_request_json(f"/stocks/{symbol.upper()}/bars", params)
            pages += 1

            for bar in payload.get("bars") or []:
                all_bars.append(OHLCVBar(
                    time=bar["t"],
                    broker="alpaca",
                    symbol=symbol.upper(),
                    timeframe=timeframe,
                    open=float(bar["o"]),
                    high=float(bar["h"]),
                    low=float(bar["l"]),
                    close=float(bar["c"]),
                    volume=float(bar["v"]),
                ))

            raw_token = payload.get("next_page_token")
            page_token = str(raw_token) if raw_token else None
            if not page_token:
                break

        return all_bars, pages

    async def get_latest_bars(self, symbol: str, timeframe: str, limit: int = 20) -> list[OHLCVBar]:
        # start=7 días atrás + sort=desc → las N barras más recientes disponibles
        start = (datetime.now(UTC) - timedelta(days=7)).strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {"timeframe": timeframe, "limit": str(limit), "start": start, "sort": "desc"}
        payload = self._data_request_json(f"/stocks/{symbol.upper()}/bars", params)
        bars_raw = list(reversed(payload.get("bars") or []))
        return [
            OHLCVBar(
                time=bar["t"],
                broker="alpaca",
                symbol=symbol.upper(),
                timeframe=timeframe,
                open=float(bar["o"]),
                high=float(bar["h"]),
                low=float(bar["l"]),
                close=float(bar["c"]),
                volume=float(bar["v"]),
            )
            for bar in bars_raw
        ]

    async def get_order(self, broker_order_id: str) -> dict[str, object]:
        payload = self._request_json(f"/orders/{broker_order_id}")
        return dict(payload)

    async def cancel_order(self, broker_order_id: str) -> CancelAck:
        try:
            self._delete_request(f"/orders/{broker_order_id}")
            return CancelAck(broker_order_id=broker_order_id, status="cancelled")
        except RuntimeError as exc:
            if ":404" in str(exc):
                return CancelAck(broker_order_id=broker_order_id, status="not_found")
            raise

    async def stream_fills(self) -> AsyncIterator[FillEvent]:
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError:
            raise RuntimeError("websockets not installed — add websockets>=12 to requirements.txt")

        api_key = os.getenv("ALPACA_API_KEY", "")
        api_secret = os.getenv("ALPACA_API_SECRET", "")
        if not api_key or not api_secret:
            raise RuntimeError("alpaca_paper_credentials_missing")

        url = self._trading_stream_url()
        log.info("alpaca_stream_connecting url=%s", url)

        async with websockets.connect(url) as ws:
            await ws.send(json.dumps({"action": "auth", "key": api_key, "secret": api_secret}))
            auth_resp = json.loads(await ws.recv())
            if auth_resp.get("data", {}).get("status") != "authorized":
                raise RuntimeError(f"alpaca_stream_auth_failed: {auth_resp}")

            await ws.send(json.dumps({"action": "listen", "data": {"streams": ["trade_updates"]}}))
            await ws.recv()  # listening confirmation

            log.info("alpaca_stream_ready")
            async for raw in ws:
                msg = json.loads(raw)
                if msg.get("stream") != "trade_updates":
                    continue
                event_data = msg.get("data", {})
                if event_data.get("event") not in ("fill", "partial_fill"):
                    continue
                order = event_data.get("order", {})
                yield FillEvent(
                    broker_order_id=str(order.get("id", "")),
                    symbol=str(order.get("symbol", "")),
                    quantity=float(order.get("filled_qty") or 0),
                    price=float(order.get("filled_avg_price") or 0),
                    timestamp=str(order.get("filled_at") or ""),
                    side=str(order.get("side", "")),
                )

    def _trading_stream_url(self) -> str:
        base = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets/v2")
        parsed = urllib.parse.urlparse(base)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return f"{scheme}://{parsed.netloc}/stream"

    def _data_request_json(self, path: str, params: dict[str, str] | None = None) -> dict[str, object]:
        base_url = os.getenv("ALPACA_DATA_BASE_URL", "https://data.alpaca.markets/v2").rstrip("/")
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("alpaca_paper_credentials_missing")
        url = f"{base_url}{path}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        request = urllib.request.Request(
            url,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"alpaca_http_error:{exc.code}:{detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"alpaca_unavailable:{exc.__class__.__name__}") from exc

    def _post_json(self, path: str, body: dict[str, object]) -> dict[str, object]:
        base_url = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("alpaca_paper_credentials_missing")
        data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(
            f"{base_url}{path}",
            data=data,
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"alpaca_http_error:{exc.code}:{detail}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"alpaca_unavailable:{exc.__class__.__name__}") from exc

    def _delete_request(self, path: str) -> None:
        base_url = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("alpaca_paper_credentials_missing")
        request = urllib.request.Request(
            f"{base_url}{path}",
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            },
            method="DELETE",
        )
        try:
            with urllib.request.urlopen(request, timeout=10):
                return
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"alpaca_http_error:{exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            raise RuntimeError(f"alpaca_unavailable:{exc.__class__.__name__}") from exc

    def _request_json(self, path: str) -> Any:
        base_url = os.getenv("ALPACA_PAPER_BASE_URL", "https://paper-api.alpaca.markets").rstrip("/")
        api_key = os.getenv("ALPACA_API_KEY")
        api_secret = os.getenv("ALPACA_API_SECRET")
        if not api_key or not api_secret:
            raise RuntimeError("alpaca_paper_credentials_missing")
        request = urllib.request.Request(
            f"{base_url}{path}",
            headers={
                "APCA-API-KEY-ID": api_key,
                "APCA-API-SECRET-KEY": api_secret,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"alpaca_http_error:{exc.code}") from exc
        except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"alpaca_unavailable:{exc.__class__.__name__}") from exc
