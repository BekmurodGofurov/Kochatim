import time

# NOTE: bu in-process cache — Gunicorn multi-worker rejimida har worker o'z
# nusxasini saqlaydi. Redis yoki shared cache kerak bo'lsa alohida sozlanadi.
_result_cache = {}
_TTL = 60


def get_cached_dashboard(u_id):
    cache_key = f"dashboard_{u_id}"
    cached = _result_cache.get(cache_key)
    if cached is None:
        return None
    if time.time() - cached["time"] >= _TTL:
        del _result_cache[cache_key]
        return None
    return cached["data"]


def set_cached_dashboard(u_id, data):
    cache_key = f"dashboard_{u_id}"
    _result_cache[cache_key] = {"time": time.time(), "data": data}


def invalidate_dashboard_cache(u_id):
    cache_key = f"dashboard_{u_id}"
    _result_cache.pop(cache_key, None)
