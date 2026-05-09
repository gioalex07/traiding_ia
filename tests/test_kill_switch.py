import unittest
from datetime import UTC, datetime
from typing import Any

from rac.admin.kill_switch import KillSwitchState


class KillSwitchStateTest(unittest.TestCase):
    """Tests for the KillSwitchState model — pure, no DB."""

    def test_inactive_by_default(self) -> None:
        state = KillSwitchState(active=False)
        self.assertFalse(state.active)
        self.assertIsNone(state.activated_at)
        self.assertIsNone(state.reason)

    def test_active_state_carries_metadata(self) -> None:
        now = datetime.now(UTC)
        state = KillSwitchState(
            active=True,
            activated_at=now,
            activated_by="operator",
            reason="runaway losses detected",
            event_id="abc-123",
        )
        self.assertTrue(state.active)
        self.assertEqual(state.reason, "runaway losses detected")
        self.assertEqual(state.activated_by, "operator")
        self.assertEqual(state.event_id, "abc-123")

    def test_inactive_state_serializes_cleanly(self) -> None:
        state = KillSwitchState(active=False)
        data: dict[str, Any] = state.model_dump()
        self.assertFalse(data["active"])
        self.assertIsNone(data["reason"])

    def test_active_state_serializes_all_fields(self) -> None:
        now = datetime.now(UTC)
        state = KillSwitchState(active=True, activated_at=now, reason="test", activated_by="ci")
        data = state.model_dump()
        self.assertTrue(data["active"])
        self.assertEqual(data["reason"], "test")


class KillSwitchLogicTest(unittest.TestCase):
    """Verifies the activate → is_active → deactivate lifecycle using a fake repo."""

    def _make_repo(self) -> Any:
        """Returns an in-memory kill switch repo that doesn't use the DB."""

        class InMemoryKillSwitch:
            def __init__(self) -> None:
                self._events: list[dict[str, Any]] = []

            def activate(self, reason: str, actor: str) -> str:
                self._events.append({"action": "activate", "reason": reason, "actor": actor})
                return "event-1"

            def deactivate(self, reason: str, actor: str) -> str:
                self._events.append({"action": "deactivate", "reason": reason, "actor": actor})
                return "event-2"

            def is_active(self) -> bool:
                if not self._events:
                    return False
                return self._events[-1]["action"] == "activate"

            def current_state(self) -> KillSwitchState:
                if not self._events or self._events[-1]["action"] == "deactivate":
                    return KillSwitchState(active=False)
                e = self._events[-1]
                return KillSwitchState(active=True, reason=e["reason"], activated_by=e["actor"])

        return InMemoryKillSwitch()

    def test_initially_inactive(self) -> None:
        ks = self._make_repo()
        self.assertFalse(ks.is_active())

    def test_activate_makes_active(self) -> None:
        ks = self._make_repo()
        ks.activate("manual stop", "operator")
        self.assertTrue(ks.is_active())

    def test_deactivate_after_activate_is_inactive(self) -> None:
        ks = self._make_repo()
        ks.activate("stop", "op")
        ks.deactivate("all clear", "op")
        self.assertFalse(ks.is_active())

    def test_multiple_cycles(self) -> None:
        ks = self._make_repo()
        ks.activate("issue 1", "op")
        ks.deactivate("fixed", "op")
        ks.activate("issue 2", "op")
        self.assertTrue(ks.is_active())
        state = ks.current_state()
        self.assertEqual(state.reason, "issue 2")

    def test_state_carries_reason(self) -> None:
        ks = self._make_repo()
        ks.activate("drawdown exceeded 5%", "risk-manager")
        state = ks.current_state()
        self.assertEqual(state.reason, "drawdown exceeded 5%")
        self.assertEqual(state.activated_by, "risk-manager")


if __name__ == "__main__":
    unittest.main()
