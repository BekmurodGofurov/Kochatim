import threading
from flask import Flask
from aiogram import executor
from loader import dp
import middlewares, filters, handlers
from utils.notify_admins import on_startup_notify
from utils.set_bot_commands import set_default_commands

# Render uchun kichik Flask server (portni band qilish uchun)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "Bot is running!", 200

async def on_startup(dispatcher):
    await set_default_commands(dispatcher)
    print("Bot started (Backend API mode)")
    await on_startup_notify(dispatcher)

def run_bot():
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)

# Botni alohida thread-da ishga tushirish
threading.Thread(target=run_bot, daemon=True).start()

if __name__ == "__main__":
    # Localda ishlatsangiz
    import os
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port)