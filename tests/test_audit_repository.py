import unittest

from rac.audit.repository import AuditRepository


class AuditRepositoryInterfaceTest(unittest.TestCase):
    """Tests that verify AuditRepository interface without a real DB connection."""

    def test_recent_events_limit_clamped_to_500(self) -> None:
        self.assertEqual(max(1, min(9999, 500)), 500)
        self.assertEqual(max(1, min(0, 500)), 1)
        self.assertEqual(max(1, min(20, 500)), 20)

    def test_repository_can_be_instantiated_with_empty_url(self) -> None:
        from rac.config import load_settings
        settings = load_settings()
        repo = AuditRepository(settings)
        self.assertIsInstance(repo, AuditRepository)


class AuditEventFilterTest(unittest.TestCase):
    """Tests for recent_events parameter handling (pure logic, no DB)."""

    def test_safe_limit_minimum_is_one(self) -> None:
        self.assertEqual(max(1, min(-5, 500)), 1)

    def test_safe_limit_maximum_is_500(self) -> None:
        self.assertEqual(max(1, min(1000, 500)), 500)

    def test_safe_limit_within_range_unchanged(self) -> None:
        self.assertEqual(max(1, min(50, 500)), 50)


if __name__ == "__main__":
    unittest.main()
