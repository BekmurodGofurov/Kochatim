# Ko'chatim - Telegram Bot

This is the Aiogram-based Telegram Bot for the Ko'chatim system. It allows users to register, interact with the system via chat, and syncs user data with the Backend.

## Role & Responsibilities

- **User Registration**: Captures Telegram user data (ID, name, username, phone number).
- **Profile Sync**: Fetches the user's Telegram profile picture and sends it to the Backend.
- **Interface**: Provides a chat interface for quick interactions (e.g., viewing balance, basic commands).
- **Data Relay**: Acts as a client to the Backend API to store and retrieve data.

## Tech Stack

- **Python 3.11+**
- **Aiogram**: Asynchronous framework for Telegram Bot API.
- **Aiohttp**: Asynchronous HTTP client for communicating with the Backend.

## Setup

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Ensure `aiogram`, `aiohttp`, `python-dotenv` are installed)*

2. **Environment variables**:
   Create a `.env` file in the `bot/` directory:
   ```env
   BOT_TOKEN=your_telegram_bot_token
   API_URL=http://localhost:8000  # URL of the Backend
   API_KEY=your_secret_api_key     # Must match Backend's API_KEY
   ADMINS=12345678,87654321
   ```

## Running the Bot

```bash
python app.py
```

## Architecture

- **`app.py`**: Entry point, starts the polling loop.
- **`handlers/`**: Contains message handlers (e.g., `/start`, contact sharing).
- **`api_client.py`**: Handles all HTTP requests to the Backend API.
- **`loader.py`**: Initializes the Bot and Dispatcher instances.

## Connection to Backend

The Bot **does not** connect to the database directly. Instead, it sends HTTP requests to the Backend (defined in `API_URL`). This ensures a unified logic and security layer managed by the Backend.
