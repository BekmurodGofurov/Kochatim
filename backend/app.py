# backend/app.py
import os
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from flask import Flask, request, make_response
from config import Config
from utils.errors import ok, fail
from extensions import init_pool
from db_init import init_db

from auth import auth_bp
from api import api_bp
from api.public import public_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.config["ENV"] = Config.FLASK_ENV

    # init pool + schema
    init_pool()
    init_db()

    # blueprints
    app.register_blueprint(auth_bp)  # /auth/*
    app.register_blueprint(api_bp)   # /api/*
    app.register_blueprint(public_bp) # /api/v1/public/*

    @app.get("/health")
    def health():
        server_identity = os.getenv('SERVER_NAME', 'unknown_server')
        return ok({
                "status": "up",
                "server": server_identity
            })

    @app.errorhandler(404)
    def not_found(_):
        return fail("Not found", 404)

    @app.errorhandler(Exception)
    def server_error(e):
        return fail("Server error", 500, extra=str(e))

    return app


app = create_app()

def _cors_origin(request_origin: str) -> str:
    if request_origin in Config.ALLOWED_ORIGINS:
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
    debug = Config.FLASK_ENV != "production"
    app.run(host="0.0.0.0", port=Config.PORT, debug=debug)
