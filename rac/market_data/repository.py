from collections.abc import Iterable

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings
from rac.market_data.models import OHLCVBar


class MarketDataRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def upsert_ohlcv(self, bars: Iterable[OHLCVBar]) -> int:
        rows = list(bars)
        if not rows:
            return 0

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO market_data_ohlcv (
                        time, broker, symbol, timeframe, open, high, low, close, volume, source_quality
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, broker, symbol, timeframe)
                    DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume,
                        source_quality = EXCLUDED.source_quality
                    """,
                    [
                        (
                            bar.time,
                            bar.broker,
                            bar.symbol,
                            bar.timeframe,
                            bar.open,
                            bar.high,
                            bar.low,
                            bar.close,
                            bar.volume,
                            bar.source_quality.value,
                        )
                        for bar in rows
                    ],
                )
            conn.commit()
        return len(rows)

    def latest_ohlcv(self, symbol: str, timeframe: str, limit: int = 100) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT time, broker, symbol, timeframe, open, high, low, close, volume, source_quality
                    FROM market_data_ohlcv
                    WHERE symbol = %s AND timeframe = %s
                    ORDER BY time DESC
                    LIMIT %s
                    """,
                    (symbol.upper(), timeframe.upper(), limit),
                )
                return list(cursor.fetchall())

