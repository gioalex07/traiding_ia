import unittest

from rac.notifications.service import AlertService
from rac.notifications.telegram import TelegramClient


class FakeTelegramClient:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.configured = True

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


class TelegramClientConfiguredTest(unittest.TestCase):
    def test_not_configured_when_token_empty(self) -> None:
        client = TelegramClient(token="", chat_id="123")
        self.assertFalse(client.configured)

    def test_not_configured_when_chat_id_empty(self) -> None:
        client = TelegramClient(token="abc:token", chat_id="")
        self.assertFalse(client.configured)

    def test_configured_when_both_set(self) -> None:
        client = TelegramClient(token="abc:token", chat_id="123456")
        self.assertTrue(client.configured)

    def test_send_returns_false_when_not_configured(self) -> None:
        client = TelegramClient(token="", chat_id="")
        self.assertFalse(client.send("hello"))


class AlertServiceKillSwitchTest(unittest.TestCase):
    def _service(self) -> tuple[AlertService, FakeTelegramClient]:
        client = FakeTelegramClient()
        return AlertService(client), client  # type: ignore[arg-type]

    def test_first_activation_sends_alert(self) -> None:
        svc, client = self._service()
        svc.on_kill_switch_active("manual test")
        self.assertEqual(len(client.sent), 1)
        self.assertIn("KILL SWITCH", client.sent[0])

    def test_repeated_activation_deduplicates(self) -> None:
        svc, client = self._service()
        svc.on_kill_switch_active("reason")
        svc.on_kill_switch_active("reason again")
        self.assertEqual(len(client.sent), 1)

    def test_reset_without_prior_activation_sends_nothing(self) -> None:
        svc, client = self._service()
        svc.on_kill_switch_reset()
        self.assertEqual(len(client.sent), 0)

    def test_reset_after_activation_sends_recovery(self) -> None:
        svc, client = self._service()
        svc.on_kill_switch_active("reason")
        svc.on_kill_switch_reset()
        self.assertEqual(len(client.sent), 2)
        self.assertIn("reset", client.sent[1].lower())

    def test_reactivation_after_reset_sends_again(self) -> None:
        svc, client = self._service()
        svc.on_kill_switch_active("first")
        svc.on_kill_switch_reset()
        svc.on_kill_switch_active("second")
        self.assertEqual(len(client.sent), 3)


class AlertServiceFillTest(unittest.TestCase):
    def _service(self) -> tuple[AlertService, FakeTelegramClient]:
        client = FakeTelegramClient()
        return AlertService(client), client  # type: ignore[arg-type]

    def test_buy_fill_sends_message(self) -> None:
        svc, client = self._service()
        svc.on_fill("AAPL", "buy", 10.0, 175.50)
        self.assertEqual(len(client.sent), 1)
        self.assertIn("BUY", client.sent[0])
        self.assertIn("AAPL", client.sent[0])

    def test_sell_fill_sends_message(self) -> None:
        svc, client = self._service()
        svc.on_fill("AAPL", "sell", 5.0, 180.00)
        self.assertEqual(len(client.sent), 1)
        self.assertIn("SELL", client.sent[0])

    def test_each_fill_sends_independently(self) -> None:
        svc, client = self._service()
        svc.on_fill("AAPL", "buy", 10.0, 175.0)
        svc.on_fill("MSFT", "buy", 5.0, 420.0)
        self.assertEqual(len(client.sent), 2)


class AlertServiceDrawdownTest(unittest.TestCase):
    def _service(self) -> tuple[AlertService, FakeTelegramClient]:
        client = FakeTelegramClient()
        return AlertService(client), client  # type: ignore[arg-type]

    def test_below_threshold_sends_nothing(self) -> None:
        svc, client = self._service()
        svc.on_drawdown(current_pct=3.0, threshold_pct=5.0)
        self.assertEqual(len(client.sent), 0)

    def test_at_threshold_sends_alert(self) -> None:
        svc, client = self._service()
        svc.on_drawdown(current_pct=5.0, threshold_pct=5.0)
        self.assertEqual(len(client.sent), 1)
        self.assertIn("5.0%", client.sent[0])

    def test_same_level_deduplicates(self) -> None:
        svc, client = self._service()
        svc.on_drawdown(current_pct=5.0, threshold_pct=5.0)
        svc.on_drawdown(current_pct=5.5, threshold_pct=5.0)
        self.assertEqual(len(client.sent), 1)

    def test_escalation_sends_second_alert(self) -> None:
        svc, client = self._service()
        svc.on_drawdown(current_pct=5.0, threshold_pct=5.0)
        svc.on_drawdown(current_pct=10.5, threshold_pct=5.0)
        self.assertEqual(len(client.sent), 2)

    def test_recovery_resets_state(self) -> None:
        svc, client = self._service()
        svc.on_drawdown(current_pct=6.0, threshold_pct=5.0)
        svc.on_drawdown(current_pct=2.0, threshold_pct=5.0)
        svc.on_drawdown(current_pct=6.0, threshold_pct=5.0)
        self.assertEqual(len(client.sent), 2)


if __name__ == "__main__":
    unittest.main()
