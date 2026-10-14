from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import fetch_one, execute, execute_returning
from utils.cache import invalidate_dashboard_cache

# One change moves a stock level by at most this much, and a level never goes
# above _MAX_STOCK (an INTEGER column overflows at 2**31 - 1).
_MAX_CHANGE = 100_000_000
_MAX_STOCK = 2_000_000_000


def _quantity(value, name):
    """A whole number of seedlings; a missing value means 0. Raises ValueError."""
    if value in (None, ""):
        return 0
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError(f"{name} must be a whole number")
    if isinstance(value, float):
        # 10.0 is fine; 10.5, NaN and infinity are not.
        if not value.is_integer():
            raise ValueError(f"{name} must be a whole number")
        value = int(value)
    try:
        n = int(value)
    except ValueError:
        raise ValueError(f"{name} must be a whole number")
    if abs(n) > _MAX_CHANGE:
        raise ValueError(f"{name} is out of range")
    return n


def _bad_quantity(exc):
    return fail(str(exc), 400, code="INVALID_QUANTITY")


def _apply_stock_change(u_id, t_id, d1, d2, d3):
    """
    Add (or, if negative, remove) stock in ONE statement.

    Reading the level, checking it, then writing is a race: two parallel
    requests of -50 against a stock of 60 both see "enough" and leave -40.
    Here the guard lives in the UPDATE's WHERE clause, so Postgres decides it
    under the row lock and only one of the two can succeed.

    Returns the new levels, or None when the row is missing or the change
    would push a level below zero (or above the cap).
    """
    return execute_returning(
        """
        UPDATE seedlings
        SET quality_1 = quality_1 + %s,
            quality_2 = quality_2 + %s,
            quality_3 = quality_3 + %s
        WHERE u_id = %s AND t_id = %s
          AND COALESCE(quality_1, 0) + %s BETWEEN 0 AND %s
          AND COALESCE(quality_2, 0) + %s BETWEEN 0 AND %s
          AND COALESCE(quality_3, 0) + %s BETWEEN 0 AND %s
        RETURNING quality_1, quality_2, quality_3
        """,
        (d1, d2, d3, u_id, t_id,
         d1, _MAX_STOCK, d2, _MAX_STOCK, d3, _MAX_STOCK),
    )


def _insufficient(u_id, t_id):
    cur = fetch_one(
        "SELECT quality_1, quality_2, quality_3 FROM seedlings WHERE u_id=%s AND t_id=%s",
        (u_id, t_id),
    ) or {}
    return fail(
        f"Ko'chat soni manfiy bo'lmaydi. Mavjud: q1={int(cur.get('quality_1') or 0)}, "
        f"q2={int(cur.get('quality_2') or 0)}, q3={int(cur.get('quality_3') or 0)}",
        400,
        code="INSUFFICIENT_STOCK",
    )

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

    try:
        q1 = _quantity(data.get("quality_1"), "quality_1")
        q2 = _quantity(data.get("quality_2"), "quality_2")
        q3 = _quantity(data.get("quality_3"), "quality_3")
    except ValueError as e:
        return _bad_quantity(e)

    if _apply_stock_change(u_id, t_id, q1, q2, q3) is None:
        if fetch_one("SELECT s_id FROM seedlings WHERE u_id=%s AND t_id=%s", (u_id, t_id)):
            return _insufficient(u_id, t_id)
        if min(q1, q2, q3) < 0:
            return fail("Ko'chat soni manfiy bo'lmaydi", 400, code="INSUFFICIENT_STOCK")
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

    try:
        cq1 = _quantity(data.get("change_q1"), "change_q1")
        cq2 = _quantity(data.get("change_q2"), "change_q2")
        cq3 = _quantity(data.get("change_q3"), "change_q3")
    except ValueError as e:
        return _bad_quantity(e)

    comment = data.get("comment", "")
    if comment is None:
        comment = ""
    if not isinstance(comment, str) or len(comment) > 1000:
        return fail("comment must be text of at most 1000 characters", 400, code="INVALID_COMMENT")

    price = data.get("price", 0)
    if price is None:
        price = 0
    if isinstance(price, bool) or not isinstance(price, (int, float)) or not 0 <= price <= 10**12:
        return fail("price must be a non-negative number", 400, code="INVALID_PRICE")

    # 1. Update seedlings table (atomically -- see _apply_stock_change)
    if _apply_stock_change(u_id, t_id, cq1, cq2, cq3) is None:
        if fetch_one("SELECT s_id FROM seedlings WHERE u_id=%s AND t_id=%s", (u_id, t_id)):
            return _insufficient(u_id, t_id)
        if min(cq1, cq2, cq3) < 0:
            return fail("Ko'chat soni manfiy bo'lmaydi", 400, code="INSUFFICIENT_STOCK")
        execute(
            "INSERT INTO seedlings (u_id, t_id, quality_1, quality_2, quality_3) VALUES (%s, %s, %s, %s, %s)",
            (u_id, t_id, cq1, cq2, cq3),
        )

    # 2. Log the change
    execute(
        """
        INSERT INTO seedlings_logs (u_id, t_id, change_q1, change_q2, change_q3, price, comment)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (u_id, t_id, cq1, cq2, cq3, price, comment),
    )

    invalidate_dashboard_cache(u_id)
    return ok({"saved": True})
