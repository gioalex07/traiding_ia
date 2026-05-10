import logging

from rac.notifications.telegram import TelegramClient

log = logging.getLogger("rac.notifications")

_DRAWDOWN_ESCALATION_STEP = 5.0


class AlertService:
    """Sends operational alerts via Telegram with built-in deduplication.

    State is in-memory: create once in the worker main loop so it persists
    across cycles. Alerts never raise — failures are logged and swallowed.
    """

    def __init__(self, client: TelegramClient) -> None:
        self._client = client
        self._kill_switch_alerted = False
        self._last_drawdown_alerted: float = 0.0

    def on_kill_switch_active(self, reason: str) -> None:
        if self._kill_switch_alerted:
            return
        self._kill_switch_alerted = True
        self._send(
            f"🚨 <b>KILL SWITCH ACTIVE</b>\n"
            f"Reason: {reason}\n"
            f"Order execution is blocked until manually reset."
        )

    def on_kill_switch_reset(self) -> None:
        if not self._kill_switch_alerted:
            return
        self._kill_switch_alerted = False
        self._send("✅ <b>Kill switch reset</b> — trading resumed.")

    def on_fill(self, symbol: str, side: str, quantity: float, price: float) -> None:
        notional = quantity * price
        icon = "🟢" if side == "buy" else "🔴"
        self._send(
            f"{icon} <b>Order filled</b>\n"
            f"{side.upper()} {quantity:g} {symbol} @ ${price:,.2f}\n"
            f"Notional: ${notional:,.2f}"
        )

    def on_drawdown(self, current_pct: float, threshold_pct: float) -> None:
        if current_pct < threshold_pct:
            if self._last_drawdown_alerted > 0.0:
                self._last_drawdown_alerted = 0.0
            return
        if current_pct < self._last_drawdown_alerted + _DRAWDOWN_ESCALATION_STEP:
            return
        self._last_drawdown_alerted = current_pct
        self._send(
            f"⚠️ <b>Drawdown alert</b>\n"
            f"Current: <b>{current_pct:.1f}%</b> (threshold: {threshold_pct:.1f}%)\n"
            f"Review portfolio and consider activating kill switch."
        )

    def _send(self, text: str) -> None:
        try:
            self._client.send(text)
        except Exception as exc:
            log.warning("alert_send_error: %s", exc)
