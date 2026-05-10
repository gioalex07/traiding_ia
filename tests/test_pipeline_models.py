import unittest

from rac.pipeline.models import PaperPipelineRequest


class PaperPipelineRequestTest(unittest.TestCase):
    def test_symbol_is_uppercase_but_timeframe_keeps_broker_case(self) -> None:
        request = PaperPipelineRequest(
            symbol="aapl",
            timeframe="1Day",
            start="2025-04-01T00:00:00Z",
            end="2025-05-01T23:59:59Z",
        )

        self.assertEqual(request.symbol, "AAPL")
        self.assertEqual(request.timeframe, "1Day")


if __name__ == "__main__":
    unittest.main()
