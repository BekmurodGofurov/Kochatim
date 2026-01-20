from flask import request
from api import api_bp
from middleware.require_api_key import require_api_key
from utils.errors import ok, fail
from db import execute, fetch_one


@api_bp.post("/img")
@require_api_key
def upsert_img():
    data = request.get_json(silent=True) or {}
    t_id = data.get("t_id")
    i_url = (data.get("i_url") or "").strip()

    try:
        t_id = int(t_id)
    except Exception:
        return fail("t_id(int) required", 400)

    if not i_url:
        return fail("i_url required", 400)

    # Sizning table: img(i_id serial, t_id int, i_url text, ...)
    # 1 type = 1 img logika: bor bo'lsa update, bo'lmasa insert
    row = fetch_one("SELECT i_id FROM img WHERE t_id=%s ORDER BY i_id DESC LIMIT 1", (t_id,))
    if row:
        execute(
            "UPDATE img SET i_url=%s, updated_at=NOW() WHERE t_id=%s",
            (i_url, t_id),
        )
    else:
        execute(
            "INSERT INTO img (t_id, i_url) VALUES (%s, %s)",
            (t_id, i_url),
        )

    return ok({"saved": True, "t_id": t_id})


@api_bp.get("/img/by-type")
@require_api_key
def get_img_by_type():
    t_id = request.args.get("t_id", type=int)
    if not t_id:
        return fail("t_id query param required", 400)

    row = fetch_one("SELECT i_url FROM img WHERE t_id=%s ORDER BY i_id DESC LIMIT 1", (t_id,))
    if not row:
        return ok(None)

    return ok(row.get("i_url"))