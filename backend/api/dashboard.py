# backend/api/dashboard.py
import time
import traceback
from concurrent.futures import ThreadPoolExecutor

from flask import g
from api import api_bp
from middleware.require_session import require_session
from utils.errors import ok
from db import fetch_one, fetch_all

# Global Cache & Executor
result_cache = {}
# Barcha requestlar uchun bitta pool (max 10 ta thread). 
# DB_POOL_MAX=20 bo'lsa, 10 ta thread bemalol ishlaydi.
global_executor = ThreadPoolExecutor(max_workers=10)

@api_bp.get("/me/dashboard")
@require_session
def dashboard_me():
    u_id = g.u_id

    # CACHING (60 seconds)
    cache_key = f"dashboard_{u_id}"
    cached = result_cache.get(cache_key)
    if cached and (time.time() - cached["time"] < 60):
        return ok(cached["data"])

    def get_user():
        return fetch_one(
            "SELECT u_id, u_name, u_phone, u_username, u_age, u_photo, added_at FROM users WHERE u_id=%s",
            (u_id,),
        )

    def get_categories():
        return fetch_all(
            "SELECT c_id, c_name FROM categories WHERE u_id=%s ORDER BY c_id DESC",
            (u_id,),
        )

    def get_types():
        # MUHIM: img jadvali types bilan t_id orqali bog'langan
        # i_url -> Telegram file_id (AgACAg...)
        return fetch_all(
            """
            SELECT
                t.t_id,
                t.c_id,
                c.c_name,
                t.t_name,
                t.deff,
                t.updated_at,
                t.added_at,
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

    def get_seedlings():
        return fetch_all(
            """
            SELECT s.t_id, t.t_name, s.quality_1, s.quality_2, s.quality_3, s.updated_at, s.added_at
            FROM seedlings s
            LEFT JOIN types t ON t.t_id = s.t_id
            WHERE s.u_id=%s
            ORDER BY s.s_id DESC
            """,
            (u_id,),
        )

    def get_sales_summary():
        return fetch_one(
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

    try:
        # Global executordan foydalanamiz
        f_user = global_executor.submit(get_user)
        f_cats = global_executor.submit(get_categories)
        f_types = global_executor.submit(get_types)
        f_seedlings = global_executor.submit(get_seedlings)
        f_sales = global_executor.submit(get_sales_summary)

        # Natijalarni olish
        user = f_user.result()
        categories = f_cats.result()
        types = f_types.result()
        seedlings = f_seedlings.result()
        sales_summary = f_sales.result()

        response_data = {
            "user": user,
            "categories": categories,
            "types": types,
            "seedlings": seedlings,
            "sales_summary": sales_summary,
        }

        # Save to global cache
        result_cache[cache_key] = {"time": time.time(), "data": response_data}

        return ok(response_data)

    except Exception as e:
        print("-------------- DASHBOARD ERROR --------------")
        traceback.print_exc()
        # Xatoni foydalanuvchiga qaytarmasdan 500 beradi (Flask default), 
        # yoki bu yerda raise qilib logsga yozdik.
        raise e