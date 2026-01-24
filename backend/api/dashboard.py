# backend/api/dashboard.py
from flask import g
from api import api_bp
from middleware.require_session import require_session
from utils.errors import ok
from db import fetch_one, fetch_all


@api_bp.get("/me/dashboard")
@require_session
def dashboard_me():
    u_id = g.u_id

    user = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age FROM users WHERE u_id=%s",
        (u_id,),
    )

    categories = fetch_all(
        "SELECT c_id, c_name FROM categories WHERE u_id=%s ORDER BY c_id DESC",
        (u_id,),
    )

    # MUHIM: img jadvali types bilan t_id orqali bog'langan
    # i_url -> Telegram file_id (AgACAg...)
    types = fetch_all(
        """
        SELECT
            t.t_id,
            t.c_id,
            c.c_name,
            t.t_name,
            t.deff,
            img.i_url
        FROM types t
        LEFT JOIN categories c ON c.c_id = t.c_id
        LEFT JOIN LATERAL (
            SELECT i_url
            FROM img
            WHERE t_id = t.t_id
            ORDER BY i_id DESC
            LIMIT 1
        ) img ON TRUE
        WHERE t.u_id=%s
        ORDER BY t.t_id DESC
        """,
        (u_id,),
    )

    seedlings = fetch_all(
        """
        SELECT s.t_id, t.t_name, s.quality_1, s.quality_2, s.quality_3
        FROM seedlings s
        LEFT JOIN types t ON t.t_id = s.t_id
        WHERE s.u_id=%s
        ORDER BY s.s_id DESC
        """,
        (u_id,),
    )

    sales_summary = fetch_one(
        """
        SELECT
            COALESCE(SUM(q1_sold),0) AS q1_sold,
            COALESCE(SUM(q2_sold),0) AS q2_sold,
            COALESCE(SUM(q3_sold),0) AS q3_sold,
            COALESCE(SUM(price),0) AS total_price
        FROM sales
        WHERE u_id=%s
        """,
        (u_id,),
    )

    return ok(
        {
            "user": user,
            "categories": categories,
            "types": types,
            "seedlings": seedlings,
            "sales_summary": sales_summary,
        }
    )