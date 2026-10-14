# backend/api/sales.py
from flask import request, g
from api import api_bp
from api.seedlings import _MAX_CHANGE, _quantity
from middleware.require_api_key import require_api_key
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import fetch_all, fetch_one, transaction
from utils.cache import invalidate_dashboard_cache


class _InsufficientStock(Exception):
    """Raised inside the transaction so everything done so far is rolled back."""

    def __init__(self, stock):
        self.stock = stock


@api_bp.errorhandler(_InsufficientStock)
def _insufficient_stock(e):
    s = e.stock
    return fail(
        f"Yetarli ko'chat yo'q. Mavjud: q1={int(s.get('quality_1') or 0)}, "
        f"q2={int(s.get('quality_2') or 0)}, q3={int(s.get('quality_3') or 0)}",
        400,
        code="INSUFFICIENT_STOCK",
    )


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

    try:
        q1 = _quantity(data.get("q1_sold"), "q1_sold")
        q2 = _quantity(data.get("q2_sold"), "q2_sold")
        q3 = _quantity(data.get("q3_sold"), "q3_sold")
    except ValueError as e:
        return fail(str(e), 400, code="INVALID_QUANTITY")
    if min(q1, q2, q3) < 0:
        return fail("Sold quantities cannot be negative", 400, code="INVALID_QUANTITY")

    price = data.get("price")
    if isinstance(price, bool):
        return fail("price(int) required", 400)
    try:
        price = int(price)
    except Exception:
        return fail("price(int) required", 400)
    if price < 0 or price > 10**12:
        return fail("price out of range", 400, code="INVALID_PRICE")

    # Ownership: t_id va c_id bu u_id ga tegishli ekanligini tekshirish
    owner_row = fetch_one(
        "SELECT t_id FROM types WHERE t_id=%s AND c_id=%s AND u_id=%s",
        (t_id, c_id, u_id),
    )
    if not owner_row:
        return fail("Type not found for this user/category", 404, code="NOT_FOUND")

    # The stock check, the stock write and the sale record are one unit: if
    # the connection drops between them, nothing is half-recorded (a sale
    # without the stock leaving, or stock gone with no sale).
    with transaction() as tx:
        updated = tx.execute(
            """
            UPDATE seedlings
            SET quality_1 = quality_1 - %s,
                quality_2 = quality_2 - %s,
                quality_3 = quality_3 - %s
            WHERE u_id=%s AND t_id=%s
              AND COALESCE(quality_1, 0) - %s >= 0
              AND COALESCE(quality_2, 0) - %s >= 0
              AND COALESCE(quality_3, 0) - %s >= 0
            """,
            (q1, q2, q3, u_id, t_id, q1, q2, q3),
        )
        if updated == 0:
            # Either there is no stock row at all (the sale is still recorded,
            # as before) or there is not enough. The guard above decided it
            # under the row lock; this only picks the message.
            stock = tx.fetch_one(
                "SELECT quality_1, quality_2, quality_3 FROM seedlings WHERE u_id=%s AND t_id=%s",
                (u_id, t_id),
            )
            if stock:
                raise _InsufficientStock(stock)

        tx.execute(
            "INSERT INTO sales (u_id,c_id,t_id,q1_sold,q2_sold,q3_sold,price) VALUES (%s,%s,%s,%s,%s,%s,%s)",
            (u_id, c_id, t_id, q1, q2, q3, price),
        )

    invalidate_dashboard_cache(u_id)
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