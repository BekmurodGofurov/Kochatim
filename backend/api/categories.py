# backend/api/categories.py
from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import execute, fetch_one, fetch_all

@api_bp.get("/categories/by-user")
@require_api_key
def list_categories_by_user():
    u_id = request.args.get("u_id", type=int)
    if not u_id:
        return fail("u_id query param required", 400)

    rows = fetch_all(
        "SELECT c_id, c_name FROM categories WHERE u_id=%s ORDER BY c_id DESC",
        (u_id,),
    )
    return ok(rows)

@api_bp.post("/categories")
@require_api_key
def create_category():
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    c_name = (data.get("c_name") or "").strip()

    if not isinstance(u_id, int) or not c_name:
        return fail("u_id(int) and c_name required", 400)

    existing = fetch_one("SELECT c_id FROM categories WHERE u_id=%s AND c_name=%s", (u_id, c_name))
    if existing:
        return ok({"created": False, "c_id": int(existing["c_id"])})

    execute("INSERT INTO categories (u_id, c_name) VALUES (%s, %s)", (u_id, c_name))
    row = fetch_one("SELECT c_id FROM categories WHERE u_id=%s AND c_name=%s", (u_id, c_name))
    return ok({"created": True, "c_id": int(row["c_id"])})


@api_bp.get("/categories")
@require_session
def list_categories_me():
    u_id = g.u_id
    rows = fetch_all(
        "SELECT c_id, c_name, added_at, updated_at FROM categories WHERE u_id=%s ORDER BY c_id DESC",
        (u_id,),
    )
    return ok(rows)

@api_bp.put("/categories/<int:c_id>")
@require_api_key
def update_category(c_id: int):
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    c_name = (data.get("c_name") or "").strip()

    if not isinstance(u_id, int) or not c_name:
        return fail("u_id(int) and c_name required", 400)

    execute(
        "UPDATE categories SET c_name=%s WHERE c_id=%s AND u_id=%s",
        (c_name, c_id, u_id),
    )
    return ok({"updated": True, "c_id": c_id})

@api_bp.delete("/categories/<int:c_id>")
@require_api_key
def delete_category(c_id: int):
    u_id = request.args.get("u_id", type=int)
    if not u_id:
        return fail("u_id query param required", 400)

    execute("DELETE FROM categories WHERE c_id=%s AND u_id=%s", (c_id, u_id))
    return ok({"deleted": True, "c_id": c_id})