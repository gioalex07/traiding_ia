from typing import Any

from pydantic import BaseModel

from rac.brokers.alpaca import AlpacaBrokerAdapter
from rac.notifications.service import AlertService
from rac.orders.repository import OrderRepository
from rac.portfolio.repository import PortfolioRepository

_FILLED_STATUSES = {"filled"}
_TERMINAL_STATUSES = {"rejected", "canceled", "expired", "done_for_day"}  # Alpaca usa "canceled" (una l)


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
    ) -> None:
        self.broker = broker_adapter
        self.orders = order_repository
        self.portfolio = portfolio_repository
        self.alerts = alerts

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

                elif alpaca_status in _TERMINAL_STATUSES:
                    self.orders.mark_cancelled(str(order_any["id"]), alpaca_status)
                    cancelled += 1

            except Exception as exc:
                errors.append(f"{broker_order_id}:{exc}")

        return ReconciliationResult(
            checked=len(pending),
            filled=filled,
            pending=len(pending) - filled - cancelled - len(errors),
            cancelled=cancelled,
            errors=errors,
        )
