from rac.market_data.models import OHLCVBar


class MarketDataValidator:
    def validate_bar(self, bar: OHLCVBar) -> list[str]:
        reasons: list[str] = []

        if bar.low > bar.high:
            reasons.append("low_above_high")
        if not (bar.low <= bar.open <= bar.high):
            reasons.append("open_outside_range")
        if not (bar.low <= bar.close <= bar.high):
            reasons.append("close_outside_range")
        if bar.volume < 0:
            reasons.append("negative_volume")
        if bar.high / bar.low > 5:
            reasons.append("extreme_intrabar_range")

        return reasons

