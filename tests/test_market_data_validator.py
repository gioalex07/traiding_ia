import unittest
from datetime import UTC, datetime

from rac.market_data.models import OHLCVBar
from rac.market_data.validation import MarketDataValidator


class MarketDataValidatorTest(unittest.TestCase):
    def test_accepts_valid_bar(self) -> None:
        bar = OHLCVBar(
            time=datetime.now(UTC),
            broker="alpaca",
            symbol="aapl",
            timeframe="1Min",
            open=100,
            high=101,
            low=99,
            close=100.5,
            volume=1000,
        )

        self.assertEqual(MarketDataValidator().validate_bar(bar), [])
        self.assertEqual(bar.symbol, "AAPL")

    def test_rejects_invalid_price_range(self) -> None:
        bar = OHLCVBar(
            time=datetime.now(UTC),
            broker="alpaca",
            symbol="AAPL",
            timeframe="1Min",
            open=120,
            high=101,
            low=99,
            close=100,
            volume=1000,
        )

        reasons = MarketDataValidator().validate_bar(bar)

        self.assertIn("open_outside_range", reasons)


if __name__ == "__main__":
    unittest.main()
