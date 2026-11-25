#!/usr/bin/env python3
"""
bot.py - Button-Driven Telegram Admin Bot for Dinesh K's Portfolio & Resume

Batch Deployment Workflow:
- Make as many edits as you want (Profile, Skills, Projects, Personal Projects).
- All edits are saved and compiled locally immediately.
- Nothing is deployed to GitHub until you tap "🚀 Deploy All Changes"!
- When you tap "🚀 Deploy All Changes", all edits are pushed together in one go,
  and you get a notification when live deployment finishes.
"""

import base64
import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
import requests

BASE_DIR = Path(__file__).resolve().parent

# Load .env
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
PENDING_CHANGES_FILE = BASE_DIR / "pending_changes.json"

GIT_CANDIDATES = [
    r"C:\Users\MSI\AppData\Local\GitHubDesktop\app-3.6.5\resources\app\git\cmd\git.exe",
    r"C:\Program Files\Git\cmd\git.exe",
    "git"
]

def get_git_executable():
    for g in GIT_CANDIDATES:
        if os.path.exists(g):
            return g
    return "git"

user_states = {}

DASHBOARD_REPLY_KEYBOARD = {
    "keyboard": [
        [{"text": "👤 Profile & Bio"}, {"text": "🛠️ Skills Manager"}],
        [{"text": "💼 Experience Projects"}, {"text": "🚀 Personal Projects"}],
        [{"text": "🚀 Deploy All Changes"}, {"text": "📄 Download data.json"}],
        [{"text": "📊 Live Status"}, {"text": "📋 Main Dashboard"}]
    ],
    "resize_keyboard": True,
    "is_persistent": True
}

# =============================================================================
# Pending Changes Tracker
# =============================================================================

def get_pending_changes():
    if PENDING_CHANGES_FILE.exists():
        try:
            with open(PENDING_CHANGES_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if GITHUB_TOKEN:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/pending_changes.json"
            headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                content = base64.b64decode(r.json()["content"]).decode("utf-8")
                return json.loads(content)
        except Exception:
            pass
    return []

def add_pending_change(desc):
    changes = get_pending_changes()
    changes.append({"desc": desc, "time": datetime.now().strftime("%H:%M:%S")})
    try:
        with open(PENDING_CHANGES_FILE, "w", encoding="utf-8") as f:
            json.dump(changes, f, indent=2)
    except Exception:
        pass

def clear_pending_changes():
    if PENDING_CHANGES_FILE.exists():
        try:
            PENDING_CHANGES_FILE.unlink()
        except Exception:
            pass
    if GITHUB_TOKEN:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/pending_changes.json"
            headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                sha = r.json().get("sha")
                payload = {
                    "message": "Clear pending changes [skip ci]",
                    "content": base64.b64encode(b"[]").decode("utf-8"),
                    "sha": sha
                }
                requests.put(url, headers=headers, json=payload, timeout=10)
        except Exception:
            pass

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
    if DATA_PATH.exists():
        try:
            with open(DATA_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    if GITHUB_TOKEN:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/data.json"
            headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                content = base64.b64decode(r.json()["content"]).decode("utf-8")
                return json.loads(content)
        except Exception as e:
            print(f"[BOT] GitHub API load note: {e}")
    return {}

def save_data_locally(data, description):
    """Saves data.json, recompiles HTML, and logs as a pending change without pushing to GitHub."""
    # 1. Save data.json locally if filesystem is writable
    try:
        with open(DATA_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        import sync
        sync.sync()
    except Exception as e:
        print(f"[BOT] Local compile note: {e}")

    # 2. Track pending change
    add_pending_change(description)

    # 3. If in cloud environment without git, sync data.json to GitHub with [skip ci]
    git_cmd = get_git_executable()
    has_git = False
    try:
        res = subprocess.run([git_cmd, "--version"], capture_output=True, text=True)
        has_git = (res.returncode == 0)
    except Exception:
        has_git = False

    if not has_git and GITHUB_TOKEN:
        try:
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/data.json"
            headers = {"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
            r = requests.get(url, headers=headers, timeout=10)
            sha = r.json().get("sha") if r.status_code == 200 else None
            content_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            payload = {
                "message": f"Update data.json: {description} [skip ci]",
                "content": base64.b64encode(content_bytes).decode("utf-8")
            }
            if sha:
                payload["sha"] = sha
            requests.put(url, headers=headers, json=payload, timeout=15)
        except Exception as e:
            print(f"[BOT] GitHub cloud commit note: {e}")

def push_pending_to_github(commit_msg):
    """Commits and pushes all pending changes to GitHub."""
    git_cmd = get_git_executable()
    pushed = False
    try:
        subprocess.run([git_cmd, "add", "data.json", "index.html", "resume.html"], cwd=str(BASE_DIR), capture_output=True, text=True)
        subprocess.run([git_cmd, "commit", "-m", commit_msg], cwd=str(BASE_DIR), capture_output=True, text=True)
        
        if GITHUB_TOKEN:
            remote_url = f"https://{GITHUB_TOKEN}@github.com/{GITHUB_REPO}.git"
            push_res = subprocess.run([git_cmd, "push", remote_url, "main"], cwd=str(BASE_DIR), capture_output=True, text=True, timeout=25)
            if push_res.returncode == 0:
                print(f"[BOT] Pushed successfully to GitHub: {commit_msg}")
                pushed = True
            else:
                print(f"[BOT] Git push note: {push_res.stderr}")
    except Exception as e:
        print(f"[BOT] Git commit/push note: {e}")

    # Fallback to GitHub REST API if git push didn't execute (e.g. Vercel serverless)
    if GITHUB_TOKEN and not pushed:
        try:
            data = load_data()
            url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/data.json"
            headers = {
                "Authorization": f"Bearer {GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json"
            }
            r = requests.get(url, headers=headers, timeout=10)
            sha = r.json().get("sha") if r.status_code == 200 else None

            content_bytes = json.dumps(data, indent=2, ensure_ascii=False).encode("utf-8")
            # Do NOT use [skip ci] here so GitHub Actions triggers!
            payload = {
                "message": commit_msg,
                "content": base64.b64encode(content_bytes).decode("utf-8")
            }
            if sha:
                payload["sha"] = sha

            requests.put(url, headers=headers, json=payload, timeout=15)
            pushed = True

            # Trigger workflow dispatch to ensure build runs immediately
            dispatch_url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/workflows/sync.yml/dispatches"
            requests.post(dispatch_url, headers=headers, json={"ref": "main"}, timeout=10)
        except Exception as e:
            print(f"[BOT] GitHub API fallback note: {e}")

    return pushed

def monitor_github_deployment(bot, chat_id, summary_text):
    """Monitors GitHub Actions in the background and sends a message when deployment finishes."""
    if not GITHUB_TOKEN:
        return

    time.sleep(6)
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/repos/{GITHUB_REPO}/actions/runs"

    poll_start = time.time()
    max_wait_seconds = 180

    while time.time() - poll_start < max_wait_seconds:
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                runs = r.json().get("workflow_runs", [])
                if runs:
                    latest = runs[0]
                    status = latest.get("status")
                    conclusion = latest.get("conclusion")

                    if status == "completed":
                        if conclusion == "success":
                            msg = (
                                f"🎉 *Deployment Succeeded!*\n\n"
                                f"All your updates are now live on GitHub Pages:\n"
                                f"• {summary_text}\n\n"
                                f"🌐 [Open Live Portfolio](https://gateway-ne.github.io/DineshK_Portfolio/)\n"
                                f"📄 [Open Live Resume](https://gateway-ne.github.io/DineshK_Portfolio/resume.html)"
                            )
                            bot.send_message(chat_id, msg)
                            return
                        else:
                            bot.send_message(chat_id, f"⚠️ *Deployment completed with status:* `{conclusion}`")
                            return
        except Exception as e:
            print(f"[BOT] Monitor error: {e}")

        time.sleep(7)

def save_user_id_to_env(user_id):
    lines = []
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith("TELEGRAM_ALLOWED_USER_ID="):
            new_lines.append(f"TELEGRAM_ALLOWED_USER_ID={user_id}\n")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"TELEGRAM_ALLOWED_USER_ID={user_id}\n")
    
    with open(env_file, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

class TelegramBot:
    def __init__(self, token):
        self.token = token
        self.api_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0

    def trigger_local_update(self, chat_id, data, desc):
        """Saves changes locally without deploying, prompts user to deploy when ready."""
        save_data_locally(data, desc)
        pending = get_pending_changes()
        
        text = (
            f"✅ *Saved Locally!*\n\n"
            f"• *Change:* {desc}\n"
            f"• *Pending changes to deploy:* `{len(pending)}`\n\n"
            f"💡 *You can keep making more edits!* When you are ready to publish all changes to your live website, tap **🚀 Deploy All Changes** below."
        )
        self.send_message(chat_id, text)

    def deploy_pending_changes(self, chat_id, force=False):
        """Pushes all pending edits to GitHub Cloud in one single deployment."""
        pending = get_pending_changes()
        
        if not pending and not force:
            self.send_message(
                chat_id,
                "✨ *No pending changes to deploy!*\n\n"
                "Your live website is already up to date with your latest edits.\n\n"
                "To publish new edits, make changes to Profile, Skills, or Projects first.",
                {"inline_keyboard": [[{"text": "⚡ Force Re-Deploy Anyway", "callback_data": "action_force_deploy"}]]}
            )
            return

        change_list_str = "\n".join([f"• {c['desc']}" for c in pending]) if pending else "• Manual full sync"
        commit_msg = f"Deploy {len(pending)} updates via Telegram Bot" if pending else "Manual sync via Telegram Bot"

        # Push to GitHub
        push_pending_to_github(commit_msg)
        clear_pending_changes()

        # Immediate feedback
        self.send_message(
            chat_id,
            f"🚀 *Deploying to Live Website...*\n\n"
            f"*Changes included:*\n{change_list_str}\n\n"
            f"⏳ Pushed to GitHub! Building & deploying to live site (~45-60s)...\n"
            f"_You will receive a notification here as soon as deployment finishes._"
        )

        # Watcher
        threading.Thread(target=monitor_github_deployment, args=(self, chat_id, change_list_str), daemon=True).start()

    def send_message(self, chat_id, text, reply_markup=None):
        markup = reply_markup if reply_markup else DASHBOARD_REPLY_KEYBOARD
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "reply_markup": json.dumps(markup)
        }
        try:
            r = requests.post(f"{self.api_url}/sendMessage", json=payload, timeout=10)
            res = r.json()
            if not res.get("ok"):
                print(f"[BOT] Telegram API rejected sendMessage: {res}")
            return res
        except Exception as e:
            print(f"[BOT] Send error: {e}")
            return None

    def edit_message(self, chat_id, message_id, text, reply_markup=None):
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True
        }
        if reply_markup:
            payload["reply_markup"] = json.dumps(reply_markup)
        try:
            r = requests.post(f"{self.api_url}/editMessageText", json=payload, timeout=10)
            res = r.json()
            if not res.get("ok"):
                print(f"[BOT] Telegram API rejected editMessageText: {res}")
        except Exception as e:
            print(f"[BOT] Edit error: {e}")

    def answer_callback(self, callback_query_id, text=None):
        payload = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text
        try:
            requests.post(f"{self.api_url}/answerCallbackQuery", json=payload, timeout=10)
        except Exception as e:
            pass

    def send_document(self, chat_id, file_path, caption=""):
        try:
            with open(file_path, "rb") as f:
                requests.post(
                    f"{self.api_url}/sendDocument",
                    data={
                        "chat_id": chat_id,
                        "caption": caption,
                        "reply_markup": json.dumps(DASHBOARD_REPLY_KEYBOARD)
                    },
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

    # =========================================================================
    # Button Menus
    # =========================================================================

    def show_main_menu(self, chat_id, message_id=None):
        data = load_data()
        p = data.get("personal", {})
        exp_calc = calculate_experience(p.get("experienceStartDate", ""))
        pending = get_pending_changes()
        
        pending_str = f"⚠️ *Pending Changes:* `{len(pending)}` (Not yet deployed)" if pending else "✅ *Live Status:* Up to date"

        text = (
            f"⚡ *Dinesh K — Portfolio Admin Dashboard*\n\n"
            f"👤 *{p.get('name', 'Dinesh K')}* | {p.get('title', '')}\n"
            f"📅 *Experience:* *{exp_calc}*\n"
            f"📁 *Experience Projects:* {len(data.get('projects', []))} | *Personal Projects:* {len(data.get('personalProjects', []))}\n"
            f"{pending_str}\n\n"
            f"Tap any button below to manage your portfolio:"
        )

        deploy_btn_text = f"🚀 Deploy All Changes ({len(pending)})" if pending else "🚀 Deploy All Changes"

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "👤 Profile & Bio", "callback_data": "menu_profile"},
                    {"text": "🛠️ Skills Manager", "callback_data": "menu_skills"}
                ],
                [
                    {"text": "💼 Experience Projects", "callback_data": "menu_projects"},
                    {"text": "🚀 Personal Projects", "callback_data": "menu_personal"}
                ],
                [
                    {"text": deploy_btn_text, "callback_data": "action_deploy_now"}
                ],
                [
                    {"text": "📄 Download data.json", "callback_data": "action_get_data"}
                ]
            ]
        }

        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    # 1. Profile & Bio Menu
    def show_profile_menu(self, chat_id, message_id=None):
        data = load_data()
        p = data.get("personal", {})
        exp_calc = calculate_experience(p.get("experienceStartDate", ""))

        text = (
            f"👤 *Profile & Bio Details*\n\n"
            f"• *Name:* {p.get('name', '')}\n"
            f"• *Title:* {p.get('title', '')}\n"
            f"• *Experience:* *{exp_calc}*\n"
            f"• *Email:* {p.get('email', '')}\n"
            f"• *Phone:* {p.get('phone', '')}\n"
            f"• *LinkedIn:* {p.get('linkedin', '')}\n"
            f"• *Location:* {p.get('location', '')}\n"
            f"• *Client:* {p.get('client', '')}\n\n"
            f"Tap any field button below to edit:"
        )

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✏️ Experience", "callback_data": "edit_prof_exp"},
                    {"text": "✏️ Job Title", "callback_data": "edit_prof_title"}
                ],
                [
                    {"text": "✏️ Full Name", "callback_data": "edit_prof_name"},
                    {"text": "✏️ Phone Number", "callback_data": "edit_prof_phone"}
                ],
                [
                    {"text": "✏️ Email", "callback_data": "edit_prof_email"},
                    {"text": "✏️ LinkedIn URL", "callback_data": "edit_prof_linkedin"}
                ],
                [
                    {"text": "✏️ Location", "callback_data": "edit_prof_location"},
                    {"text": "✏️ Client Name", "callback_data": "edit_prof_client"}
                ],
                [
                    {"text": "⬅️ Back to Dashboard", "callback_data": "menu_main"}
                ]
            ]
        }

        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    # 2. Skills Menu
    def show_skills_menu(self, chat_id, message_id=None):
        data = load_data()
        skills = data.get("skills", {})

        cat_names = [
            ("coreTC", "Core Teamcenter"),
            ("integration", "Integration & Upgrade"),
            ("programming", "Programming & Database"),
            ("tools", "Tools & Platforms"),
            ("documentation", "Documentation & Guides")
        ]

        text = "🛠️ *Skills Manager*\n\nSelect a skill category button below:\n"
        buttons = []
        for key, title in cat_names:
            count = len(skills.get(key, []))
            buttons.append([{"text": f"📂 {title} ({count})", "callback_data": f"view_skills_{key}"}])

        buttons.append([{"text": "⬅️ Back to Dashboard", "callback_data": "menu_main"}])

        keyboard = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    def show_skills_category(self, chat_id, cat_key, message_id=None):
        data = load_data()
        skills = data.get("skills", {}).get(cat_key, [])
        cat_titles = {
            "coreTC": "Core Teamcenter",
            "integration": "Integration & Upgrade",
            "programming": "Programming & Database",
            "tools": "Tools & Platforms",
            "documentation": "Documentation & Guides"
        }
        title = cat_titles.get(cat_key, cat_key)

        text = (
            f"🛠️ *Skills in {title}* ({len(skills)} items)\n\n"
            f"• Tap `🔝` to jump directly to first (#1)\n"
            f"• Tap `⬆️` or `⬇️` to move up / down\n"
            f"• Tap `❌` to delete a skill\n"
            f"• Tap **`[ ✅ Done Rearranging ]`** when finished!\n\n"
        )
        if not skills:
            text += "_No skills added in this category yet._\n"
        else:
            for idx, s in enumerate(skills):
                text += f"`{idx + 1}.` {s.get('name', '')}\n"

        buttons = [
            [
                {"text": "✅ Done Rearranging", "callback_data": f"done_skills_{cat_key}"},
                {"text": "➕ Add Skill", "callback_data": f"add_skill_{cat_key}"}
            ]
        ]
        
        for idx, s in enumerate(skills):
            row = [
                {"text": f"{idx + 1}. {s.get('name')[:13]}", "callback_data": f"detail_skill_{cat_key}_{idx}"}
            ]
            if idx > 0:
                row.append({"text": "🔝", "callback_data": f"move_skill_{cat_key}_{idx}_top"})
                row.append({"text": "⬆️", "callback_data": f"move_skill_{cat_key}_{idx}_up"})
            else:
                row.append({"text": "·", "callback_data": "noop"})
                row.append({"text": "·", "callback_data": "noop"})

            if idx < len(skills) - 1:
                row.append({"text": "⬇️", "callback_data": f"move_skill_{cat_key}_{idx}_down"})
            else:
                row.append({"text": "·", "callback_data": "noop"})

            row.append({"text": "❌", "callback_data": f"del_skill_{cat_key}_{idx}"})
            buttons.append(row)

        buttons.append([{"text": "⬅️ Back to Skills Menu", "callback_data": "menu_skills"}])
        keyboard = {"inline_keyboard": buttons}

        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    def show_skill_detail(self, chat_id, cat_key, idx, message_id=None):
        data = load_data()
        skills = data.get("skills", {}).get(cat_key, [])
        if idx >= len(skills):
            self.show_skills_category(chat_id, cat_key, message_id)
            return

        s = skills[idx]
        cat_titles = {
            "coreTC": "Core Teamcenter",
            "integration": "Integration & Upgrade",
            "programming": "Programming & Database",
            "tools": "Tools & Platforms",
            "documentation": "Documentation & Guides"
        }
        title = cat_titles.get(cat_key, cat_key)

        text = (
            f"🛠️ *Skill: {s.get('name')}*\n\n"
            f"• *Category:* {title}\n"
            f"• *Current Order:* #{idx + 1} of {len(skills)}\n\n"
            f"Tap an option below to arrange or modify:"
        )

        buttons = [
            [
                {"text": "🔝 Jump to First (#1)", "callback_data": f"move_skill_{cat_key}_{idx}_top"},
                {"text": "🔚 Move to Bottom", "callback_data": f"move_skill_{cat_key}_{idx}_bottom"}
            ],
            [
                {"text": "⬆️ Move Up", "callback_data": f"move_skill_{cat_key}_{idx}_up"},
                {"text": "⬇️ Move Down", "callback_data": f"move_skill_{cat_key}_{idx}_down"}
            ],
            [
                {"text": "✏️ Rename Skill", "callback_data": f"rename_skill_{cat_key}_{idx}"},
                {"text": "❌ Delete Skill", "callback_data": f"del_skill_{cat_key}_{idx}"}
            ],
            [
                {"text": f"⬅️ Back to {title}", "callback_data": f"view_skills_{cat_key}"}
            ]
        ]

        keyboard = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    # 3. Experience Projects Menu
    def show_projects_menu(self, chat_id, message_id=None):
        data = load_data()
        projects = data.get("projects", [])

        text = f"💼 *Professional Projects* ({len(projects)} total)\n\nTap any project button below to view or edit:\n"
        buttons = []
        for idx, p in enumerate(projects):
            name = p.get("name", "Untitled")
            period = p.get("period", "")
            btn_text = f"📁 {idx + 1}. {name[:22]} ({period})"
            buttons.append([{"text": btn_text, "callback_data": f"view_proj_{idx}"}])

        buttons.append([{"text": "➕ Add New Project", "callback_data": "action_add_project"}])
        buttons.append([{"text": "⬅️ Back to Dashboard", "callback_data": "menu_main"}])

        keyboard = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    def show_project_detail(self, chat_id, idx, message_id=None):
        data = load_data()
        projects = data.get("projects", [])
        if idx >= len(projects):
            self.show_projects_menu(chat_id, message_id)
            return

        p = projects[idx]
        bullets = p.get("bullets", [])
        bullet_text = "\n".join([f"• {b}" for b in bullets[:4]])
        if len(bullets) > 4:
            bullet_text += f"\n_...and {len(bullets) - 4} more bullets._"

        text = (
            f"💼 *Project #{idx + 1}: {p.get('name', '')}*\n\n"
            f"• *Period:* {p.get('period', '')}\n"
            f"• *Role:* {p.get('role', '')} ({p.get('teamRole', 'Team Member')})\n"
            f"• *Tech Tags:* {', '.join(p.get('techTags', []))}\n"
            f"• *Resume Page:* {p.get('page', 1)}\n\n"
            f"*Key Achievements / Bullets:*\n{bullet_text}\n"
        )

        cur_page = p.get("page", 1)
        next_page = 2 if cur_page == 1 else 1

        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✏️ Name", "callback_data": f"edit_proj_name_{idx}"},
                    {"text": "✏️ Period", "callback_data": f"edit_proj_period_{idx}"}
                ],
                [
                    {"text": "✏️ Role", "callback_data": f"edit_proj_role_{idx}"},
                    {"text": "✏️ Tech Tags", "callback_data": f"edit_proj_tech_{idx}"}
                ],
                [
                    {"text": f"📄 Switch to Page {next_page}", "callback_data": f"toggle_proj_page_{idx}_{next_page}"},
                    {"text": "📝 Replace Bullets", "callback_data": f"edit_proj_bullets_{idx}"}
                ],
                [
                    {"text": "🗑️ Delete Project", "callback_data": f"del_proj_confirm_{idx}"}
                ],
                [
                    {"text": "⬅️ Back to Projects", "callback_data": "menu_projects"}
                ]
            ]
        }

        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    # 4. Personal Projects Menu
    def show_personal_menu(self, chat_id, message_id=None):
        data = load_data()
        personal = data.get("personalProjects", [])

        text = f"🚀 *Personal Projects* ({len(personal)} total)\n\nTap a project button below to view or edit:\n"
        buttons = []
        for idx, p in enumerate(personal):
            status_icon = "🟢" if p.get("status", "").lower() == "live" else "🔵"
            btn_text = f"{status_icon} {p.get('title', 'Untitled')} ({p.get('status', 'Dev')})"
            buttons.append([{"text": btn_text, "callback_data": f"view_pers_{idx}"}])

        buttons.append([{"text": "➕ Add Personal Project", "callback_data": "action_add_personal"}])
        buttons.append([{"text": "⬅️ Back to Dashboard", "callback_data": "menu_main"}])

        keyboard = {"inline_keyboard": buttons}
        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    def show_personal_detail(self, chat_id, idx, message_id=None):
        data = load_data()
        personal = data.get("personalProjects", [])
        if idx >= len(personal):
            self.show_personal_menu(chat_id, message_id)
            return

        p = personal[idx]
        status = p.get("status", "Live")
        status_icon = "🟢" if status.lower() == "live" else "🔵"

        text = (
            f"🚀 *Personal Project #{idx + 1}*\n\n"
            f"• *Title:* {p.get('title', '')}\n"
            f"• *Status:* {status_icon} *{status}*\n"
            f"• *URL:* {p.get('url', 'None')}\n"
            f"• *Button Text:* {p.get('buttonText', 'Visit Live Web App')}\n"
            f"• *Tech:* {', '.join(p.get('tech', []))}\n\n"
            f"*Description:*\n{p.get('description', '')}\n"
        )

        toggle_target = "In Progress" if status.lower() == "live" else "Live"
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": f"🔄 Toggle to '{toggle_target}'", "callback_data": f"toggle_pers_status_{idx}"}
                ],
                [
                    {"text": "✏️ Title", "callback_data": f"edit_pers_title_{idx}"},
                    {"text": "✏️ Live URL", "callback_data": f"edit_pers_url_{idx}"}
                ],
                [
                    {"text": "✏️ Button Text", "callback_data": f"edit_pers_btn_{idx}"},
                    {"text": "✏️ Description", "callback_data": f"edit_pers_desc_{idx}"}
                ],
                [
                    {"text": "🗑️ Delete Project", "callback_data": f"del_pers_confirm_{idx}"}
                ],
                [
                    {"text": "⬅️ Back to Personal Projects", "callback_data": "menu_personal"}
                ]
            ]
        }

        if message_id:
            self.edit_message(chat_id, message_id, text, keyboard)
        else:
            self.send_message(chat_id, text, keyboard)

    # =========================================================================
    # Callback Query Router
    # =========================================================================

    def handle_callback_query(self, cb):
        cb_id = cb["id"]
        data_str = cb.get("data", "")
        chat_id = cb["message"]["chat"]["id"]
        message_id = cb["message"]["message_id"]
        from_user = cb.get("from", {})
        username = (from_user.get("username") or "").strip().lower()

        # Strict authorization: Only @DineshK142
        if username != "dineshk142":
            self.answer_callback(cb_id, text="⛔ Access Denied: This is a private admin bot.")
            return

        if not data_str.startswith("move_skill_"):
            self.answer_callback(cb_id)

        # No-op button (placeholder)
        if data_str == "noop":
            return

        # Cancel button
        if data_str == "cancel_input":
            user_states.pop(chat_id, None)
            self.send_message(chat_id, "↩️ Action cancelled.")
            self.show_main_menu(chat_id)
            return

        # Main Nav
        if data_str == "menu_main":
            self.show_main_menu(chat_id, message_id)
        elif data_str == "menu_profile":
            self.show_profile_menu(chat_id, message_id)
        elif data_str == "menu_skills":
            self.show_skills_menu(chat_id, message_id)
        elif data_str == "menu_projects":
            self.show_projects_menu(chat_id, message_id)
        elif data_str == "menu_personal":
            self.show_personal_menu(chat_id, message_id)

        # Quick Actions
        elif data_str == "action_get_data":
            if DATA_PATH.exists():
                self.send_document(chat_id, DATA_PATH, caption="📄 Current data.json configuration")
            else:
                self.send_message(chat_id, "❌ data.json not found.")
        elif data_str == "action_deploy_now":
            self.deploy_pending_changes(chat_id)
        elif data_str == "action_force_deploy":
            self.deploy_pending_changes(chat_id, force=True)

        # Profile Edits
        elif data_str == "edit_prof_exp":
            user_states[chat_id] = {"action": "set_prof_exp"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "📅 Please send the new *Experience Start Date* in `YYYY-MM-DD` (e.g. `2024-02-15`):", cancel_kb)
        elif data_str == "edit_prof_title":
            user_states[chat_id] = {"action": "set_prof_title"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "💼 Please send your new *Job Title* (e.g. `Senior PLM Developer`):", cancel_kb)
        elif data_str == "edit_prof_name":
            user_states[chat_id] = {"action": "set_prof_name"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "👤 Please send your full *Name*:", cancel_kb)
        elif data_str == "edit_prof_phone":
            user_states[chat_id] = {"action": "set_prof_phone"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "📞 Please send your new *Phone Number*:", cancel_kb)
        elif data_str == "edit_prof_email":
            user_states[chat_id] = {"action": "set_prof_email"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "📧 Please send your new *Email Address*:", cancel_kb)
        elif data_str == "edit_prof_linkedin":
            user_states[chat_id] = {"action": "set_prof_linkedin"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "🔗 Please send your *LinkedIn URL*:", cancel_kb)
        elif data_str == "edit_prof_location":
            user_states[chat_id] = {"action": "set_prof_location"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "📍 Please send your *Location* (e.g. `Chennai, India`):", cancel_kb)
        elif data_str == "edit_prof_client":
            user_states[chat_id] = {"action": "set_prof_client"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "🏢 Please send your *Client Engagement Name*:", cancel_kb)

        # Skills Views & Edits
        elif data_str.startswith("view_skills_"):
            cat_key = data_str.replace("view_skills_", "")
            self.show_skills_category(chat_id, cat_key, message_id)
        elif data_str.startswith("detail_skill_"):
            parts = data_str.split("_")
            cat_key = parts[2]
            idx = int(parts[3])
            self.show_skill_detail(chat_id, cat_key, idx, message_id)
        elif data_str.startswith("move_skill_"):
            parts = data_str.split("_")
            cat_key = parts[2]
            idx = int(parts[3])
            direction = parts[4]
            d = load_data()
            skills_list = d.get("skills", {}).get(cat_key, [])

            if idx < len(skills_list):
                skill_name = skills_list[idx].get("name", "")
                if direction == "up" and idx > 0:
                    skills_list[idx], skills_list[idx - 1] = skills_list[idx - 1], skills_list[idx]
                    toast_text = f"Moved '{skill_name}' up to #{idx}"
                elif direction == "down" and idx < len(skills_list) - 1:
                    skills_list[idx], skills_list[idx + 1] = skills_list[idx + 1], skills_list[idx]
                    toast_text = f"Moved '{skill_name}' down to #{idx + 2}"
                elif direction == "top" and idx > 0:
                    item = skills_list.pop(idx)
                    skills_list.insert(0, item)
                    toast_text = f"Moved '{item.get('name')}' to Top (#1)!"
                elif direction == "bottom" and idx < len(skills_list) - 1:
                    item = skills_list.pop(idx)
                    skills_list.append(item)
                    toast_text = f"Moved '{item.get('name')}' to Bottom!"
                else:
                    toast_text = "Already in position"

                # Save silently to data.json without flooding the chat
                with open(DATA_PATH, "w", encoding="utf-8") as f:
                    json.dump(d, f, indent=2, ensure_ascii=False)

                self.answer_callback(cb_id, text=toast_text)
                self.show_skills_category(chat_id, cat_key, message_id)
        elif data_str.startswith("done_skills_"):
            cat_key = data_str.replace("done_skills_", "")
            cat_titles = {
                "coreTC": "Core Teamcenter",
                "integration": "Integration & Upgrade",
                "programming": "Programming & Database",
                "tools": "Tools & Platforms",
                "documentation": "Documentation & Guides"
            }
            title = cat_titles.get(cat_key, cat_key)
            d = load_data()
            import sync
            sync.sync()
            add_pending_change(f"Rearranged skills order in {title}")

            pending = get_pending_changes()
            self.send_message(
                chat_id,
                f"✅ *Skills Order Saved!* ({title})\n\n"
                f"💾 Saved locally in your portfolio.\n"
                f"📝 *Pending changes to deploy:* `{len(pending)}`\n\n"
                f"👉 Tap **🚀 Deploy All Changes** below whenever you are ready to publish to your live website!"
            )
            self.show_skills_menu(chat_id)
        elif data_str.startswith("rename_skill_"):
            parts = data_str.split("_")
            cat_key = parts[2]
            idx = int(parts[3])
            user_states[chat_id] = {"action": "rename_skill_name", "cat_key": cat_key, "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, "✏️ Please send the new name for this skill:", cancel_kb)
        elif data_str.startswith("add_skill_"):
            cat_key = data_str.replace("add_skill_", "")
            user_states[chat_id] = {"action": "add_skill_name", "cat_key": cat_key}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"➕ Please send the *Skill Name* to add to this category:", cancel_kb)
        elif data_str.startswith("del_skill_"):
            parts = data_str.split("_")
            cat_key = parts[2]
            s_idx = int(parts[3])
            d = load_data()
            if cat_key in d.get("skills", {}) and s_idx < len(d["skills"][cat_key]):
                removed = d["skills"][cat_key].pop(s_idx)
                self.trigger_local_update(chat_id, d, f"Removed skill '{removed.get('name')}' from {cat_key}")
                self.show_skills_category(chat_id, cat_key)

        # Experience Projects Router
        elif data_str.startswith("view_proj_"):
            idx = int(data_str.replace("view_proj_", ""))
            self.show_project_detail(chat_id, idx, message_id)
        elif data_str.startswith("toggle_proj_page_"):
            parts = data_str.split("_")
            idx = int(parts[3])
            new_page = int(parts[4])
            d = load_data()
            if idx < len(d.get("projects", [])):
                d["projects"][idx]["page"] = new_page
                self.trigger_local_update(chat_id, d, f"Moved Project #{idx+1} to Resume Page {new_page}")
                self.show_project_detail(chat_id, idx)
        elif data_str.startswith("edit_proj_name_"):
            idx = int(data_str.replace("edit_proj_name_", ""))
            user_states[chat_id] = {"action": "set_proj_name", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"✏️ Send new *Project Name* for Project #{idx + 1}:", cancel_kb)
        elif data_str.startswith("edit_proj_period_"):
            idx = int(data_str.replace("edit_proj_period_", ""))
            user_states[chat_id] = {"action": "set_proj_period", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"📅 Send new *Period* (e.g. `Mar 2026 – Oct 2026` or `Oct 2026 – Present`):", cancel_kb)
        elif data_str.startswith("edit_proj_role_"):
            idx = int(data_str.replace("edit_proj_role_", ""))
            user_states[chat_id] = {"action": "set_proj_role", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"💼 Send new *Role* (e.g. `Teamcenter Developer`):", cancel_kb)
        elif data_str.startswith("edit_proj_tech_"):
            idx = int(data_str.replace("edit_proj_tech_", ""))
            user_states[chat_id] = {"action": "set_proj_tech", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"🏷️ Send *Tech Tags* separated by commas (e.g. `TC 13.2, AWC 5.2, BMIDE, ITK`):", cancel_kb)
        elif data_str.startswith("edit_proj_bullets_"):
            idx = int(data_str.replace("edit_proj_bullets_", ""))
            user_states[chat_id] = {"action": "set_proj_bullets", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"📝 Send bullet points (one bullet per line) to replace achievements for Project #{idx + 1}:", cancel_kb)
        elif data_str.startswith("del_proj_confirm_"):
            idx = int(data_str.replace("del_proj_confirm_", ""))
            d = load_data()
            if idx < len(d.get("projects", [])):
                del_p = d["projects"].pop(idx)
                self.trigger_local_update(chat_id, d, f"Deleted project '{del_p.get('name')}'")
                self.show_projects_menu(chat_id)
        elif data_str == "action_add_project":
            user_states[chat_id] = {"action": "add_project_wizard"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(
                chat_id,
                "➕ *Add New Project*\n\n"
                "Please send the project details in this format:\n"
                "`Name | Period | Role | Tech Tags | Page (1 or 2)`\n\n"
                "*Example:*\n"
                "`Substance Compliance | Mar 2026 – Present | Teamcenter Developer | TC 13.2, BMIDE | 1`",
                cancel_kb
            )

        # Personal Projects Router
        elif data_str.startswith("view_pers_"):
            idx = int(data_str.replace("view_pers_", ""))
            self.show_personal_detail(chat_id, idx, message_id)
        elif data_str.startswith("toggle_pers_status_"):
            idx = int(data_str.replace("toggle_pers_status_", ""))
            d = load_data()
            if idx < len(d.get("personalProjects", [])):
                cur_status = d["personalProjects"][idx].get("status", "Live")
                new_status = "In Progress" if cur_status.lower() == "live" else "Live"
                d["personalProjects"][idx]["status"] = new_status
                d["personalProjects"][idx]["statusColor"] = "green" if new_status.lower() == "live" else "blue"
                self.trigger_local_update(chat_id, d, f"Toggled '{d['personalProjects'][idx].get('title')}' status to {new_status}")
                self.show_personal_detail(chat_id, idx)
        elif data_str.startswith("edit_pers_title_"):
            idx = int(data_str.replace("edit_pers_title_", ""))
            user_states[chat_id] = {"action": "set_pers_title", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"✏️ Send new *Title* for Personal Project #{idx + 1}:", cancel_kb)
        elif data_str.startswith("edit_pers_url_"):
            idx = int(data_str.replace("edit_pers_url_", ""))
            user_states[chat_id] = {"action": "set_pers_url", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"🔗 Send new *URL* for this project:", cancel_kb)
        elif data_str.startswith("edit_pers_btn_"):
            idx = int(data_str.replace("edit_pers_btn_", ""))
            user_states[chat_id] = {"action": "set_pers_btn", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"🔘 Send new *Button Text* (e.g. `Visit Live Web App`):", cancel_kb)
        elif data_str.startswith("edit_pers_desc_"):
            idx = int(data_str.replace("edit_pers_desc_", ""))
            user_states[chat_id] = {"action": "set_pers_desc", "idx": idx}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(chat_id, f"📝 Send new *Description* for this project:", cancel_kb)
        elif data_str.startswith("del_pers_confirm_"):
            idx = int(data_str.replace("del_pers_confirm_", ""))
            d = load_data()
            if idx < len(d.get("personalProjects", [])):
                del_p = d["personalProjects"].pop(idx)
                self.trigger_local_update(chat_id, d, f"Deleted personal project '{del_p.get('title')}'")
                self.show_personal_menu(chat_id)
        elif data_str == "action_add_personal":
            user_states[chat_id] = {"action": "add_pers_wizard"}
            cancel_kb = {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "cancel_input"}]]}
            self.send_message(
                chat_id,
                "➕ *Add Personal Project*\n\n"
                "Please send in format:\n"
                "`Title | Status (Live/In Progress) | URL | Description`\n\n"
                "*Example:*\n"
                "`TC Buddy | Live | https://gateway-ne.github.io/TC-Buddy/ | AI Teamcenter code generator`",
                cancel_kb
            )

    # =========================================================================
    # User Input Processing
    # =========================================================================

    def handle_user_state(self, chat_id, text):
        state = user_states.pop(chat_id, None)
        if not state:
            return False

        action = state.get("action")
        d = load_data()

        try:
            # Profile updates
            if action == "set_prof_exp":
                datetime.strptime(text, "%Y-%m-%d")
                d["personal"]["experienceStartDate"] = text
                calc_exp = calculate_experience(text)
                self.trigger_local_update(chat_id, d, f"Updated Experience Start Date to {text} ({calc_exp})")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_title":
                d["personal"]["title"] = text
                self.trigger_local_update(chat_id, d, f"Updated Job Title to '{text}'")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_name":
                d["personal"]["name"] = text
                parts = text.split(maxsplit=1)
                d["personal"]["firstName"] = parts[0]
                d["personal"]["lastName"] = parts[1] if len(parts) > 1 else ""
                self.trigger_local_update(chat_id, d, f"Updated Name to '{text}'")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_phone":
                d["personal"]["phone"] = text
                self.trigger_local_update(chat_id, d, f"Updated Phone to '{text}'")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_email":
                d["personal"]["email"] = text
                self.trigger_local_update(chat_id, d, f"Updated Email to '{text}'")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_linkedin":
                d["personal"]["linkedin"] = text
                d["personal"]["linkedinDisplay"] = text.replace("https://", "").replace("www.", "")
                self.trigger_local_update(chat_id, d, f"Updated LinkedIn URL")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_location":
                d["personal"]["location"] = text
                self.trigger_local_update(chat_id, d, f"Updated Location to '{text}'")
                self.show_profile_menu(chat_id)
                return True
            elif action == "set_prof_client":
                d["personal"]["client"] = text
                self.trigger_local_update(chat_id, d, f"Updated Client Engagement to '{text}'")
                self.show_profile_menu(chat_id)
                return True

            # Skills updates
            elif action == "add_skill_name":
                cat_key = state.get("cat_key")
                icon = text[:3].upper()
                d["skills"][cat_key].append({"name": text, "icon": icon})
                self.trigger_local_update(chat_id, d, f"Added skill '{text}' to {cat_key}")
                self.show_skills_category(chat_id, cat_key)
                return True
            elif action == "rename_skill_name":
                cat_key = state.get("cat_key")
                idx = state.get("idx")
                if idx < len(d.get("skills", {}).get(cat_key, [])):
                    old_name = d["skills"][cat_key][idx].get("name")
                    d["skills"][cat_key][idx]["name"] = text
                    d["skills"][cat_key][idx]["icon"] = text[:3].upper()
                    self.trigger_local_update(chat_id, d, f"Renamed skill '{old_name}' to '{text}'")
                self.show_skills_category(chat_id, cat_key)
                return True

            # Professional Projects updates
            elif action == "set_proj_name":
                idx = state.get("idx")
                d["projects"][idx]["name"] = text
                self.trigger_local_update(chat_id, d, f"Updated Project #{idx+1} name to '{text}'")
                self.show_project_detail(chat_id, idx)
                return True
            elif action == "set_proj_period":
                idx = state.get("idx")
                d["projects"][idx]["period"] = text
                self.trigger_local_update(chat_id, d, f"Updated Project #{idx+1} period to '{text}'")
                self.show_project_detail(chat_id, idx)
                return True
            elif action == "set_proj_role":
                idx = state.get("idx")
                d["projects"][idx]["role"] = text
                self.trigger_local_update(chat_id, d, f"Updated Project #{idx+1} role to '{text}'")
                self.show_project_detail(chat_id, idx)
                return True
            elif action == "set_proj_tech":
                idx = state.get("idx")
                tags = [t.strip() for t in text.split(",") if t.strip()]
                d["projects"][idx]["techTags"] = tags
                d["projects"][idx]["techResume"] = ", ".join(tags)
                self.trigger_local_update(chat_id, d, f"Updated Project #{idx+1} tech tags")
                self.show_project_detail(chat_id, idx)
                return True
            elif action == "set_proj_bullets":
                idx = state.get("idx")
                bullets = [b.strip() for b in text.split("\n") if b.strip()]
                d["projects"][idx]["bullets"] = bullets
                self.trigger_local_update(chat_id, d, f"Updated Project #{idx+1} bullets")
                self.show_project_detail(chat_id, idx)
                return True
            elif action == "add_project_wizard":
                parts = [p.strip() for p in text.split("|")]
                name = parts[0]
                period = parts[1] if len(parts) > 1 else "Present"
                role = parts[2] if len(parts) > 2 else "Teamcenter Developer"
                tech = [t.strip() for t in parts[3].split(",")] if len(parts) > 3 else ["TC 13.2", "BMIDE"]
                page = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 1
                
                new_proj = {
                    "name": name,
                    "period": period,
                    "role": role,
                    "teamRole": "Team Member",
                    "techResume": ", ".join(tech),
                    "techTags": tech,
                    "categories": ["customization"],
                    "page": page,
                    "bullets": [f"Implemented PLM solutions for {name}."]
                }
                d["projects"].insert(0, new_proj)
                self.trigger_local_update(chat_id, d, f"Added new project '{name}'")
                self.show_projects_menu(chat_id)
                return True

            # Personal Projects updates
            elif action == "set_pers_title":
                idx = state.get("idx")
                d["personalProjects"][idx]["title"] = text
                self.trigger_local_update(chat_id, d, f"Updated personal project title to '{text}'")
                self.show_personal_detail(chat_id, idx)
                return True
            elif action == "set_pers_url":
                idx = state.get("idx")
                d["personalProjects"][idx]["url"] = text
                self.trigger_local_update(chat_id, d, f"Updated personal project URL to '{text}'")
                self.show_personal_detail(chat_id, idx)
                return True
            elif action == "set_pers_btn":
                idx = state.get("idx")
                d["personalProjects"][idx]["buttonText"] = text
                self.trigger_local_update(chat_id, d, f"Updated button text to '{text}'")
                self.show_personal_detail(chat_id, idx)
                return True
            elif action == "set_pers_desc":
                idx = state.get("idx")
                d["personalProjects"][idx]["description"] = text
                self.trigger_local_update(chat_id, d, f"Updated personal project description")
                self.show_personal_detail(chat_id, idx)
                return True
            elif action == "add_pers_wizard":
                parts = [p.strip() for p in text.split("|")]
                title = parts[0]
                status = parts[1] if len(parts) > 1 else "Live"
                url = parts[2] if len(parts) > 2 else ""
                desc = parts[3] if len(parts) > 3 else "Personal project."
                
                new_p = {
                    "id": title.lower().replace(" ", "-"),
                    "title": title,
                    "status": status,
                    "statusColor": "green" if status.lower() == "live" else "blue",
                    "url": url,
                    "buttonText": "Visit Live Web App",
                    "description": desc,
                    "tech": ["HTML", "JavaScript", "Python"]
                }
                d["personalProjects"].append(new_p)
                self.trigger_local_update(chat_id, d, f"Added personal project '{title}'")
                self.show_personal_menu(chat_id)
                return True

        except Exception as e:
            self.send_message(chat_id, f"❌ Error processing input: {e}")
            return True

        return False

    # =========================================================================
    # Main Handler
    # =========================================================================

    def handle_update(self, update):
        if "callback_query" in update:
            self.handle_callback_query(update["callback_query"])
            return

        message = update.get("message")
        if not message:
            return

        chat_id = message["chat"]["id"]
        from_user = message.get("from", {})
        username = (from_user.get("username") or "").strip().lower()
        first_name = from_user.get("first_name", "Friend")

        # Strict Whitelist: ONLY @DineshK142 is authorized
        if username != "dineshk142":
            print(f"[SECURITY BLOCKED] Stranger: @{from_user.get('username')} (ID: {from_user.get('id')})")
            self.send_message(
                chat_id,
                "⛔ *Access Denied*: This is a private admin bot.",
                {"remove_keyboard": True}
            )
            return

        # Direct file upload (data.json)
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
                        
                        if temp_path.exists():
                            temp_path.unlink()
                        
                        self.trigger_local_update(chat_id, new_data, "Uploaded new data.json file")
                        self.show_main_menu(chat_id)
                        return
                    except Exception as e:
                        if temp_path.exists():
                            temp_path.unlink()
                        self.send_message(chat_id, f"❌ *Invalid JSON file*: {e}")
                        return
            else:
                self.send_message(chat_id, "⚠️ Please upload a `.json` file.")
                return

        text = message.get("text", "").strip()
        if not text:
            return

        # Check conversation state
        if self.handle_user_state(chat_id, text):
            return

        # Handle Bottom Persistent Buttons
        if text == "👤 Profile & Bio" or text == "/profile":
            self.show_profile_menu(chat_id)
        elif text == "🛠️ Skills Manager" or text == "/skills":
            self.show_skills_menu(chat_id)
        elif text == "💼 Experience Projects" or text == "/projects":
            self.show_projects_menu(chat_id)
        elif text == "🚀 Personal Projects" or text == "/personal":
            self.show_personal_menu(chat_id)
        elif text == "🚀 Deploy All Changes" or text == "/deploy":
            self.deploy_pending_changes(chat_id)
        elif text == "📄 Download data.json" or text == "/get_data":
            if DATA_PATH.exists():
                self.send_document(chat_id, DATA_PATH, caption="📄 Current data.json configuration")
        elif text == "📊 Live Status" or text == "/status":
            d = load_data()
            p = d.get("personal", {})
            calc = calculate_experience(p.get("experienceStartDate", ""))
            pending = get_pending_changes()
            p_text = f"\n⚠️ Pending changes to deploy: *{len(pending)}*" if pending else "\n✅ Everything is deployed & live"
            self.send_message(
                chat_id,
                f"📊 *Portfolio Status:*\n\n"
                f"👤 *{p.get('name')}* — {p.get('title')}\n"
                f"📅 Experience: *{calc}*\n"
                f"📁 Projects: {len(d.get('projects', []))} | Personal: {len(d.get('personalProjects', []))}"
                f"{p_text}\n\n"
                f"🌐 https://gateway-ne.github.io/DineshK_Portfolio/"
            )
        elif text.startswith("/set_webhook"):
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                wh_url = parts[1].strip()
                r = requests.post(f"{self.api_url}/setWebhook", json={"url": wh_url}).json()
                if r.get("ok"):
                    self.send_message(chat_id, f"✅ *Webhook Activated!*\n\nAll Telegram updates are now sent 24/7 to:\n`{wh_url}`")
                else:
                    self.send_message(chat_id, f"❌ *Error setting webhook:* {r.get('description')}")
            else:
                self.send_message(chat_id, "ℹ️ *Usage:* `/set_webhook https://your-project.vercel.app/api/webhook`")
        elif text == "/delete_webhook":
            r = requests.post(f"{self.api_url}/deleteWebhook").json()
            if r.get("ok"):
                self.send_message(chat_id, "✅ *Webhook Deleted!*\n\nThe bot is now back in polling mode.")
            else:
                self.send_message(chat_id, f"❌ *Error deleting webhook:* {r.get('description')}")
        elif text == "/webhook_info":
            r = requests.get(f"{self.api_url}/getWebhookInfo").json()
            wh = r.get("result", {})
            url = wh.get("url") or "None (Polling Mode)"
            self.send_message(chat_id, f"ℹ️ *Webhook Status:*\n\n• *URL:* `{url}`\n• *Pending Updates:* `{wh.get('pending_update_count', 0)}`")
        elif text == "📋 Main Dashboard" or text == "/menu" or text == "/start":
            self.show_main_menu(chat_id)
        else:
            self.show_main_menu(chat_id)

    def run(self):
        print("[BOT] Button-driven Dinesh K Portfolio Telegram Bot running with Batch Deployment...")
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
                    print("[BOT] Error: Invalid TELEGRAM_BOT_TOKEN.")
                    time.sleep(10)
                else:
                    time.sleep(2)
            except requests.exceptions.RequestException:
                time.sleep(3)
            except KeyboardInterrupt:
                print("\n[BOT] Stopping Telegram Bot...")
                break
            except Exception as e:
                print(f"[BOT] Polling error: {e}")
                time.sleep(2)

def start_render_health_server():
    """Starts a lightweight HTTP server on $PORT for Render health checks if configured."""
    port_env = os.environ.get("PORT")
    if not port_env:
        return
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        class HealthHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header("Content-Type", "text/plain")
                self.end_headers()
                self.wfile.write(b"Dinesh K Portfolio Bot - Running 24/7 OK")
            def log_message(self, format, *args):
                pass
        port = int(port_env)
        server = HTTPServer(("0.0.0.0", port), HealthHandler)
        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        print(f"[BOT] Render Health Check server running on port {port}")
    except Exception as e:
        print(f"[BOT] Render Health server note: {e}")

def ensure_single_instance(port=58921):
    if os.environ.get("PORT") or os.environ.get("VERCEL"):
        return None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("127.0.0.1", port))
        s.listen(1)
        return s
    except OSError:
        print("[BOT] Another instance of bot.py is already running. Exiting cleanly.")
        sys.exit(0)

if __name__ == "__main__":
    start_render_health_server()
    lock_socket = ensure_single_instance()
    if not TELEGRAM_BOT_TOKEN:
        print("ERROR: TELEGRAM_BOT_TOKEN is not set in .env")
        sys.exit(1)

    bot = TelegramBot(TELEGRAM_BOT_TOKEN)
    bot.run()
