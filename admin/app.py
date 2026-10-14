import os
import hmac
import json
import threading
from flask import Flask, Response, jsonify, render_template, request
from flask_socketio import SocketIO
import redis
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)

# The panel is not for the public: it is reached over an SSH tunnel or behind
# the host's nginx, and is protected by HTTP Basic auth either way.
ADMIN_USER = os.getenv('ADMIN_USER', '')
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

# Browsers send cached Basic credentials on a cross-site WebSocket handshake,
# so an open origin list would let any web page the operator visits read the
# live feed. Same-origin only, unless origins are listed explicitly.
ALLOWED_ORIGINS = [o.strip() for o in os.getenv('ADMIN_ALLOWED_ORIGINS', '').split(',') if o.strip()]
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins=ALLOWED_ORIGINS or None)

# .env orqali Redis ulanishi (izolyatsiya qilingan)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', ''),
    decode_responses=True
)

def _authorized(req) -> bool:
    """Constant-time check of the Basic credentials; false if none are configured."""
    if not ADMIN_USER or not ADMIN_PASSWORD:
        return False
    auth = req.authorization
    if auth is None or auth.type != 'basic':
        return False
    # Both comparisons always run, so timing does not reveal which half was right.
    user_ok = hmac.compare_digest((auth.username or '').encode(), ADMIN_USER.encode())
    pass_ok = hmac.compare_digest((auth.password or '').encode(), ADMIN_PASSWORD.encode())
    return user_ok and pass_ok


@app.before_request
def require_admin_auth():
    if not ADMIN_USER or not ADMIN_PASSWORD:
        # Fail closed: a panel nobody configured a password for stays shut.
        return Response('Admin panel is not configured', status=503)
    if not _authorized(request):
        return Response('Authentication required', status=401,
                        headers={'WWW-Authenticate': 'Basic realm="Kochatim admin", charset="UTF-8"'})


@app.after_request
def security_headers(resp):
    resp.headers['X-Content-Type-Options'] = 'nosniff'
    resp.headers['X-Frame-Options'] = 'DENY'
    resp.headers['Referrer-Policy'] = 'no-referrer'
    resp.headers['Cache-Control'] = 'no-store'
    # Exactly what templates/index.html loads: its own files, Chart.js from
    # jsDelivr and socket.io from cdnjs. No inline scripts.
    resp.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
        "style-src 'self' 'unsafe-inline'; "
        "connect-src 'self' ws: wss:; "
        "img-src 'self' data:; "
        "frame-ancestors 'none'; base-uri 'none'; form-action 'none'"
    )
    return resp


def handle_connect(auth=None):
    """Socket.IO traffic never passes through before_request, so check here."""
    if not _authorized(request):
        return False  # refuse the connection


socketio.on('connect')(handle_connect)


def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe(['server_metrics', 'live_requests'])
    for message in pubsub.listen():
        if message['type'] == 'message':
            channel = message['channel']
            try:
                data = json.loads(message['data'])
                if channel == 'server_metrics':
                    socketio.emit('metrics', data)
                elif channel == 'live_requests':
                    socketio.emit('live_request', data)
            except Exception as e:
                print("Error parsing pubsub message:", e)

listener_thread = threading.Thread(target=redis_listener, daemon=True)
listener_thread.start()

@app.route('/')
def index():
    return render_template('index.html')

def request_counts():
    today = datetime.utcnow().date()
    week_start = today - timedelta(days=today.weekday())
    stats = {"today": {"total": 0}, "this_week": {"total": 0}}
    try:
        days = [week_start + timedelta(days=i) for i in range((today - week_start).days + 1)]
        counts = redis_client.mget([f"req_count:{d}" for d in days])
        stats["this_week"]["total"] = sum(int(c or 0) for c in counts)
        stats["today"]["total"] = int(counts[-1] or 0)
    except Exception as e:
        print(f"Redis ulanish xatosi: {e}")
    return stats


@app.route('/api/stats')
def get_stats():
    # 1. Kunlik so'rovlar soni (backend Redis'ga yozadi)
    log_stats = request_counts()
    
    # 2. Redis'dan Endpoint Popularity (faqat kesh orqali, tashqi tarmoqsiz)
    try:
        endpoints_raw = redis_client.zrevrangebyscore("endpoint_stats", "+inf", "-inf", withscores=True, start=0, num=10)
        endpoints = [{"path": e[0], "count": int(e[1])} for e in endpoints_raw]
    except Exception as e:
        print(f"Redis ulanish xatosi: {e}")
        endpoints = []
        
    return jsonify({
        "logs": log_stats,
        "endpoints": endpoints
    })

if __name__ == '__main__':
    port = int(os.getenv('PORT', 9000))
    host = os.getenv('HOST', '0.0.0.0')
    # Debug mode only on request: the Werkzeug debugger executes code for anyone who can reach it.
    socketio.run(app, host=host, port=port, debug=os.getenv('FLASK_DEBUG') == '1')
