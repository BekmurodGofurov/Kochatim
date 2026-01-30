import aiohttp
import time
from typing import Optional, Dict, Any

from data.config import API_URL, API_KEY


class BackendAPIError(Exception):
    pass


async def _request(
    method: str,
    path: str,
    json: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
):
    if not API_URL or not API_KEY:
        raise BackendAPIError("API_URL or API_KEY is not configured")

    url = f"{API_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }

    t0 = time.perf_counter()
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=headers, json=json, params=params) as resp:
            status = resp.status
            try:
                data = await resp.json(content_type=None)
            except Exception:
                # Agar JSON emas bo'lsa (masalan 404 HTML), textni olib error beramiz
                body_text = await resp.text()
                dt_ms = (time.perf_counter() - t0) * 1000
                print(f"[HTTP ERROR] {method} {path} -> {status} {dt_ms:.0f}ms. Body: {body_text[:100]}")
                raise BackendAPIError(f"Backend HTTP {status} (Not JSON)")

    dt_ms = (time.perf_counter() - t0) * 1000
    print(f"[HTTP] {method} {path} -> {status} {dt_ms:.0f}ms")

    if status >= 400 or not data.get("ok"):
        raise BackendAPIError(data)

    return data.get("data")


# =========================
# USERS
# =========================
async def db_start():
    # old compat: bot/app.py da chaqirilgan bo'lishi mumkin
    return True


async def new_user(u_id: int, u_name: Optional[str] = None, u_username: Optional[str] = None,
                   u_phone: Optional[str] = None, u_age: Optional[int] = None):
    return await _request(
        "POST",
        "/api/users/ensure",
        json={
            "u_id": int(u_id),
            "u_name": u_name,
            "u_username": u_username,
            "u_phone": u_phone,
            "u_age": u_age,
        },
    )


async def ensure_user(u_id: int, u_name: Optional[str] = None, u_username: Optional[str] = None,
                      u_phone: Optional[str] = None, u_age: Optional[int] = None):
    return await new_user(u_id, u_name, u_username, u_phone, u_age)


async def get_user(u_id: int):
    return await _request("GET", f"/api/users/{int(u_id)}")


# =========================
# CATEGORIES (handlerlar string list kutadi)
# =========================
async def get_all_cat_rows(u_id: int):
    return await _request("GET", "/api/categories/by-user", params={"u_id": int(u_id)})


async def get_all_cat(u_id: int):
    rows = await get_all_cat_rows(u_id)
    if not rows:
        return []
    return [str(r.get("c_name")) for r in rows if r.get("c_name")]


async def get_cat_id(u_id: int, c_name):
    # c_name ba'zan dict bo'lib kelib qolsa ham ko'taramiz
    if isinstance(c_name, dict):
        if c_name.get("c_id") is not None:
            try:
                return int(c_name["c_id"])
            except Exception:
                pass
        c_name = c_name.get("c_name")

    name = str(c_name or "").strip().lower()
    rows = await get_all_cat_rows(u_id)
    for r in (rows or []):
        if str(r.get("c_name") or "").strip().lower() == name:
            return int(r["c_id"])
    return None

async def new_cat(u_id: int, c_name: str):
    # backend: POST /api/categories
    return await _request(
        "POST",
        "/api/categories",
        json={"u_id": int(u_id), "c_name": c_name},
    )

# =========================
# TYPES (handlerlar string list kutadi)
# =========================
async def get_all_ty_rows(u_id: int, c_id: int):
    return await _request("GET", "/api/types/by-user", params={"u_id": int(u_id), "c_id": int(c_id)})


async def get_all_ty(u_id: int, c_id: int):
    rows = await get_all_ty_rows(u_id, c_id)
    if not rows:
        return []
    return [str(r.get("t_name")) for r in rows if r.get("t_name")]


async def get_type_id(u_id: int, c_id: int, t_name):
    if isinstance(t_name, dict):
        if t_name.get("t_id") is not None:
            try:
                return int(t_name["t_id"])
            except Exception:
                pass
        t_name = t_name.get("t_name")

    name = str(t_name or "").strip().lower()
    rows = await get_all_ty_rows(u_id, c_id)
    for r in (rows or []):
        if str(r.get("t_name") or "").strip().lower() == name:
            return int(r["t_id"])
    return None

async def new_ty(u_id: int, c_id, t_name: str, deff: Optional[str] = None):
    # c_id ba'zan dict bo'lib kelib qolsa (masalan {"c_id":1,"c_name":"Olma"}) -> ichidan id ni olamiz
    if isinstance(c_id, dict):
        c_id = c_id.get("c_id") or c_id.get("id")

    return await _request(
        "POST",
        "/api/types",
        json={
            "u_id": int(u_id),
            "c_id": int(c_id),
            "t_name": t_name,
            "deff": deff,
        },
    )


async def get_a_ty(u_id: int, t_id: int):
    # backend: GET /api/types/by-id?u_id=&t_id=
    return await _request("GET", "/api/types/by-id", params={"u_id": int(u_id), "t_id": int(t_id)})


async def get_type_info(u_id: int, t_id: int):
    # backend: GET /api/type-info?u_id=&t_id=
    return await _request("GET", "/api/type-info", params={"u_id": int(u_id), "t_id": int(t_id)})


# =========================
# SEEDLINGS (compat)
# =========================
async def new_seedling(u_id: int, t_id: int, q1: int, q2: int, q3: int):
    # backend: POST /api/seedlings/set
    return await _request(
        "POST",
        "/api/seedlings/set",
        json={
            "u_id": int(u_id),
            "t_id": int(t_id),
            "quality_1": int(q1 or 0),
            "quality_2": int(q2 or 0),
            "quality_3": int(q3 or 0),
        },
    )


async def get_seedling_count(u_id: int, t_id: int):
    # backend: GET /api/seedlings/count?u_id=&t_id=
    return await _request("GET", "/api/seedlings/count", params={"u_id": int(u_id), "t_id": int(t_id)})


# =========================
# IMAGES (compat)
# =========================
async def add_new_img(t_id: int, i_url: str):
    # backend: POST /api/img
    return await _request("POST", "/api/img", json={"t_id": int(t_id), "i_url": i_url})


async def get_img_url(t_id: int):
    # backend: GET /api/img/by-type?t_id=
    return await _request("GET", "/api/img/by-type", params={"t_id": int(t_id)})


# =========================
# SALES (compat)
# =========================
async def add_sale(u_id: int, c_id: int, t_id: int, q1_sold=0, q2_sold=0, q3_sold=0, price=None):
    # backend: POST /api/sales
    return await _request(
        "POST",
        "/api/sales",
        json={
            "u_id": int(u_id),
            "c_id": int(c_id),
            "t_id": int(t_id),
            "q1_sold": int(q1_sold or 0),
            "q2_sold": int(q2_sold or 0),
            "q3_sold": int(q3_sold or 0),
            "price": price,
        },
    )