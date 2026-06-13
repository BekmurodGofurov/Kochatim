# backend/api/dashboard.py
import traceback
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor

from flask import g
from api import api_bp
from middleware.require_session import require_session
from utils.errors import ok, fail
from db import fetch_one, fetch_all
from utils.cache import get_cache, set_cache, get_cached_dashboard, set_cached_dashboard
from config import Config

# Dashboard uchun bitta executor — max_workers DB pool hajmidan oshmasin
_EXECUTOR_WORKERS = max(2, Config.DB_POOL_MAX // 2)
global_executor = ThreadPoolExecutor(max_workers=_EXECUTOR_WORKERS)

@api_bp.get("/me/dashboard")
@require_session
def dashboard_me():
    u_id = g.u_id

    # CACHING (60 seconds)
    cached_data = get_cached_dashboard(u_id)
    if cached_data:
        return ok(cached_data)

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
        set_cached_dashboard(u_id, response_data)

        return ok(response_data)

    except Exception as e:
        print("-------------- DASHBOARD ERROR --------------")
        traceback.print_exc()
        # Xatoni foydalanuvchiga qaytarmasdan 500 beradi (Flask default), 
        # yoki bu yerda raise qilib logsga yozdik.
        raise e


@api_bp.get("/partners/dashboards")
@require_session
def partner_dashboards():
    """
    Barcha hamkorlarning inventarini bitta so'rovda qaytaradi.
    N+1 o'rniga 3 ta bulk query ishlatiladi.
    """
    u_id = g.u_id
    key = f"partner_dashboards_{u_id}"

    cached = get_cache(key)
    if cached is not None:
        return ok(cached)

    partner_rows = fetch_all(
        """
        SELECT u.u_id, u.u_name, u.u_phone, u.u_username, u.u_age, u.u_photo, p.created_at
        FROM partners p
        JOIN users u ON u.u_id = p.p_id
        WHERE p.u_id = %s
        ORDER BY p.created_at DESC
        """,
        (u_id,),
    )

    if not partner_rows:
        set_cache(key, [], ttl=300)
        return ok([])

    partner_ids = [int(p["u_id"]) for p in partner_rows]
    ph = ",".join(["%s"] * len(partner_ids))

    all_categories = fetch_all(
        f"SELECT u_id AS owner_id, c_id, c_name FROM categories WHERE u_id IN ({ph}) ORDER BY c_id DESC",
        tuple(partner_ids),
    )
    all_types = fetch_all(
        f"""
        SELECT t.u_id AS owner_id, t.t_id, t.c_id, t.t_name, t.deff, t.updated_at, t.added_at, img.i_url
        FROM types t
        LEFT JOIN LATERAL (
            SELECT i_url FROM img WHERE t_id = t.t_id ORDER BY i_id DESC LIMIT 1
        ) img ON TRUE
        WHERE t.u_id IN ({ph})
        ORDER BY t.t_id DESC
        """,
        tuple(partner_ids),
    )
    all_seedlings = fetch_all(
        f"""
        SELECT s.u_id AS owner_id, s.t_id, t.t_name,
               s.quality_1, s.quality_2, s.quality_3, s.updated_at, s.added_at
        FROM seedlings s
        LEFT JOIN types t ON t.t_id = s.t_id
        WHERE s.u_id IN ({ph})
        ORDER BY s.s_id DESC
        """,
        tuple(partner_ids),
    )

    cats_by  = defaultdict(list)
    types_by = defaultdict(list)
    seeds_by = defaultdict(list)

    for row in all_categories:
        oid = int(row["owner_id"])
        cats_by[oid].append({k: v for k, v in row.items() if k != "owner_id"})
    for row in all_types:
        oid = int(row["owner_id"])
        types_by[oid].append({k: v for k, v in row.items() if k != "owner_id"})
    for row in all_seedlings:
        oid = int(row["owner_id"])
        seeds_by[oid].append({k: v for k, v in row.items() if k != "owner_id"})

    result = []
    for p in partner_rows:
        pid = int(p["u_id"])
        result.append({
            "partner":     p,
            "categories":  cats_by.get(pid, []),
            "types":       types_by.get(pid, []),
            "seedlings":   seeds_by.get(pid, []),
        })

    set_cache(key, result, ttl=300)
    return ok(result)


@api_bp.get("/users/<int:u_id>/dashboard")
def dashboard_user(u_id: int):
    """
    Public read-only dashboard for a user (bog'bon profili uchun).
    """
    # no caching here (partners view can be larger & less frequent)
    user = fetch_one(
        "SELECT u_id, u_name, u_phone, u_username, u_age, u_photo, added_at FROM users WHERE u_id=%s",
        (u_id,),
    )
    if not user:
        return fail("User not found", 404, code="NOT_FOUND")
    categories = fetch_all(
        "SELECT c_id, c_name FROM categories WHERE u_id=%s ORDER BY c_id DESC",
        (u_id,),
    )
    types = fetch_all(
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
    seedlings = fetch_all(
        """
        SELECT s.t_id, t.t_name, s.quality_1, s.quality_2, s.quality_3, s.updated_at, s.added_at
        FROM seedlings s
        LEFT JOIN types t ON t.t_id = s.t_id
        WHERE s.u_id=%s
        ORDER BY s.s_id DESC
        """,
        (u_id,),
    )

    return ok(
        {
            "user": user,
            "categories": categories,
            "types": types,
            "seedlings": seedlings,
        }
    )