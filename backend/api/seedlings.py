from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import fetch_one, execute
from utils.cache import invalidate_dashboard_cache

@api_bp.get("/seedlings/count")
@require_api_key
def seedlings_count():
    u_id = request.args.get("u_id", type=int)
    t_id = request.args.get("t_id", type=int)

    if not u_id:
        return fail("u_id query param required", 400)
    if not t_id:
        return fail("t_id query param required", 400)

    row = fetch_one(
        """
        SELECT quality_1, quality_2, quality_3
        FROM seedlings
        WHERE u_id=%s AND t_id=%s
        """,
        (u_id, t_id),
    )

    if not row:
        return ok({"t_id": t_id, "quality_1": 0, "quality_2": 0, "quality_3": 0})

    return ok(
        {
            "t_id": t_id,
            "quality_1": int(row.get("quality_1") or 0),
            "quality_2": int(row.get("quality_2") or 0),
            "quality_3": int(row.get("quality_3") or 0),
        }
    )

@api_bp.post("/seedlings/set")
@require_api_key
def seedlings_set():
    """
    Bot ishlatadi.
    body: {u_id, t_id, quality_1, quality_2, quality_3}
    Agar mavjud bo'lsa UPDATE, bo'lmasa INSERT.
    """
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    t_id = data.get("t_id")

    if not isinstance(u_id, int) or not isinstance(t_id, int):
        return fail("u_id(int) and t_id(int) required", 400)

    q1 = int(data.get("quality_1", 0) or 0)
    q2 = int(data.get("quality_2", 0) or 0)
    q3 = int(data.get("quality_3", 0) or 0)

    row = fetch_one("SELECT s_id FROM seedlings WHERE u_id=%s AND t_id=%s", (u_id, t_id))
    if row:
        execute(
            """
            UPDATE seedlings 
            SET quality_1 = quality_1 + %s, 
                quality_2 = quality_2 + %s, 
                quality_3 = quality_3 + %s 
            WHERE s_id=%s
            """,
            (q1, q2, q3, int(row["s_id"])),
        )
    else:
        execute(
            "INSERT INTO seedlings (u_id, t_id, quality_1, quality_2, quality_3) VALUES (%s, %s, %s, %s, %s)",
            (u_id, t_id, q1, q2, q3),
        )

    invalidate_dashboard_cache(u_id)
    return ok({"saved": True})


@api_bp.get("/seedlings")
@require_session
def seedlings_get_me():
    """
    Website: GET /api/seedlings?t_id=...
    """
    u_id = g.u_id
    t_id = request.args.get("t_id", type=int)
    if not t_id:
        return fail("t_id query param required", 400)

    row = fetch_one(
        "SELECT quality_1, quality_2, quality_3 FROM seedlings WHERE u_id=%s AND t_id=%s",
        (u_id, t_id),
    )
    if not row:
        return ok({"t_id": t_id, "quality_1": 0, "quality_2": 0, "quality_3": 0})

    return ok(
        {
            "t_id": t_id,
            "quality_1": int(row["quality_1"] or 0),
            "quality_2": int(row["quality_2"] or 0),
            "quality_3": int(row["quality_3"] or 0),
        }
    )
@api_bp.post("/seedlings/update")
@require_session
def seedlings_update_me():
    """
    Website: POST /api/seedlings/update
    body: {t_id, change_q1, change_q2, change_q3, comment}
    """
    u_id = g.u_id
    data = request.get_json(silent=True) or {}
    t_id = data.get("t_id")

    if not isinstance(t_id, int):
        return fail("t_id(int) required", 400)

    cq1 = int(data.get("change_q1", 0) or 0)
    cq2 = int(data.get("change_q2", 0) or 0)
    cq3 = int(data.get("change_q3", 0) or 0)
    comment = data.get("comment", "")

    # 1. Update seedlings table
    row = fetch_one("SELECT s_id FROM seedlings WHERE u_id=%s AND t_id=%s", (u_id, t_id))
    if row:
        execute(
            """
            UPDATE seedlings 
            SET quality_1 = quality_1 + %s, 
                quality_2 = quality_2 + %s, 
                quality_3 = quality_3 + %s 
            WHERE s_id=%s
            """,
            (cq1, cq2, cq3, int(row["s_id"])),
        )
    else:
        execute(
            "INSERT INTO seedlings (u_id, t_id, quality_1, quality_2, quality_3) VALUES (%s, %s, %s, %s, %s)",
            (u_id, t_id, cq1, cq2, cq3),
        )

    # 2. Log the change
    price = data.get("price", 0)
    execute(
        """
        INSERT INTO seedlings_logs (u_id, t_id, change_q1, change_q2, change_q3, price, comment)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (u_id, t_id, cq1, cq2, cq3, price, comment),
    )

    invalidate_dashboard_cache(u_id)
    return ok({"saved": True})
