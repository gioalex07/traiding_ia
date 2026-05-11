import json
import logging
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.notifications.service import AlertService
from rac.orders.outcome import TradeOutcomeRepository
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository

log = logging.getLogger("rac.reconciliation")

_FILLED_STATUSES = {"filled", "partially_filled"}
_TERMINAL_STATUSES = {"rejected", "canceled", "expired", "done_for_day", "stopped"}
_KNOWN_PENDING_STATUSES = {"pending_new", "accepted", "accepted_for_bidding", "new", "held", "pending_cancel"}
_MAX_ORDER_AGE_HOURS = 48


class ReconciliationResult(BaseModel):
    checked: int
    filled: int
    pending: int
    cancelled: int
    errors: list[str]


class ReconciliationService:
    def __init__(
        self,
        broker_adapter: AlpacaBrokerAdapter,
        order_repository: OrderRepository,
        portfolio_repository: PortfolioRepository,
        alerts: AlertService | None = None,
        outcomes: TradeOutcomeRepository | None = None,
    ) -> None:
        self.broker = broker_adapter
        self.orders = order_repository
        self.portfolio = portfolio_repository
        self.alerts = alerts
        self.outcomes = outcomes

    async def reconcile_pending(self) -> ReconciliationResult:
        pending = self.orders.pending_broker_orders()
        filled = cancelled = 0
        errors: list[str] = []

        for order in pending:
            order_any: dict[str, Any] = dict(order)
            broker_order_id = str(order_any["broker_order_id"])
            try:
                broker_order = await self.broker.get_order(broker_order_id)
                alpaca_status = str(broker_order.get("status", ""))

                if alpaca_status in _FILLED_STATUSES:
                    filled_qty = float(broker_order.get("filled_qty") or order_any["quantity"])
                    filled_price = float(broker_order.get("filled_avg_price") or order_any["estimated_price"])
                    filled_at = str(broker_order.get("filled_at") or "")

                    self.orders.mark_filled(
                        order_id=str(order_any["id"]),
                        filled_price=filled_price,
                        filled_qty=filled_qty,
                        filled_at=filled_at,
                    )
                    current_cash = self.portfolio.current_cash(environment=str(order_any["environment"]))
                    self.portfolio.apply_paper_fill(
                        environment=str(order_any["environment"]),
                        order_id=str(order_any["id"]),
                        symbol=str(order_any["symbol"]),
                        side=str(order_any["side"]),
                        quantity=filled_qty,
                        price=filled_price,
                        starting_cash=current_cash,
                    )
                    filled += 1
                    if self.alerts:
                        self.alerts.on_fill(
                            symbol=str(order_any["symbol"]),
                            side=str(order_any["side"]),
                            quantity=filled_qty,
                            price=filled_price,
                        )
                    if self.outcomes and str(order_any["side"]) == "sell":
                        self._record_outcome(order_any, filled_price, filled_qty,
                                             str(broker_order.get("filled_at") or ""))

                elif alpaca_status in _TERMINAL_STATUSES:
                    self.orders.mark_cancelled(str(order_any["id"]), alpaca_status)
                    cancelled += 1

                elif alpaca_status in _KNOWN_PENDING_STATUSES:
                    age_hours = (
                        datetime.now(UTC) - datetime.fromisoformat(str(order_any["created_at"]))
                    ).total_seconds() / 3600
                    if age_hours > _MAX_ORDER_AGE_HOURS:
                        log.warning(
                            "stale_order broker_order_id=%s status=%s age_hours=%.0f — marking expired",
                            broker_order_id, alpaca_status, age_hours,
                        )
                        self.orders.mark_cancelled(str(order_any["id"]), "expired_by_rac")
                        cancelled += 1
                    else:
                        log.debug(
                            "order_pending broker_order_id=%s status=%s age_hours=%.1f",
                            broker_order_id, alpaca_status, age_hours,
                        )

                else:
                    log.warning(
                        "unknown_alpaca_status broker_order_id=%s status=%s",
                        broker_order_id, alpaca_status,
                    )

            except Exception as exc:
                errors.append(f"{broker_order_id}:{exc}")

        return ReconciliationResult(
            checked=len(pending),
            filled=filled,
            pending=len(pending) - filled - cancelled - len(errors),
            cancelled=cancelled,
            errors=errors,
        )

    def _record_outcome(
        self,
        sell_order: dict[str, Any],
        sell_price: float,
        sell_qty: float,
        closed_at: str,
    ) -> None:
        if not self.outcomes:
            return
        try:
            environment = str(sell_order["environment"])
            symbol      = str(sell_order["symbol"])

            # Try to find parent BUY via raw_payload (SL/TP close orders)
            raw = sell_order.get("raw_payload")
            if isinstance(raw, str):
                raw = json.loads(raw)
            parent_id = (raw or {}).get("parent_order_id") if isinstance(raw, dict) else None
            close_reason = (raw or {}).get("reason", "signal") if isinstance(raw, dict) else "signal"

            if parent_id:
                buy_order = self.orders.get_by_id(str(parent_id))
            else:
                buy_order = self.orders.latest_filled_buy_full(symbol, environment)

            if not buy_order:
                log.warning("outcome_no_buy_found symbol=%s", symbol)
                return

            open_price = float(buy_order.get("filled_price") or buy_order.get("estimated_price") or 0)
            opened_at  = str(buy_order.get("filled_at") or buy_order.get("created_at") or "")
            strategy   = str(buy_order.get("strategy_id") or sell_order.get("strategy_id", "unknown"))

            self.outcomes.record(
                environment=environment,
                symbol=symbol,
                strategy_id=strategy,
                open_order_id=str(buy_order["id"]),
                close_order_id=str(sell_order["id"]),
                open_price=open_price,
                close_price=sell_price,
                quantity=sell_qty,
                close_reason=close_reason,
                opened_at=opened_at,
                closed_at=closed_at,
            )
            log.info(
                "trade_outcome symbol=%s pnl=%.2f reason=%s",
                symbol,
                (sell_price - open_price) * sell_qty,
                close_reason,
            )
        except Exception as exc:
            log.warning("outcome_record_error: %s", exc)
