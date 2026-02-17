import time

_result_cache = {}

def get_cached_dashboard(u_id):
    cache_key = f"dashboard_{u_id}"
    cached = _result_cache.get(cache_key)
    if cached and (time.time() - cached["time"] < 60):
        return cached["data"]
    return None

def set_cached_dashboard(u_id, data):
    cache_key = f"dashboard_{u_id}"
    _result_cache[cache_key] = {"time": time.time(), "data": data}

def invalidate_dashboard_cache(u_id):
    cache_key = f"dashboard_{u_id}"
    if cache_key in _result_cache:
        del _result_cache[cache_key]
