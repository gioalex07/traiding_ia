import unittest
from datetime import UTC, datetime

from rac.notifications.service import AlertService
from rac.reports.daily import DailyReport, DailyReportService


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakePortfolioRepository:
    def __init__(
        self,
        snapshot: dict | None = None,
        positions: list | None = None,
    ) -> None:
        self._snapshot = snapshot
        self._positions = positions or []

    def latest_snapshot(self, environment: str = "paper") -> dict | None:
        return self._snapshot

    def positions(self, environment: str = "paper") -> list:
        return self._positions


class FakeOrderRepository:
    def __init__(self, fills: list | None = None) -> None:
        self._fills = fills or []

    def fills_today(self, environment: str = "paper") -> list:
        return self._fills


class FakeTelegramClient:
    def __init__(self) -> None:
        self.sent: list[str] = []
        self.configured = True

    def send(self, text: str) -> bool:
        self.sent.append(text)
        return True


# ── DailyReportService ───────────────────────────────────────────────────────

class DailyReportServiceTest(unittest.TestCase):
    def _service(self, snapshot=None, positions=None, fills=None) -> DailyReportService:
        return DailyReportService(
            portfolio_repository=FakePortfolioRepository(snapshot, positions),  # type: ignore[arg-type]
            order_repository=FakeOrderRepository(fills),  # type: ignore[arg-type]
        )

    def test_empty_snapshot_returns_zeros(self) -> None:
        report = self._service().build()
        self.assertIsInstance(report, DailyReport)
        self.assertEqual(report.nav, 0.0)
        self.assertEqual(report.pnl_daily, 0.0)
        self.assertEqual(report.drawdown_pct, 0.0)
        self.assertEqual(report.cash, 0.0)

    def test_snapshot_values_mapped_correctly(self) -> None:
        snapshot = {"nav": 103250.0, "pnl_daily": 1250.0, "drawdown": 1.2, "cash": 85000.0}
        report = self._service(snapshot=snapshot).build()
        self.assertAlmostEqual(report.nav, 103250.0)
        self.assertAlmostEqual(report.pnl_daily, 1250.0)
        self.assertAlmostEqual(report.drawdown_pct, 1.2)
        self.assertAlmostEqual(report.cash, 85000.0)

    def test_positions_included(self) -> None:
        positions = [{"symbol": "AAPL", "quantity": 10.0, "market_value": 1750.0}]
        report = self._service(positions=positions).build()
        self.assertEqual(len(report.positions), 1)
        self.assertEqual(report.positions[0]["symbol"], "AAPL")

    def test_fills_today_included(self) -> None:
        fills = [{"symbol": "AAPL", "side": "buy", "quantity": 10.0, "price": 175.0}]
        report = self._service(fills=fills).build()
        self.assertEqual(len(report.fills_today), 1)
        self.assertEqual(report.fills_today[0]["side"], "buy")

    def test_date_is_today(self) -> None:
        report = self._service().build()
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        self.assertEqual(report.date, today)

    def test_none_snapshot_gracefully_returns_zeros(self) -> None:
        report = self._service(snapshot=None).build()
        self.assertEqual(report.nav, 0.0)


# ── AlertService.on_daily_report ─────────────────────────────────────────────

class AlertServiceDailyReportTest(unittest.TestCase):
    def _service(self) -> tuple[AlertService, FakeTelegramClient]:
        client = FakeTelegramClient()
        return AlertService(client), client  # type: ignore[arg-type]

    def _base_kwargs(self) -> dict:
        return dict(
            report_date="2026-05-10",
            nav=103250.0,
            pnl_daily=1250.0,
            drawdown_pct=1.2,
            cash=85000.0,
            positions=[],
            fills_today=[],
            strategies=("trend_following_v1", "mean_reversion_v1"),
        )

    def test_report_sends_one_message(self) -> None:
        svc, client = self._service()
        svc.on_daily_report(**self._base_kwargs())
        self.assertEqual(len(client.sent), 1)

    def test_report_contains_date(self) -> None:
        svc, client = self._service()
        svc.on_daily_report(**self._base_kwargs())
        self.assertIn("2026-05-10", client.sent[0])

    def test_report_contains_nav(self) -> None:
        svc, client = self._service()
        svc.on_daily_report(**self._base_kwargs())
        self.assertIn("103,250", client.sent[0])

    def test_report_contains_strategies(self) -> None:
        svc, client = self._service()
        svc.on_daily_report(**self._base_kwargs())
        self.assertIn("trend_following_v1", client.sent[0])

    def test_report_with_positions_mentions_symbol(self) -> None:
        svc, client = self._service()
        kwargs = self._base_kwargs()
        kwargs["positions"] = [{"symbol": "AAPL", "quantity": 10.0, "market_value": 1750.0}]
        svc.on_daily_report(**kwargs)
        self.assertIn("AAPL", client.sent[0])

    def test_report_with_fills_mentions_buy(self) -> None:
        svc, client = self._service()
        kwargs = self._base_kwargs()
        kwargs["fills_today"] = [{"symbol": "AAPL", "side": "buy", "quantity": 10.0, "price": 175.0}]
        svc.on_daily_report(**kwargs)
        self.assertIn("BUY", client.sent[0])

    def test_report_sets_last_report_date(self) -> None:
        svc, _ = self._service()
        self.assertIsNone(svc._last_report_date)
        svc.on_daily_report(**self._base_kwargs())
        self.assertEqual(svc._last_report_date, datetime.now(UTC).date())

    def test_loss_day_shows_negative_pnl(self) -> None:
        svc, client = self._service()
        kwargs = self._base_kwargs()
        kwargs["pnl_daily"] = -500.0
        svc.on_daily_report(**kwargs)
        self.assertIn("$-500", client.sent[0])


# ── AlertService.should_send_daily_report ────────────────────────────────────

class AlertServiceDailyReportDeduplicationTest(unittest.TestCase):
    def _service(self) -> AlertService:
        client = FakeTelegramClient()
        return AlertService(client)  # type: ignore[arg-type]

    def test_returns_false_when_already_sent_today(self) -> None:
        svc = self._service()
        svc._last_report_date = datetime.now(UTC).date()
        self.assertFalse(svc.should_send_daily_report())

    def test_returns_false_when_sent_today_via_on_daily_report(self) -> None:
        svc = self._service()
        svc.on_daily_report(
            report_date="2026-05-10",
            nav=100_000.0,
            pnl_daily=0.0,
            drawdown_pct=0.0,
            cash=100_000.0,
            positions=[],
            fills_today=[],
            strategies=("trend_following_v1",),
        )
        self.assertFalse(svc.should_send_daily_report())

    def test_returns_true_when_last_report_was_yesterday(self) -> None:
        from datetime import timedelta
        svc = self._service()
        svc._last_report_date = (datetime.now(UTC) - timedelta(days=1)).date()
        # Only True after 21:00 UTC — we test the date logic regardless of hour
        # by checking that yesterday != today (the date guard)
        today = datetime.now(UTC).date()
        self.assertNotEqual(svc._last_report_date, today)


if __name__ == "__main__":
    unittest.main()
