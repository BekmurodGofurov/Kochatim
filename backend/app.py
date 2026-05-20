# backend/app.py
from dotenv import load_dotenv
load_dotenv()
import os

from flask import Flask, request, make_response
from config import Config
from utils.errors import ok, fail
from extensions import init_pool
from db_init import init_db

_ALLOWED_ORIGINS = {
    "https://kochatim.uz",
    "https://www.kochatim.uz",
    "https://app.kochatim.uz",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
}

from auth import auth_bp
from api import api_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["ENV"] = Config.FLASK_ENV

    # init pool + schema
    init_pool()
    init_db()

    # blueprints
    app.register_blueprint(auth_bp)  # /auth/*
    app.register_blueprint(api_bp)   # /api/*

    @app.get("/health")
    def health():
        return ok({"status": "up"})

    @app.errorhandler(404)
    def not_found(_):
        return fail("Not found", 404)

    @app.errorhandler(Exception)
    def server_error(e):
        return fail("Server error", 500, extra=str(e))

    return app


app = create_app()

def _cors_origin(request_origin: str) -> str:
    if request_origin in _ALLOWED_ORIGINS:
        return request_origin
    return "null"


@app.before_request
def _cors_preflight():
    if request.method == "OPTIONS":
        resp = make_response("", 204)
        origin = _cors_origin(request.headers.get("Origin", ""))
        resp.headers["Access-Control-Allow-Origin"] = origin
        resp.headers["Vary"] = "Origin"
        resp.headers["Access-Control-Allow-Credentials"] = "true"
        resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-KEY"
        resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        return resp


@app.after_request
def _add_cors_headers(resp):
    origin = _cors_origin(request.headers.get("Origin", ""))
    resp.headers["Access-Control-Allow-Origin"] = origin
    resp.headers["Vary"] = "Origin"
    resp.headers["Access-Control-Allow-Credentials"] = "true"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-API-KEY"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
    return resp

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = Config.FLASK_ENV != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)