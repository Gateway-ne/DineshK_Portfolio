#!/usr/bin/env python3
"""
bot.py - Telegram Bot for Dinesh K's Portfolio & Resume Automation

Allows you to update portfolio data, upload data.json, check live status,
and trigger syncs directly from Telegram on your phone.
"""

import base64
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent

# Load .env if present
env_file = BASE_DIR / ".env"
if env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_ALLOWED_USER_ID = os.environ.get("TELEGRAM_ALLOWED_USER_ID", "").strip()
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "").strip()
GITHUB_REPO = os.environ.get("GITHUB_REPO", "Gateway-ne/DineshK_Portfolio").strip()

DATA_PATH = BASE_DIR / "data.json"

def calculate_experience(start_date_str):
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d")
        now = datetime.now()
        months = (now.year - start.year) * 12 + (now.month - start.month)
        if now.day < start.day:
            months -= 1
        months = max(0, months)
        years = months // 12
        rem_months = months % 12
        return f"{years}.{rem_months} Years"
    except Exception:
        return "N/A"

def load_data():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def save_and_sync(data):
    # 1. Save locally
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    
    # 2. Run sync.py
    import sync
    sync.sync()

    # 3. If GITHUB_TOKEN is available, commit to GitHub directly
    if GITHUB_TOKEN:
        push_to_github(data)

def push_to_github(data):
    """Pushes data.json to GitHub using REST API so GitHub Actions triggers auto-sync."""
    try:
        url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/data.json"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json"
        }
        # Get existing file SHA
        r = requests.get(url, headers=headers, timeout=10)
        sha = r.json().get("sha") if r.status_code == 200 else None

        content_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
        payload = {
            "message": "Update data.json via Telegram Bot [skip ci]",
            "content": base64.b64encode(content_bytes).decode("utf-8")
        }
        if sha:
            payload["sha"] = sha

        put_res = requests.put(url, headers=headers, json=payload, timeout=15)
        if put_res.status_code in (200, 201):
            print("[BOT] Successfully committed data.json to GitHub repository!")
        else:
            print(f"[BOT] GitHub API warning ({put_res.status_code}): {put_res.text}")
    except Exception as e:
        print(f"[BOT] GitHub commit error: {e}")

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0

    def send_message(self, chat_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
        except Exception as e:
            print(f"[BOT] Send error: {e}")

    def send_document(self, chat_id, file_path, caption=""):
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"{self.api_url}/sendDocument",
                    data={"chat_id": chat_id, "caption": caption},
                    files={"document": f},
                    timeout=20
                )
        except Exception as e:
            print(f"[BOT] Send document error: {e}")

    def download_file(self, file_id, dest_path):
        try:
            res = requests.get(f"{self.api_url}/getFile", params={"file_id": file_id}, timeout=10)
            file_info = res.json()
            if not file_info.get("ok"):
                return False
            file_path = file_info["result"]["file_path"]
            download_url = f"https://api.telegram.org/file/bot{self.token}/{file_path}"
            r = requests.get(download_url, timeout=30)
            if r.status_code == 200:
                with open(dest_path, "wb") as f:
                    f.write(r.content)
                return True
        except Exception as e:
            print(f"[BOT] Download error: {e}")
        return False

    def handle_update(self, update):
        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        user_id = str(from_user.get("id", ""))
        first_name = from_user.get("first_name", "Friend")

        # Security check: if ALLOWED_USER_ID is set, only respond to that user
        if TELEGRAM_ALLOWED_USER_ID and user_id != TELEGRAM_ALLOWED_USER_ID:
            self.send_message(chat_id, "⛔ *Access Denied*: You are not authorized to manage this portfolio.")
            return

        # Check for uploaded document (data.json)
        if "document" in message:
            doc = message["document"]
            filename = doc.get("file_name", "")
            if filename.endswith(".json"):
                self.send_message(chat_id, "📥 *Downloading and validating JSON file...*")
                temp_path = BASE_DIR / "temp_data.json"
                if self.download_file(doc["file_id"], temp_path):
                    try:
                        with open(temp_path, "r", encoding="utf-8") as f:
                            new_data = json.load(f)
                        if "personal" not in new_data or "projects" not in new_data:
                            raise ValueError("Missing 'personal' or 'projects' root keys.")
                        
                        save_and_sync(new_data)
                        if temp_path.exists():
                            temp_path.unlink()
                        
                        self.send_message(
                            chat_id,
                            "✅ *Success!* Updated `data.json` received.\n\n"
                            "Both your *Portfolio* and *Resume* have been automatically synchronized and deployed!"
                        )
                        return
                    except Exception as e:
                        if temp_path.exists():
                            temp_path.unlink()
                        self.send_message(chat_id, f"❌ *Invalid JSON file*: {e}")
                        return
            else:
                self.send_message(chat_id, "⚠️ Please upload a `.json` file (specifically `data.json`).")
                return

        text = message.get("text", "").strip()
        if not text:
            return

        # Commands
        if text.startswith("/start"):
            welcome = (
                f"👋 *Hello {first_name}!*\n\n"
                f"Welcome to your *Dinesh K Portfolio Bot*.\n"
                f"Your Telegram User ID is: `{user_id}`\n\n"
                "📌 *Available Commands:*\n"
                "• `/status` — View current live portfolio details & experience\n"
                "• `/exp YYYY-MM-DD` — Update experience start date\n"
                "• `/title <Title>` — Update job title\n"
                "• `/get_data` — Receive current `data.json` file\n"
                "• `/help` — Show help message\n\n"
                "💡 *Pro-Tip:* You can also simply **drag & drop or send `data.json`** directly here in this chat to auto-update!"
            )
            self.send_message(chat_id, welcome)

        elif text.startswith("/help"):
            help_msg = (
                "🛠️ *Portfolio Telegram Bot Help:*\n\n"
                "1️⃣ *Check Details:* `/status`\n"
                "2️⃣ *Update Experience Date:* `/exp 2024-02-15`\n"
                "3️⃣ *Update Job Title:* `/title PLM / Teamcenter Developer`\n"
                "4️⃣ *Download data.json:* `/get_data`\n"
                "5️⃣ *Upload data.json:* Send `data.json` as a file attachment anytime!"
            )
            self.send_message(chat_id, help_msg)

        elif text.startswith("/status"):
            try:
                data = load_data()
                p = data.get("personal", {})
                start_date = p.get("experienceStartDate", "N/A")
                calc_exp = calculate_experience(start_date)
                proj_count = len(data.get("projects", []))
                pers_count = len(data.get("personalProjects", []))
                
                status_text = (
                    "📊 *Current Portfolio Status:*\n\n"
                    f"👤 *Name:* {p.get('name', 'Dinesh K')}\n"
                    f"💼 *Title:* {p.get('title', 'N/A')}\n"
                    f"📅 *Start Date:* `{start_date}` (*{calc_exp}*)\n"
                    f"📁 *Experience Projects:* {proj_count}\n"
                    f"🚀 *Personal Projects:* {pers_count}\n"
                    f"📍 *Location:* {p.get('location', 'Chennai, India')}\n\n"
                    f"🌐 *Portfolio:* {p.get('portfolioUrl', 'https://gateway-ne.github.io/DineshK_Portfolio')}\n"
                    f"📄 *Resume:* {p.get('portfolioUrl', 'https://gateway-ne.github.io/DineshK_Portfolio')}/resume.html"
                )
                self.send_message(chat_id, status_text)
            except Exception as e:
                self.send_message(chat_id, f"❌ Error loading status: {e}")

        elif text.startswith("/exp"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                self.send_message(chat_id, "⚠️ Usage: `/exp YYYY-MM-DD` (e.g. `/exp 2024-02-15`)")
                return
            new_date = parts[1].strip()
            try:
                # Validate date format
                datetime.strptime(new_date, "%Y-%m-%d")
                data = load_data()
                data["personal"]["experienceStartDate"] = new_date
                save_and_sync(data)
                calc_exp = calculate_experience(new_date)
                self.send_message(
                    chat_id,
                    f"✅ *Experience Start Date Updated!*\n\n"
                    f"📅 New Date: `{new_date}`\n"
                    f"⏱️ Total Experience: *{calc_exp}*\n"
                    f"⚡ Both Portfolio and Resume have been synchronized!"
                )
            except ValueError:
                self.send_message(chat_id, "❌ Invalid date format. Please use `YYYY-MM-DD` (e.g. `2024-02-15`).")
            except Exception as e:
                self.send_message(chat_id, f"❌ Error updating: {e}")

        elif text.startswith("/title"):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                self.send_message(chat_id, "⚠️ Usage: `/title <Your New Title>`")
                return
            new_title = parts[1].strip()
            try:
                data = load_data()
                data["personal"]["title"] = new_title
                save_and_sync(data)
                self.send_message(chat_id, f"✅ *Job Title Updated!*\n\n💼 New Title: *{new_title}*")
            except Exception as e:
                self.send_message(chat_id, f"❌ Error updating title: {e}")

        elif text.startswith("/get_data"):
            if DATA_PATH.exists():
                self.send_document(chat_id, DATA_PATH, caption="📄 Current data.json configuration")
            else:
                self.send_message(chat_id, "❌ data.json not found.")

        else:
            self.send_message(chat_id, "❓ Unknown command. Type `/help` for available commands or send `data.json` to update.")

    def run(self):
        print("[BOT] Starting Telegram Bot long polling...")
        print("[BOT] Press Ctrl+C to stop.")
        while True:
            try:
                params = {"timeout": 30, "offset": self.offset}
                res = requests.get(f"{self.api_url}/getUpdates", params=params, timeout=35)
                if res.status_code == 200:
                    data = res.json()
                    if data.get("ok"):
                        for update in data.get("result", []):
                            self.offset = update["update_id"] + 1
                            self.handle_update(update)
                elif res.status_code == 401:
                    print("[BOT] Error: Invalid TELEGRAM_BOT_TOKEN. Please check your .env file.")
                    time.sleep(10)
                else:
                    time.sleep(2)
            except requests.exceptions.RequestException:
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n[BOT] Stopping Telegram Bot...")
                break
            except Exception as e:
                print(f"[BOT] Unexpected polling error: {e}")
                time.sleep(2)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("=" * 60)
        print("ERROR: TELEGRAM_BOT_TOKEN is not set!")
        print("Please create or edit '.env' in this directory with:")
        print("TELEGRAM_BOT_TOKEN=your_token_from_botfather")
        print("=" * 60)
        sys.exit(1)

    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    bot.run()
