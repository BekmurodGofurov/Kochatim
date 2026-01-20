# backend/app.py
from dotenv import load_dotenv
load_dotenv()

import os
from flask import Flask
from config import Config
from utils.errors import ok, fail
from extensions import init_pool
from db_init import init_db

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

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    debug = Config.FLASK_ENV != "production"
    app.run(host="0.0.0.0", port=port, debug=debug)