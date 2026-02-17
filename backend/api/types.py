from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import execute, execute_returning, fetch_all, fetch_one
from utils.cache import invalidate_dashboard_cache


def _to_int(value, field_name: str):
    """
    value int/str/dict bo'lishi mumkin.
    dict bo'lsa c_id/t_id/u_id/id/value dan oladi.
    """
    if isinstance(value, dict):
        value = (
            value.get(field_name)
            or value.get("id")
            or value.get("value")
            or value.get("c_id")
            or value.get("t_id")
            or value.get("u_id")
        )
    try:
        return int(value)
    except Exception:
        return None

@api_bp.post("/types/me")
@require_session
def create_type_me():
    u_id = g.u_id
    data = request.get_json(silent=True) or {}

    c_id = _to_int(data.get("c_id"), "c_id")
    t_name = (data.get("t_name") or "").strip()
    deff = (data.get("deff") or "").strip() or None

    if not c_id:
        return fail("c_id(int) required", 400)
    if not t_name:
        return fail("t_name required", 400)

    # Check if category exists for this user
    cat = fetch_one("SELECT c_id FROM categories WHERE c_id=%s AND u_id=%s", (c_id, u_id))
    if not cat:
        return fail("Guruh topilmadi yoki sizga tegishli emas", 404, code="NOT_FOUND")

    row = execute_returning(
        """
        INSERT INTO types (u_id, c_id, t_name, deff)
        VALUES (%s, %s, %s, %s)
        RETURNING t_id, u_id, c_id, t_name, deff, added_at, updated_at
        """,
        (u_id, c_id, t_name, deff),
    )
    invalidate_dashboard_cache(u_id)
    return ok(row)


@api_bp.post("/types")
@require_api_key
def create_type():
    data = request.get_json(silent=True) or {}

    u_id = _to_int(data.get("u_id"), "u_id")
    c_id = _to_int(data.get("c_id"), "c_id")
    t_name = (data.get("t_name") or "").strip()
    deff = (data.get("deff") or "").strip() or None

    if not u_id:
        return fail("u_id(int) required", 400)
    if not c_id:
        return fail("c_id(int) required", 400)
    if not t_name:
        return fail("t_name required", 400)

    row = execute_returning(
        """
        INSERT INTO types (u_id, c_id, t_name, deff)
        VALUES (%s, %s, %s, %s)
        RETURNING t_id, u_id, c_id, t_name, deff, added_at, updated_at
        """,
        (u_id, c_id, t_name, deff),
    )
    invalidate_dashboard_cache(u_id)
    return ok(row)


@api_bp.get("/types")
@require_api_key
def list_types():
    # optional: u_id, c_id filter
    u_id = request.args.get("u_id", type=int)
    c_id = request.args.get("c_id", type=int)

    q = "SELECT t_id, u_id, c_id, t_name, deff, added_at, updated_at FROM types"
    params = []
    where = []
    if u_id:
        where.append("u_id=%s")
        params.append(u_id)
    if c_id:
        where.append("c_id=%s")
        params.append(c_id)
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY t_id DESC"

    return ok(fetch_all(q, tuple(params)))


@api_bp.get("/types/by-user")
@require_api_key
def list_types_by_user():
    u_id = request.args.get("u_id", type=int)
    c_id = request.args.get("c_id", type=int)

    if not u_id:
        return fail("u_id query param required", 400)
    if not c_id:
        return fail("c_id query param required", 400)

    rows = fetch_all(
        """
        SELECT t_id, u_id, c_id, t_name, deff, added_at, updated_at
        FROM types
        WHERE u_id=%s AND c_id=%s
        ORDER BY t_id DESC
        """,
        (u_id, c_id),
    )
    return ok(rows)


@api_bp.get("/types/<int:t_id>")
@require_api_key
def get_type(t_id: int):
    row = fetch_one(
        """
        SELECT t_id, u_id, c_id, t_name, deff, added_at, updated_at
        FROM types
        WHERE t_id=%s
        """,
        (t_id,),
    )
    if not row:
        return fail("Type not found", 404, code="NOT_FOUND")
    return ok(row)


@api_bp.get("/types/by-id")
@require_api_key
def get_type_by_id():
    u_id = request.args.get("u_id", type=int)
    t_id = request.args.get("t_id", type=int)

    if not u_id:
        return fail("u_id query param required", 400)
    if not t_id:
        return fail("t_id query param required", 400)

    row = fetch_one(
        """
        SELECT t_id, u_id, c_id, t_name, deff, added_at, updated_at
        FROM types
        WHERE u_id=%s AND t_id=%s
        """,
        (u_id, t_id),
    )
    if not row:
        return fail("Type not found", 404, code="NOT_FOUND")
    return ok(row)

@api_bp.get("/type-info")
@require_api_key
def type_info():
    u_id = request.args.get("u_id", type=int)
    t_id = request.args.get("t_id", type=int)

    if not u_id:
        return fail("u_id query param required", 400)
    if not t_id:
        return fail("t_id query param required", 400)

    row = fetch_one(
        """
        SELECT t_id, t_name, deff
        FROM types
        WHERE u_id=%s AND t_id=%s
        """,
        (u_id, t_id),
    )

    if not row:
        return fail("Not found", 404, code="NOT_FOUND")

    return ok(row)


@api_bp.put("/types/<int:t_id>")
@require_api_key
def update_type(t_id: int):
    data = request.get_json(silent=True) or {}
    u_id = _to_int(data.get("u_id"), "u_id")
    t_name = (data.get("t_name") or "").strip()
    deff = (data.get("deff") or "").strip() or None

    if not u_id:
        return fail("u_id(int) required", 400)
    if not t_name:
        return fail("t_name required", 400)

    execute(
        "UPDATE types SET t_name=%s, deff=%s WHERE t_id=%s AND u_id=%s",
        (t_name, deff, t_id, u_id),
    )
    invalidate_dashboard_cache(u_id)
    return ok({"updated": True, "t_id": t_id})


@api_bp.delete("/types/<int:t_id>")
@require_api_key
def delete_type(t_id: int):
    u_id = request.args.get("u_id", type=int)
    if not u_id:
        return fail("u_id query param required", 400)

    execute("DELETE FROM types WHERE t_id=%s AND u_id=%s", (t_id, u_id))
    invalidate_dashboard_cache(u_id)
    return ok({"deleted": True, "t_id": t_id})