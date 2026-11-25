import io
import json
import os
import sys

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from bot import TelegramBot, TELEGRAM_BOT_TOKEN

_bot_instance = None

def get_bot():
    global _bot_instance
    if _bot_instance is None:
        token = os.environ.get("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN).strip()
        _bot_instance = TelegramBot(token)
    return _bot_instance

def app(environ, start_response):
    method = environ.get("REQUEST_METHOD", "GET").upper()
    
    if method == "POST":
        try:
            content_length = int(environ.get("CONTENT_LENGTH", 0))
        except (ValueError, TypeError):
            content_length = 0
            
        body = ""
        if content_length > 0:
            body = environ["wsgi.input"].read(content_length).decode("utf-8")
            
        try:
            if body:
                update = json.loads(body)
                bot = get_bot()
                bot.handle_update(update)
        except Exception as e:
            print(f"[WEBHOOK ERROR] {e}")
            
        status = "200 OK"
        headers = [("Content-Type", "application/json")]
        start_response(status, headers)
        return [json.dumps({"ok": True}).encode("utf-8")]
        
    else:
        status = "200 OK"
        headers = [("Content-Type", "application/json")]
        start_response(status, headers)
        response = {
            "status": "online",
            "bot": "Dinesh K Portfolio Bot (24/7 Cloud)",
            "service": "Vercel WSGI Serverless",
            "webhook_endpoint": "/api/webhook"
        }
        return [json.dumps(response, indent=2).encode("utf-8")]

# Export both app and handler for all WSGI/ASGI/Vercel runners
handler = app
