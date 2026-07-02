import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def parse_nginx_logs():
    log_path = "/var/log/nginx/access.log"
    worker_1_name = os.getenv("WORKER_1_NAME", "Server 1")
    worker_2_name = os.getenv("WORKER_2_NAME", "Server 2")
    server_one_ip = os.getenv("WORKER_1_IP", "172.26.3.174")
    server_two_ip = os.getenv("WORKER_2_IP", "172.26.10.95")
    
    stats = {
        "today": {"total": 0, "server_one": 0, "server_two": 0},
        "this_week": {"total": 0, "server_one": 0, "server_two": 0},
        "meta": {
            "server_one_label": f"{worker_1_name} ({server_one_ip})",
            "server_two_label": f"{worker_2_name} ({server_two_ip})"
        }
    }
    
    if not os.path.exists(log_path):
        return stats
        
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = today_start - timedelta(days=today_start.weekday())
    
    try:
        with open(log_path, "r") as f:
            for line in f:
                try:
                    time_str = line.split("[")[1].split("]")[0] 
                    log_date_str = time_str.split()[0]
                    log_time = datetime.strptime(log_date_str, "%d/%b/%Y:%H:%M:%S")
                    
                    if log_time >= week_start:
                        stats["this_week"]["total"] += 1
                        if server_one_ip in line:
                            stats["this_week"]["server_one"] += 1
                        if server_two_ip in line:
                            stats["this_week"]["server_two"] += 1
                            
                    if log_time >= today_start:
                        stats["today"]["total"] += 1
                        if server_one_ip in line:
                            stats["today"]["server_one"] += 1
                        if server_two_ip in line:
                            stats["today"]["server_two"] += 1
                except Exception:
                    continue
    except Exception as e:
        print(f"Log parser xatosi: {e}")
        
    return stats
