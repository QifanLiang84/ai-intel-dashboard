"""每日邮件推送模块"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

try:
    from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, EMAIL_FROM, EMAIL_TO
except ImportError:
    SMTP_HOST = ""
    SMTP_PORT = 465
    SMTP_USER = ""
    SMTP_PASSWORD = ""
    EMAIL_FROM = ""
    EMAIL_TO = []


def _build_html(data: dict) -> str:
    """构建邮件HTML内容"""
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))
    summary = data.get("daily_summary", "")
    insight = data.get("investment_insight", "")
    sector_summaries = data.get("sector_summaries", {})
    keywords = data.get("keywords", [])[:10]
    key_events = data.get("key_events", [])
    company_updates = data.get("company_updates", {})

    sector_names = {
        "computing": "算力与国产替代",
        "ai_app": "AI应用",
        "physical_ai": "物理AI",
    }

    # 关键词HTML
    kw_html = ""
    for kw in keywords:
        trend_icon = {"up": "&#9650;", "down": "&#9660;", "stable": "&#9644;"}.get(kw.get("trend", "stable"), "")
        trend_color = {"up": "#4ade80", "down": "#f87171", "stable": "#94a3b8"}.get(kw.get("trend", "stable"), "#94a3b8")
        kw_html += f'<span style="display:inline-block;background:#1e293b;color:#e2e8f0;padding:4px 10px;margin:3px;border-radius:4px;font-size:13px;">{kw["word"]} <span style="color:{trend_color}">{trend_icon}</span></span>'

    # 赛道摘要HTML
    sector_html = ""
    for code, name in sector_names.items():
        text = sector_summaries.get(code, "")
        if text:
            sector_html += f'<div style="margin:8px 0;padding:8px 12px;background:#1e293b;border-left:3px solid #3b82f6;border-radius:4px;"><strong style="color:#60a5fa;">{name}</strong><br><span style="color:#cbd5e1;font-size:14px;">{text}</span></div>'

    # 关键事件HTML
    events_html = ""
    for i, event in enumerate(key_events[:5], 1):
        events_html += f'<li style="color:#e2e8f0;margin:4px 0;font-size:14px;">{event}</li>'

    # 公司动态HTML
    company_html = ""
    for sector, updates in company_updates.items():
        if not updates:
            continue
        name = sector_names.get(sector, sector)
        company_html += f'<div style="margin:6px 0;"><strong style="color:#60a5fa;">{name}</strong></div>'
        for u in updates[:3]:
            company_html += f'<div style="color:#cbd5e1;font-size:13px;padding-left:12px;">- <strong>{u["name"]}</strong>: {u["event"]}</div>'

    html = f"""
    <html><body style="background:#0f172a;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;margin:0;padding:20px;">
    <div style="max-width:680px;margin:0 auto;">
        <div style="text-align:center;padding:20px 0;border-bottom:1px solid #1e293b;">
            <h1 style="color:#f8fafc;font-size:22px;margin:0;">投资·AI产业链每日情报</h1>
            <p style="color:#64748b;font-size:14px;margin:4px 0 0;">{date}</p>
        </div>

        <div style="padding:16px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">每日摘要</h2>
            <p style="color:#cbd5e1;font-size:15px;line-height:1.6;">{summary}</p>
        </div>

        <div style="padding:12px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">投资建议</h2>
            <p style="color:#fbbf24;font-size:14px;line-height:1.6;">{insight}</p>
        </div>

        <div style="padding:12px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">关键事件</h2>
            <ul style="padding-left:20px;margin:0;">{events_html}</ul>
        </div>

        <div style="padding:12px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">热门关键词</h2>
            <div>{kw_html}</div>
        </div>

        <div style="padding:12px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">各赛道动态</h2>
            {sector_html}
        </div>

        <div style="padding:12px 0;">
            <h2 style="color:#f8fafc;font-size:18px;margin:0 0 8px;">重点公司动态</h2>
            {company_html}
        </div>

        <div style="text-align:center;padding:20px 0;color:#475569;font-size:12px;">
            由AI自动生成，仅供参考，不构成投资建议
        </div>
    </div>
    </body></html>
    """
    return html


def send_daily_email(data: dict) -> bool:
    """发送每日情报邮件"""
    if not SMTP_HOST or not SMTP_USER or not EMAIL_TO:
        print("[SKIP] Email: SMTP not configured, skipping")
        return False

    html = _build_html(data)
    date = data.get("date", datetime.now().strftime("%Y-%m-%d"))

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"投资·AI产业链每日情报 | {date}"
    msg["From"] = EMAIL_FROM or SMTP_USER
    msg["To"] = ", ".join(EMAIL_TO)
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(msg["From"], EMAIL_TO, msg.as_string())
        server.quit()
        print(f"[OK] Email sent to {len(EMAIL_TO)} recipients")
        return True
    except Exception as e:
        print(f"[ERROR] Email send failed: {e}")
        return False
