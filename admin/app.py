import os
import json
import threading
from flask import Flask, jsonify, render_template
from flask_socketio import SocketIO
import redis
from dotenv import load_dotenv
from log_parser import parse_nginx_logs

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

@app.route('/api/stats')
def get_stats():
    # 1. Nginx loglaridan statistika (faqat mahalliy fayl)
    log_stats = parse_nginx_logs()
    
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
