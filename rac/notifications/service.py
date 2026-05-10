import logging
from datetime import UTC, date, datetime

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
        self._last_report_date: date | None = None

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

    def should_send_daily_report(self) -> bool:
        """True once per day after 21:00 UTC (≈ 4 pm ET market close)."""
        now = datetime.now(UTC)
        if now.hour < 21:
            return False
        return self._last_report_date != now.date()

    def on_daily_report(
        self,
        *,
        report_date: str,
        nav: float,
        pnl_daily: float,
        drawdown_pct: float,
        cash: float,
        positions: list[dict],
        fills_today: list[dict],
        strategies: tuple[str, ...],
    ) -> None:
        sign = "+" if pnl_daily >= 0 else ""
        pnl_pct = (pnl_daily / (nav - pnl_daily) * 100) if nav != pnl_daily else 0.0

        lines = [
            f"📊 <b>RAC Daily Report — {report_date}</b>",
            "─────────────────────────────────",
            "<b>Portfolio</b>",
            f"  NAV       <b>${nav:,.0f}</b>  ({sign}${pnl_daily:,.0f} | {sign}{pnl_pct:.2f}%)",
            f"  Drawdown  {drawdown_pct:.2f}% from peak",
            f"  Cash      ${cash:,.0f}",
        ]

        if positions:
            lines.append(f"\n<b>Open positions ({len(positions)})</b>")
            for p in positions:
                lines.append(
                    f"  {p['symbol']}  {float(p['quantity']):g} shares"
                    f" · mkt ${float(p['market_value']):,.0f}"
                )
        else:
            lines.append("\n<b>Open positions:</b> none")

        if fills_today:
            lines.append(f"\n<b>Fills today ({len(fills_today)})</b>")
            for f in fills_today:
                icon = "🟢" if f["side"] == "buy" else "🔴"
                lines.append(
                    f"  {icon} {str(f['side']).upper():4s} {float(f['quantity']):g}"
                    f" {f['symbol']} @ ${float(f['price']):,.2f}"
                )
        else:
            lines.append("\n<b>Fills today:</b> none")

        lines.append(f"\n<b>Strategies:</b> {', '.join(strategies)}")
        self._last_report_date = datetime.now(UTC).date()
        self._send("\n".join(lines))

    def _send(self, text: str) -> None:
        try:
            self._client.send(text)
        except Exception as exc:
            log.warning("alert_send_error: %s", exc)
