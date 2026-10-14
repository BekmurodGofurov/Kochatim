# backend/api/public.py
from flask import Blueprint, current_app
from utils.errors import ok, fail
from db import fetch_all

public_bp = Blueprint('public', __name__)

@public_bp.get("/api/v1/public/categories")
def public_categories():
    try:
        rows = fetch_all("SELECT c_id AS id, c_name AS name FROM categories ORDER BY c_name ASC")
        return ok(rows)
    except Exception:
        # The exception text can carry SQL or a connection string; log it,
        # never return it.
        current_app.logger.exception("public categories failed")
        return fail("Failed to fetch categories", 500)
