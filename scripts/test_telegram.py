#!/usr/bin/env python3
"""Smoke test for Telegram alerts. Run with:

    set -a && source .env && set +a && python scripts/test_telegram.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from rac.config import load_settings
from rac.notifications.service import AlertService
from rac.notifications.telegram import TelegramClient


def main() -> None:
    settings = load_settings()
    client = TelegramClient(settings.telegram_bot_token, settings.telegram_chat_id)

    if not client.configured:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in environment.")
        sys.exit(1)

    print(f"Sending test alert to chat_id={settings.telegram_chat_id} ...")

    ok = client.send(
        "✅ <b>RAC alert test</b>\n"
        "Telegram integration is working correctly.\n"
        f"Environment: <code>{settings.env}</code> / mode: <code>{settings.trading_mode}</code>"
    )

    if not ok:
        print("ERROR: message not delivered — check token/chat_id and try again.")
        sys.exit(1)

    print("Message delivered. Testing AlertService deduplication ...")

    svc = AlertService(client)

    svc.on_drawdown(current_pct=6.0, threshold_pct=settings.max_drawdown_pct)
    print(f"  drawdown alert sent (6.0% > threshold {settings.max_drawdown_pct}%)")

    svc.on_kill_switch_active("test activation")
    print("  kill switch alert sent")

    svc.on_kill_switch_reset()
    print("  kill switch reset sent")

    print("\nAll good. Check your Telegram for 3 messages.")


if __name__ == "__main__":
    main()
