# Kochatim Monitoring & Analytics Dashboard

This microservice (Admin Dashboard) is an independent system designed for visual monitoring of the **Kochatim** project, including Nginx server load and Endpoint Popularity.

## Architecture & How It Works

This project does not rely on classic "Backend-to-Backend" HTTP requests. Instead, it operates entirely using **local data sources**:

1. **Server Load Analytics:** 
   The microservice reads the local Nginx access log file (`/var/log/nginx/access.log`) on the server where it resides. By parsing these logs, it calculates the number of incoming requests routed to specific worker servers (e.g., Server 1 or Server 2) and groups them by "Today" and "This Week".

2. **Endpoint Popularity:** 
   Whenever users (or bots) hit the main backend API, the backend increments a counter for each route in a central **Redis cache** in the background. The Admin Dashboard connects directly to this Redis cache via TCP to fetch the Top 10 most used APIs instantly, without ever querying the main PostgreSQL database.

3. **UI/UX Design:** 
   The frontend uses `Chart.js` for lightweight graphs and fetches data asynchronously via AJAX from the `/api/stats` endpoint. It also includes a modern Light/Dark mode toggle for user convenience.

### Architecture Diagram

```mermaid
flowchart TD
    Client((Client / Admin)) -->|HTTPS request| Nginx[Nginx Load Balancer]
    
    subgraph Load Balancer Server
        Nginx -->|Reverse Proxy :9000| AdminApp[Admin Microservice\nFlask port: 9000]
        AdminApp -.->|1. Reads File| AccessLog[/var/log/nginx/access.log]
    end
    
    subgraph Internal Network
        AdminApp -->|2. TCP connection| Redis[(Central Redis Cache)]
        Worker1[Backend Worker 1] -->|Logs API usage| Redis
        Worker2[Backend Worker 2] -->|Logs API usage| Redis
    end
```

---

## Deployment Location

Since this application's primary function is to read Nginx logs directly, it **MUST be deployed on the main Load Balancer (Nginx) server**. Worker servers do not hold the centralized access logs, so the dashboard will not function correctly if deployed there.

---

## Security & Isolation Structure

The system operates under strict security constraints for the production environment:

- **Absolute `.env` Isolation:** 
  No IP addresses, server names, passwords, or network ports are hardcoded in the codebase. All configurations are strictly loaded from the `.env` file.
  
- **No Outbound HTTP Requests:** 
  The dashboard does NOT send any HTTP requests to the main API (e.g., `api.kochatim.uz`) to gather data. It relies solely on local physical log files and a closed-network Redis connection (TCP). This guarantees that errors or DDoS attacks on the admin panel will never freeze or crash the main backend.

- **Process Isolation:**
  This Flask application runs in a completely separate memory space and on a dedicated port (`9000`). If it crashes or stops, the main backend and the bot will continue to function normally without any interruption.

- **Why is the Port Bound to `127.0.0.1`? (Security Notice):**
  Initially, running a server on `0.0.0.0` exposes the port to the public internet, which is a security risk. To ensure maximum security, the application and Gunicorn are now bound strictly to `127.0.0.1:9000` (localhost). This means the microservice is completely hidden from the outside world. Only the local Nginx reverse proxy on the exact same server can access port 9000 and serve it securely over your domain (e.g., `admin.kochatim.uz`).

---

## Installation & Setup

1. Install Dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Configure `.env` (Create a file named `.env` in the `admin/` folder and adapt it to your actual server details):
   ```env
   # Redis Settings
   REDIS_HOST=Hidden_Redis_IP
   REDIS_PORT=6379
   REDIS_PASSWORD=hidden_password

   # Nginx Log Parsing (Worker IP Addresses)
   WORKER_1_IP=10.0.x.x
   WORKER_1_NAME=Server 1

   WORKER_2_IP=10.0.x.x
   WORKER_2_NAME=Server 2

   # Microservice execution port and host
   HOST=127.0.0.1
   PORT=9000
   ```

3. Run in the background using Gunicorn:
   ```bash
   gunicorn -w 1 -b 127.0.0.1:9000 app:app --daemon
   ```

**Nginx Configuration:** 
You should create a new server block in Nginx for `admin.kochatim.uz` and set up a `proxy_pass` to `http://127.0.0.1:9000`. This allows users to access the dashboard securely via standard HTTP/HTTPS while keeping port 9000 blocked from direct external access.
