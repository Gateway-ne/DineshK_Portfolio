#!/usr/bin/env python3
"""
server.py - Lightweight Dev Server with Live API for Dinesh K's Portfolio Admin

Runs on http://localhost:8000
- Serves static files (index.html, resume.html, admin.html, assets, etc.)
- POST /api/save: Saves data.json and automatically executes sync.py
"""

import http.server
import json
import socketserver
import subprocess
import sys
from pathlib import Path

PORT = 8000
BASE_DIR = Path(__file__).resolve().parent

class PortfolioRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def end_headers(self):
        # Prevent aggressive browser caching of data.json / html during development
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_POST(self):
        if self.path == "/api/save":
            content_length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(content_length)
            
            try:
                new_data = json.loads(post_data.decode("utf-8"))
                
                # Write to data.json
                data_path = BASE_DIR / "data.json"
                with open(data_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2, ensure_ascii=False)
                
                # Trigger sync.py
                import sync
                sync.sync()
                
                # Respond with success
                response = {
                    "status": "success",
                    "message": "data.json saved and portfolio/resume synchronized successfully!"
                }
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps(response).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_error(404, "Endpoint not found")

def run_server():
    # Use ThreadingHTTPServer so concurrent browser connections / keep-alive do not block the server
    handler = PortfolioRequestHandler
    server_address = ("0.0.0.0", PORT)
    httpd = http.server.ThreadingHTTPServer(server_address, handler)
    httpd.daemon_threads = True
    print(f"[SERVER] Dinesh K Portfolio Server running at http://localhost:{PORT}/")
    print(f"[SERVER] Portfolio: http://localhost:{PORT}/index.html")
    print(f"[SERVER] Resume:    http://localhost:{PORT}/resume.html")
    print(f"[SERVER] Admin UI:  http://localhost:{PORT}/admin.html")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
        httpd.server_close()

# Export handler for Vercel/serverless environments
handler = PortfolioRequestHandler
app = PortfolioRequestHandler

if __name__ == "__main__":
    run_server()
