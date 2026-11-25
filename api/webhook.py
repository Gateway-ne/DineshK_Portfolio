from http.server import BaseHTTPRequestHandler
import json
import os
import sys

# Ensure root directory is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        bot_tok = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        gh_tok = os.environ.get("GITHUB_TOKEN", "").strip()
        data = {
            "status": "online",
            "bot": "Dinesh K Portfolio Bot (24/7 Cloud)",
            "webhook_endpoint": "/api/webhook",
            "has_telegram_token": bool(bot_tok),
            "has_github_token": bool(gh_tok),
            "telegram_token_preview": (bot_tok[:8] + "...") if bot_tok else "MISSING",
            "github_token_preview": (gh_tok[:8] + "...") if gh_tok else "MISSING"
        }
        self.wfile.write(json.dumps(data, indent=2).encode("utf-8"))

    def do_POST(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length).decode("utf-8")
            if body:
                update = json.loads(body)
                from bot import TelegramBot, TELEGRAM_BOT_TOKEN
                token = os.environ.get("TELEGRAM_BOT_TOKEN", TELEGRAM_BOT_TOKEN).strip()
                bot = TelegramBot(token)
                bot.handle_update(update)
        except Exception as e:
            print(f"[WEBHOOK ERROR] {e}")
            
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode("utf-8"))
