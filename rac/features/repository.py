import json
from collections.abc import Iterable

import psycopg
from psycopg.rows import dict_row

from rac.config import Settings
from rac.features.models import FeaturePoint


class FeatureRepository:
    def __init__(self, settings: Settings) -> None:
        self._database_url = settings.database_url.replace("postgresql+psycopg://", "postgresql://")

    def upsert_features(self, points: Iterable[FeaturePoint]) -> int:
        rows = list(points)
        if not rows:
            return 0

        with psycopg.connect(self._database_url) as conn:
            with conn.cursor() as cursor:
                cursor.executemany(
                    """
                    INSERT INTO features (
                        time, symbol, timeframe, feature_set, values, source_bar_count
                    )
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s)
                    ON CONFLICT (time, symbol, timeframe, feature_set)
                    DO UPDATE SET
                        values = EXCLUDED.values,
                        source_bar_count = EXCLUDED.source_bar_count,
                        created_at = now()
                    """,
                    [
                        (
                            point.time,
                            point.symbol.upper(),
                            point.timeframe.upper(),
                            point.feature_set,
                            json.dumps(point.values),
                            point.source_bar_count,
                        )
                        for point in rows
                    ],
                )
            conn.commit()
        return len(rows)

    def latest_features(
        self,
        *,
        symbol: str,
        timeframe: str,
        feature_set: str = "technical_v1",
        limit: int = 100,
    ) -> list[dict[str, object]]:
        with psycopg.connect(self._database_url, row_factory=dict_row) as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT time, symbol, timeframe, feature_set, values, source_bar_count, created_at
                    FROM features
                    WHERE symbol = %s AND timeframe = %s AND feature_set = %s
                    ORDER BY time DESC
                    LIMIT %s
                    """,
                    (symbol.upper(), timeframe.upper(), feature_set, limit),
                )
                return list(cursor.fetchall())

