# backend/api/public.py
from flask import Blueprint
from utils.errors import ok, fail
from db import fetch_all

public_bp = Blueprint('public', __name__)

@public_bp.get("/api/v1/public/categories")
def public_categories():
    try:
        rows = fetch_all("SELECT c_id AS id, c_name AS name FROM categories ORDER BY c_name ASC")
        return ok(rows)
    except Exception as e:
        return fail("Failed to fetch categories", 500, extra=str(e))
