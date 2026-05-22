# ============================================
# 投资·AI产业链每日情报看板 配置文件
# 复制此文件为 config.py 并填入实际值
# ============================================

import os

# Claude API（也可通过环境变量 CLAUDE_API_KEY 设置）
CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY", "sk-ant-xxx")

# 同花顺 iFinD（可选，无则留空跳过）
IFIND_API_KEY = os.environ.get("IFIND_API_KEY", "")
IFIND_API_SECRET = os.environ.get("IFIND_API_SECRET", "")

# Wind 金融终端（可选，无则留空跳过）
WIND_API_KEY = os.environ.get("WIND_API_KEY", "")
WIND_API_SECRET = os.environ.get("WIND_API_SECRET", "")

# 东方财富 Choice（可选，无则留空跳过）
CHOICE_API_KEY = os.environ.get("CHOICE_API_KEY", "")
CHOICE_API_SECRET = os.environ.get("CHOICE_API_SECRET", "")

# 易懂舆情监控（可选，需登录Cookie）
YIDONG_COOKIE = os.environ.get("YIDONG_COOKIE", "")

# 邮件推送（可选，无则留空跳过）
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "")
EMAIL_TO = []  # ["user1@example.com", "user2@example.com"]

# 爬虫设置
REQUEST_TIMEOUT = 15
REQUEST_DELAY = 2
MAX_RETRIES = 3
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"

# 数据输出路径
DATA_DIR = os.environ.get("DATA_DIR", "../site/data")
