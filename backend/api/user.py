from flask import request
from api import api_bp
from middleware.require_api_key import require_api_key
from utils.errors import ok, fail
from db import execute, fetch_one


@api_bp.post("/users/ensure")
@require_api_key
def ensure_user():
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    if not isinstance(u_id, int):
        return fail("u_id(int) required", 400)

    u_name = (data.get("u_name") or "").strip() or None
    u_phone = (data.get("u_phone") or "").strip() or None
    u_username = (data.get("u_username") or "").strip() or None

    u_age = data.get("u_age")
    if u_age is not None:
        try:
            u_age = int(u_age)
        except Exception:
            u_age = None

    execute(
        """
        INSERT INTO users (u_id, u_name, u_phone, u_username, u_age)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (u_id) DO UPDATE SET
            u_name = COALESCE(EXCLUDED.u_name, users.u_name),
            u_phone = COALESCE(EXCLUDED.u_phone, users.u_phone),
            u_username = COALESCE(EXCLUDED.u_username, users.u_username),
            u_age = COALESCE(EXCLUDED.u_age, users.u_age)
        """,
        (u_id, u_name, u_phone, u_username, u_age),
    )

    return ok({"saved": True})


@api_bp.get("/users/<int:u_id>")
@require_api_key
def get_user(u_id: int):
    row = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at FROM users WHERE u_id=%s",
        (u_id,),
    )
    if not row:
        return fail("User not found", 404, code="NOT_FOUND")
    return ok(row)