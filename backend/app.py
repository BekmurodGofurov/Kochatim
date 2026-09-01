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

import time
import threading
import json
import psutil
from datetime import datetime
from utils.telegram_notify import send_message

def system_monitor():
    from utils.cache import redis_client
    server_identity = os.getenv('SERVER_NAME', 'unknown_server')
    last_alert_time = 0
    while True:
        try:
            cpu = psutil.cpu_percent(interval=None)
            ram = psutil.virtual_memory().percent
            
            metrics = {
                "server": server_identity,
                "cpu": cpu,
                "ram": ram,
                "time": datetime.utcnow().isoformat()
            }
            redis_client.publish("server_metrics", json.dumps(metrics))
            
            if cpu > 90 or ram > 90:
                current_time = time.time()
                if current_time - last_alert_time > 300:
                    msg = f"⚠️ *DIQQAT!*\nServer: `{server_identity}`\nCPU: `{cpu}%`\nRAM: `{ram}%`\nHolat kritik darajada!"
                    if Config.ADMINS:
                        for admin_id in Config.ADMINS.split(","):
                            if admin_id.strip():
                                send_message(int(admin_id.strip()), msg)
                    last_alert_time = current_time
                    
        except Exception as e:
            print(f"Monitor error: {e}")
        time.sleep(2)

monitor_thread = threading.Thread(target=system_monitor, daemon=True)
monitor_thread.start()


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

@app.after_request
def _record_endpoint_stats(resp):
    try:
        from utils.cache import redis_client
        if request.path.startswith("/api/") or request.path.startswith("/auth/"):
            redis_client.zincrby("endpoint_stats", 1, request.path)
            server_identity = os.getenv('SERVER_NAME', 'unknown_server')
            req_data = {
                "server": server_identity,
                "path": request.path,
                "method": request.method,
                "status": resp.status_code,
                "time": datetime.utcnow().strftime('%H:%M:%S')
            }
            redis_client.publish("live_requests", json.dumps(req_data))
    except Exception:
        pass
    return resp

if __name__ == "__main__":
    debug = Config.FLASK_ENV != "production"
    app.run(host="0.0.0.0", port=Config.PORT, debug=debug)
