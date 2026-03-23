import redis
from app.core.config import settings


def _create_redis_client():
    """Create a Redis client with in-memory fallback if Redis is unavailable."""
    try:
        client = redis.Redis.from_url(
            settings.redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
        )
        client.ping()
        print("✅ Redis connected successfully")
        return client
    except (redis.ConnectionError, redis.TimeoutError, Exception) as e:
        print(f"⚠️  Redis connection failed: {e}")
        print("📌 Using in-memory fallback cache")

        class InMemoryCache:
            def __init__(self):
                self.cache = {}

            def get(self, key):
                return self.cache.get(key)

            def set(self, key, value, ex=None):
                self.cache[key] = value

            def delete(self, key):
                self.cache.pop(key, None)

            def ping(self):
                return True

        return InMemoryCache()


redis_client = _create_redis_client()
