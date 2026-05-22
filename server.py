"""投资·AI产业链每日情报看板 - 本地服务器

提供：
  - 静态文件服务（site/目录）
  - /api/refresh 接口触发爬虫刷新数据
  - /api/status 接口查看爬虫状态

用法：
  python server.py              # 默认 http://localhost:8199
  python server.py --port 9000  # 自定义端口
"""

import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

# 项目目录
PROJECT_DIR = Path(__file__).parent.resolve()
SITE_DIR = PROJECT_DIR / "site"
SCRAPER_DIR = PROJECT_DIR / "scraper"

# 爬虫状态
scraper_status = {
    "running": False,
    "last_run": None,
    "last_result": None,
    "last_error": None,
}


def run_scraper():
    """在子线程中运行爬虫管道"""
    if scraper_status["running"]:
        return {"status": "already_running"}

    scraper_status["running"] = True
    scraper_status["last_error"] = None

    try:
        result = subprocess.run(
            [sys.executable, str(SCRAPER_DIR / "main.py")],
            cwd=str(SCRAPER_DIR),
            capture_output=True,
            text=True,
            timeout=300,
            encoding="utf-8",
            errors="replace",
        )

        scraper_status["last_run"] = time.strftime("%Y-%m-%d %H:%M:%S")

        if result.returncode == 0:
            scraper_status["last_result"] = "success"
            return {"status": "success", "output": result.stdout[-500:] if result.stdout else ""}
        else:
            scraper_status["last_result"] = "error"
            scraper_status["last_error"] = result.stderr[-500:] if result.stderr else "Unknown error"
            return {"status": "error", "error": scraper_status["last_error"]}

    except subprocess.TimeoutExpired:
        scraper_status["last_result"] = "timeout"
        scraper_status["last_error"] = "Scraper timed out (300s)"
        return {"status": "error", "error": "Scraper timed out"}

    except Exception as e:
        scraper_status["last_result"] = "error"
        scraper_status["last_error"] = str(e)
        return {"status": "error", "error": str(e)}

    finally:
        scraper_status["running"] = False


class DashboardHandler(http.server.SimpleHTTPRequestHandler):
    """自定义请求处理器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # API 路由
        if path == "/api/refresh":
            self._handle_refresh()
            return

        if path == "/api/status":
            self._handle_status()
            return

        # 静态文件
        super().do_GET()

    def _handle_refresh(self):
        """触发爬虫刷新"""
        if scraper_status["running"]:
            self._json_response({"status": "already_running", "message": "爬虫正在运行中，请稍后"})
            return

        # 启动后台线程运行爬虫
        thread = threading.Thread(target=run_scraper, daemon=True)
        thread.start()

        self._json_response({"status": "started", "message": "爬虫已启动，请等待约1-3分钟"})

    def _handle_status(self):
        """返回爬虫状态"""
        self._json_response({
            "running": scraper_status["running"],
            "last_run": scraper_status["last_run"],
            "last_result": scraper_status["last_result"],
            "last_error": scraper_status["last_error"],
        })

    def _json_response(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

    def log_message(self, format, *args):
        # 静默静态文件日志
        if "/api/" in (args[0] if args else ""):
            super().log_message(format, *args)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="投资·AI产业链每日情报看板 - 本地服务器")
    parser.add_argument("--port", type=int, default=8199, help="端口号（默认8199）")
    parser.add_argument("--no-open", action="store_true", help="不自动打开浏览器")
    args = parser.parse_args()

    port = args.port

    # 允许端口复用
    socketserver.TCPServer.allow_reuse_address = True

    with socketserver.TCPServer(("", port), DashboardHandler) as httpd:
        url = f"http://localhost:{port}"
        print("=" * 50)
        print("投资·AI产业链每日情报看板 - 本地服务器")
        print(f"访问地址: {url}")
        print(f"API: {url}/api/refresh  (手动刷新数据)")
        print(f"API: {url}/api/status   (查看爬虫状态)")
        print("按 Ctrl+C 停止服务器")
        print("=" * 50)

        if not args.no_open:
            threading.Timer(1.0, lambda: webbrowser.open(url)).start()

        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务器已停止")


if __name__ == "__main__":
    main()
