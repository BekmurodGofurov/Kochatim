from flask import request, g 
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import execute, fetch_one, fetch_all

@api_bp.get("/me")
@require_session
def get_me():
    u_id = int(g.u_id)

    row = fetch_one(
        """
        SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at
        FROM users
        WHERE u_id=%s
        """,
        (u_id,),
    )
    if not row:
        return fail("User not found", 404, code="NOT_FOUND")

    return ok(row)

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
    u_photo = (data.get("u_photo") or "").strip() or None

    u_age = data.get("u_age")
    if u_age is not None:
        try:
            u_age = int(u_age)
        except Exception:
            u_age = None

    execute(
        """
        INSERT INTO users (u_id, u_name, u_phone, u_username, u_age, u_photo)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (u_id) DO UPDATE SET
            u_name = COALESCE(EXCLUDED.u_name, users.u_name),
            u_phone = COALESCE(EXCLUDED.u_phone, users.u_phone),
            u_username = COALESCE(EXCLUDED.u_username, users.u_username),
            u_age = COALESCE(EXCLUDED.u_age, users.u_age),
            u_photo = COALESCE(EXCLUDED.u_photo, users.u_photo)
        """,
        (u_id, u_name, u_phone, u_username, u_age, u_photo),
    )

    row = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age, added_at, updated_at FROM users WHERE u_id=%s",
        (u_id,),
    )
    return ok(row)


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


@api_bp.get("/gardeners")
def search_gardeners():
    """
    Public: search of gardeners (bog'bonlar).
    query params:
      - q: by u_id exact or u_name/u_username partial
      - limit: default 12 (max 50)
    """
    q = (request.args.get("q") or "").strip()
    limit = request.args.get("limit", type=int) or 12
    limit = max(1, min(limit, 50))

    params = []
    where = ["u_phone IS NOT NULL"]

    # If numeric -> match u_id first
    if q:
        try:
            u_id = int(q)
            where.append("u_id=%s")
            params.append(u_id)
        except Exception:
            where.append("(u_name ILIKE %s OR u_username ILIKE %s)")
            like = f"%{q}%"
            params.extend([like, like])

    rows = fetch_all(
        f"""
        SELECT u_id, u_name, u_username, u_phone, u_photo, added_at
        FROM users
        WHERE {' AND '.join(where)}
        ORDER BY added_at DESC
        LIMIT %s
        """,
        tuple(params + [limit]),
    )
    return ok(rows)
