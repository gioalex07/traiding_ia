import psycopg
import redis

from rac.config import Settings


def check_postgres(settings: Settings) -> dict[str, object]:
    if not settings.database_url:
        return {"configured": False, "ok": False, "reason": "missing_database_url"}
    try:
        with psycopg.connect(
            settings.database_url.replace("postgresql+psycopg://", "postgresql://"),
            connect_timeout=2,
        ) as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
        return {"configured": True, "ok": True}
    except psycopg.Error as exc:
        return {"configured": True, "ok": False, "reason": exc.__class__.__name__}


def check_redis(settings: Settings) -> dict[str, object]:
    if not settings.redis_url:
        return {"configured": False, "ok": False, "reason": "missing_redis_url"}
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2, socket_timeout=2)
        client.ping()
        return {"configured": True, "ok": True}
    except redis.RedisError as exc:
        return {"configured": True, "ok": False, "reason": exc.__class__.__name__}

