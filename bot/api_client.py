import os
import aiohttp
from typing import Optional, Dict, Any

API_URL = os.getenv("API_URL", "").rstrip("/")
API_KEY = os.getenv("API_KEY", "")

class BackendAPIError(Exception):
    pass


_session: Optional[aiohttp.ClientSession] = None


def get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session


async def _request(method: str, path: str, json: Optional[Dict[str, Any]] = None):
    if not API_URL or not API_KEY:
        raise BackendAPIError("API_URL or API_KEY is not configured")

    url = f"{API_URL}{path}"
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": API_KEY,
    }

    session = get_session()
    async with session.request(method, url, headers=headers, json=json) as resp:
        data = await resp.json(content_type=None)
        if resp.status >= 400 or not data.get("ok"):
            raise BackendAPIError(data)
        return data["data"]


async def ensure_user(
    u_id: int,
    u_name: Optional[str],
    u_username: Optional[str],
    u_phone: Optional[str] = None,
    u_age: Optional[int] = None,
    u_photo: Optional[str] = None,
):
    return await _request(
        "POST",
        "/api/users/ensure",
        json={
            "u_id": u_id,
            "u_name": u_name,
            "u_username": u_username,
            "u_phone": u_phone,
            "u_age": u_age,
            "u_photo": u_photo,
        },
    )


async def get_user(u_id: int):
    return await _request("GET", f"/api/users/{u_id}")


async def partners_accept(token: str, u_id: int):
    return await _request(
        "POST",
        "/api/partners/accept",
        json={"token": token, "u_id": int(u_id)},
    )


async def partners_decline(token: str, u_id: int):
    return await _request(
        "POST",
        "/api/partners/decline",
        json={"token": token, "u_id": int(u_id)},
    )