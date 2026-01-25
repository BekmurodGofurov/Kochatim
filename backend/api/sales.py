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
    try:
        price = int(price)
    except Exception:
        return fail("price(int) required", 400)

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
    """
    Web ishlatadi:
    - history: sotuvlar ro'yxati (UI uchun name/category/date/qty/price)
    - pie: kategoriya bo'yicha tushum yig'indisi
    """
    u_id = g.u_id

    # 1) HISTORY (200 ta)
    history = fetch_all(
        """
        SELECT
            s.sale_id,
            s.price,
            s.sold_at,
            s.q1_sold,
            s.q2_sold,
            s.q3_sold,
            c.c_id,
            c.c_name,
            t.t_id,
            t.t_name
        FROM sales s
        LEFT JOIN categories c ON c.c_id = s.c_id
        LEFT JOIN types t ON t.t_id = s.t_id
        WHERE s.u_id=%s
        ORDER BY s.sale_id DESC
        LIMIT 200
        """,
        (u_id,),
    )

    # UI'ga qulay fieldlar
    history_ui = []
    for r in history:
        qty = int(r.get("q1_sold") or 0) + int(r.get("q2_sold") or 0) + int(r.get("q3_sold") or 0)
        history_ui.append(
            {
                "id": r.get("sale_id"),
                "name": r.get("t_name") or "—",
                "category": r.get("c_name") or "—",
                "date": r.get("sold_at"),   # ISO bo‘lib ketadi
                "qty": qty,
                "price": int(r.get("price") or 0),
            }
        )

    # 2) PIE (kategoriya bo‘yicha tushum)
    pie = fetch_all(
        """
        SELECT
            c.c_name AS name,
            COALESCE(SUM(s.price), 0) AS value
        FROM sales s
        LEFT JOIN categories c ON c.c_id = s.c_id
        WHERE s.u_id=%s
        GROUP BY c.c_name
        ORDER BY value DESC
        """,
        (u_id,),
    )

    return ok(
        {
            "history": history_ui,
            "pie": pie,
        }
    )