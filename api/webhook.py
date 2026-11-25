from http.server import BaseHTTPRequestHandler
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

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode("utf-8")
        
        try:
            update = json.loads(body)
            bot = get_bot()
            bot.handle_update(update)
        except Exception as e:
            print(f"[WEBHOOK ERROR] {e}")
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "status": "online",
            "bot": "Dinesh K Portfolio Bot (24/7 Cloud)",
            "message": "Send Telegram updates to POST /api/webhook"
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))
