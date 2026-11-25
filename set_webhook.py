#!/usr/bin/env python3
"""
set_webhook.py - Helper to set, check, or delete Telegram Webhook for Dinesh K's Portfolio Bot
Usage:
  python set_webhook.py https://your-project.vercel.app/api/webhook
  python set_webhook.py --delete   (to switch back to local polling)
  python set_webhook.py --info     (to check current webhook status)
"""
import sys
import os
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent
env_file = BASE_DIR / ".env"
token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

if not token and env_file.exists():
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("TELEGRAM_BOT_TOKEN="):
                token = line.split("=", 1)[1].strip().strip('"').strip("'")

if not token:
    print("ERROR: TELEGRAM_BOT_TOKEN not found in .env or environment.")
    sys.exit(1)

api_url = f"https://api.telegram.org/bot{token}"

if len(sys.argv) < 2 or sys.argv[1] == "--info":
    r = requests.get(f"{api_url}/getWebhookInfo").json()
    print("Current Webhook Info:")
    print(r)
elif sys.argv[1] == "--delete":
    r = requests.post(f"{api_url}/deleteWebhook").json()
    print("Delete Webhook Result:", r)
else:
    webhook_url = sys.argv[1].strip()
    r = requests.post(f"{api_url}/setWebhook", json={"url": webhook_url}).json()
    print(f"Setting webhook to: {webhook_url}")
    print("Result:", r)
