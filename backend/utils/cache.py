import time

# NOTE: in-process cache — Gunicorn multi-worker rejimida har worker o'z
# nusxasini saqlaydi. Workerlar orasida ulashish kerak bo'lsa Redis kerak.
_store: dict[str, dict] = {}


def get_cache(key: str):
    entry = _store.get(key)
    if entry is None:
        return None
    if time.time() - entry["time"] >= entry["ttl"]:
        del _store[key]
        return None
    return entry["data"]


def set_cache(key: str, data, ttl: int = 60):
    _store[key] = {"time": time.time(), "data": data, "ttl": ttl}


def invalidate_cache(key: str):
    _store.pop(key, None)


def invalidate_prefix(prefix: str):
    """prefix bilan boshlanadigan barcha kesh kalitlarini o'chiradi."""
    to_del = [k for k in _store if k.startswith(prefix)]
    for k in to_del:
        del _store[k]


# --- Dashboard uchun qulaylik wrappers (back-compat) ---

def get_cached_dashboard(u_id):
    return get_cache(f"dashboard_{u_id}")


def set_cached_dashboard(u_id, data):
    set_cache(f"dashboard_{u_id}", data, ttl=60)


def invalidate_dashboard_cache(u_id):
    invalidate_cache(f"dashboard_{u_id}")
