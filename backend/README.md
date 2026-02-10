# Ko'chatim - Backend

This is the Flask-based backend API for the Ko'chatim greenhouse management system. It serves as the bridge between the database, the Telegram bot, and the frontend client.

## Role & Responsibilities

- **API Server**: Provides RESTful endpoints for the Frontend (Client).
- **Database Management**: Handles all interactions with the PostgreSQL database (via `psycopg2`).
- **Bot Integration**: Processes data sent from the Telegram Bot (e.g., user registration, photo syncing).
- **Authentication**: Manages user sessions and secures API endpoints.

## Tech Stack

- **Python 3.11+**
- **Flask**: Lightweight WSGI web application framework.
- **Psycopg2**: PostgreSQL adapter for Python.
- **Threading**: Uses `ThreadPoolExecutor` for concurrent query processing.
- **Gunicorn**: WSGI HTTP Server for production deployment.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Environment variables**:
   Create a `.env` file in the `backend/` directory with the following keys:
   ```env
   DATABASE_URL=postgresql://user:password@host/dbname
   API_KEY=your_secret_api_key
   BOT_TOKEN=your_telegram_bot_token
   FLASK_ENV=development
   ```

3. **Database Initialization**:
   The database schema is automatically checked and initialized on startup via `db_init.py`.

## Running the Server

### Development
```bash
python app.py
```
Runs on `http://localhost:8000` by default.

### Production (Gunicorn)
```bash
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

## Key Modules

- **`app.py`**: Entry point, initializes Flask app and blueprints.
- **`api/`**: Contains REST endpoints (e.g., `users.py`, `dashboard.py`, `images.py`).
- **`auth/`**: Handles authentication logic.
- **`db.py`**: Database connection pool and query execution utilities.
