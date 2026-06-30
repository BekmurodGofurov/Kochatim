import json
import redis

# Redis mijoziga ulanish (Load Balancer serveridagi markaziy kesh)
redis_client = redis.Redis(
    host='newUbuntu_IP',
    port=6379,
    password='kuchli_parol',
    decode_responses=True
)


def get_cache(key: str):
    """Redisdan ma'lumotni o'qiydi (Cache Hit/Miss)."""
    try:
        val = redis_client.get(key)
        if val is None:
            return None
        return json.loads(val)
    except Exception as e:
        print(f"Redis GET error: {e}")
        return None


def set_cache(key: str, data, ttl: int = 60):
    """Ma'lumotni JSON ga o'girib Redisga TTL bilan saqlaydi."""
    try:
        val = json.dumps(data)
        redis_client.setex(key, ttl, val)
    except Exception as e:
        print(f"Redis SET error: {e}")


def invalidate_cache(key: str):
    """Redisdan ma'lumotni o'chiradi (Instant Logout uchun)."""
    try:
        redis_client.delete(key)
    except Exception as e:
        print(f"Redis DELETE error: {e}")


def invalidate_prefix(prefix: str):
    """Prefix bilan boshlanadigan barcha kesh kalitlarini o'chiradi."""
    try:
        cursor = '0'
        while cursor != 0:
            cursor, keys = redis_client.scan(cursor=cursor, match=f"{prefix}*", count=100)
            if keys:
                redis_client.delete(*keys)
    except Exception as e:
        print(f"Redis invalidate prefix error: {e}")


# --- Dashboard uchun qulaylik wrappers ---
def get_cached_dashboard(u_id):
    return get_cache(f"dashboard_{u_id}")

def set_cached_dashboard(u_id, data):
    set_cache(f"dashboard_{u_id}", data, ttl=60)

def invalidate_dashboard_cache(u_id):
    invalidate_cache(f"dashboard_{u_id}")
