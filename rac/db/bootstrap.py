from pathlib import Path

import psycopg

from rac.config import Settings

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"


def bootstrap_database(settings: Settings) -> None:
    if not settings.database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    with psycopg.connect(settings.database_url.replace("postgresql+psycopg://", "postgresql://")) as conn:
        with conn.cursor() as cursor:
            for migration in sorted(MIGRATIONS_DIR.glob("*.sql")):
                cursor.execute(migration.read_text(encoding="utf-8"))
        conn.commit()

