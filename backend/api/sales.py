# backend/api/sales.py
from flask import request, g
from api import api_bp
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import execute, fetch_all


@api_bp.post("/sales")
@require_api_key
def add_sale():
    """
    Bot ishlatadi:
    1) sales insert
    2) seedlings'dan ayirish
    body: {u_id,c_id,t_id,q1_sold,q2_sold,q3_sold,price}
    """
    data = request.get_json(silent=True) or {}
    u_id = data.get("u_id")
    c_id = data.get("c_id")
    t_id = data.get("t_id")

    if not isinstance(u_id, int) or not isinstance(c_id, int) or not isinstance(t_id, int):
        return fail("u_id(int), c_id(int), t_id(int) required", 400)

    q1 = int(data.get("q1_sold", 0) or 0)
    q2 = int(data.get("q2_sold", 0) or 0)
    q3 = int(data.get("q3_sold", 0) or 0)
    price = data.get("price")

    execute(
        "INSERT INTO sales (u_id,c_id,t_id,q1_sold,q2_sold,q3_sold,price) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (u_id, c_id, t_id, q1, q2, q3, price),
    )

    execute(
        """
        UPDATE seedlings
        SET quality_1 = quality_1 - %s,
            quality_2 = quality_2 - %s,
            quality_3 = quality_3 - %s
        WHERE u_id=%s AND t_id=%s
        """,
        (q1, q2, q3, u_id, t_id),
    )

    return ok({"saved": True})


@api_bp.get("/sales")
@require_session
def list_sales_me():
    u_id = g.u_id
    rows = fetch_all(
        "SELECT sale_id,c_id,t_id,q1_sold,q2_sold,q3_sold,price,sold_at FROM sales WHERE u_id=%s ORDER BY sale_id DESC LIMIT 200",
        (u_id,),
    )
    return ok(rows)