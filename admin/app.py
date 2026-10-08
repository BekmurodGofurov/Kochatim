import os
import json
import threading
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import redis
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()

app = Flask(__name__)
socketio = SocketIO(app, async_mode='gevent', cors_allowed_origins="*")

# .env orqali Redis ulanishi (izolyatsiya qilingan)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', ''),
    decode_responses=True
)

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
    socketio.run(app, host=host, port=port, debug=True)
