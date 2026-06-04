import redis

from apps.core.config import settings

pool = redis.ConnectionPool(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    password=getattr(settings, "REDIS_PASSWORD", None),
    db=0,
    decode_responses=True,
    socket_timeout=5,
    retry_on_timeout=True,
    max_connections=10
)

redis_client = redis.Redis(connection_pool=pool)