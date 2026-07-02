import os
from flask import Flask, jsonify, render_template
import redis
from dotenv import load_dotenv
from log_parser import parse_nginx_logs

# Load environment variables
load_dotenv()

app = Flask(__name__)

# .env orqali Redis ulanishi (izolyatsiya qilingan)
redis_client = redis.Redis(
    host=os.getenv('REDIS_HOST', 'localhost'),
    port=int(os.getenv('REDIS_PORT', 6379)),
    password=os.getenv('REDIS_PASSWORD', ''),
    decode_responses=True
)

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
    host = os.getenv('HOST', '127.0.0.1')
    app.run(host=host, port=port, debug=True)
