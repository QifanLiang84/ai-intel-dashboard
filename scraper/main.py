"""投资·AI产业链每日情报看板 - 主调度入口"""

import json
import os
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher

# 添加项目根目录到path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sources import gov, kr36, cls, research, ifind, wind, choice, industry, sange, yidong
from sources.base import is_excluded_industry, SECTOR_KEYWORDS
from ai_summary import generate_daily_summary, generate_research_summary, generate_rule_summary
from keyword_tracker import extract_keywords, compute_trends
from company_tracker import classify_company_news, TRACKED_COMPANIES

try:
    from config import DATA_DIR
except ImportError:
    DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site", "data")


SECTOR_NAMES = {
    "computing": "算力与国产替代",
    "ai_app": "AI应用",
    "physical_ai": "物理AI",
}


def run_scrapers() -> list:
    """运行所有爬虫源"""
    all_news = []
    scrapers = [
        ("政府官方", gov.scrape),
        ("36氪", kr36.scrape),
        ("财联社", cls.scrape),
        ("研报中心", research.scrape),
        ("iFinD", ifind.scrape),
        ("Wind", wind.scrape),
        ("Choice", choice.scrape),
        ("行业资讯", industry.scrape),
        ("三个皮匠/前瞻", sange.scrape),
        ("易懂舆情", yidong.scrape),
    ]
    for name, scraper in scrapers:
        try:
            print(f"[SCRAPING] {name}...")
            items = scraper()
            print(f"  -> {len(items)} items")
            all_news.extend(items)
        except Exception as e:
            print(f"  -> ERROR: {e}")
    return all_news


def deduplicate(news_list: list, threshold: float = 0.7) -> list:
    """按标题相似度去重"""
    seen_titles = []
    unique = []
    for news in news_list:
        title = news.get("title", "")
        is_dup = False
        for seen in seen_titles:
            if SequenceMatcher(None, title, seen).ratio() > threshold:
                is_dup = True
                break
        if not is_dup:
            seen_titles.append(title)
            unique.append(news)
    return unique


def classify_news(news_list: list) -> tuple[dict, list]:
    """按赛道分类新闻，返回 (按赛道分组, 政策新闻列表)"""
    from sources.gov import classify_policy_from_news
    by_sector = {k: [] for k in SECTOR_NAMES}
    by_sector["funding"] = []
    policy = []

    # 先从普通新闻中提取政策类新闻
    extra_policy = classify_policy_from_news(news_list)

    for news in news_list:
        category = news.get("category", "industry")
        sector = news.get("sector", "ai_app")

        if category == "policy":
            policy.append(news)
        elif category == "funding":
            by_sector["funding"].append(news)
        elif category == "research":
            # 研报同时放入对应赛道和研报列表
            if sector in by_sector:
                by_sector[sector].append(news)
        else:
            if sector in by_sector:
                by_sector[sector].append(news)
            else:
                by_sector["ai_app"].append(news)

    # 合并从普通新闻中提取的政策
    for p in extra_policy:
        if p not in policy:
            policy.append(p)

    return by_sector, policy


def run_pipeline():
    """执行完整数据管道"""
    print("=" * 50)
    print("投资·AI产业链每日情报看板")
    print(f"运行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 1. 抓取新闻
    all_news = run_scrapers()
    print(f"\n[TOTAL] Raw news: {len(all_news)} items")

    if not all_news:
        print("[WARN] No news collected, exiting")
        return

    # 2. 去重
    all_news = deduplicate(all_news)
    print(f"[DEDUP] After dedup: {len(all_news)} items")

    # 2.5 最终防线：只保留AI产业链相关新闻
    all_ai_keywords = ["AI", "人工智能", "大模型"]
    for kws in SECTOR_KEYWORDS.values():
        all_ai_keywords.extend(kws)
    filtered = []
    for news in all_news:
        title = news.get("title", "")
        content = news.get("content", "")
        # 三个皮匠外链等特殊条目保留
        if news.get("source") in ["三个皮匠报告"]:
            filtered.append(news)
            continue
        # 黑名单过滤
        if is_excluded_industry(title, content):
            continue
        # 白名单：标题或内容必须包含至少一个AI产业链关键词
        text = (title + " " + content).lower()
        if any(kw.lower() in text for kw in all_ai_keywords):
            filtered.append(news)
        else:
            print(f"  [FILTER] Removed: {title[:50]}")
    removed = len(all_news) - len(filtered)
    if removed > 0:
        print(f"[FILTER] Removed {removed} non-AI items")
    all_news = filtered

    # 3. 分类
    by_sector, policy_news = classify_news(all_news)
    for sector, items in by_sector.items():
        name = SECTOR_NAMES.get(sector, sector)
        print(f"  {name}: {len(items)} items")
    print(f"  政策: {len(policy_news)} items")

    # 4. AI摘要（API不可用时自动降级为规则摘要）
    print("\n[AI] Generating daily summary...")
    summary = generate_daily_summary(by_sector, policy_news)
    if not summary.get("daily_summary") or "未生成" in summary.get("daily_summary", ""):
        print("[FALLBACK] Using rule-based summary...")
        summary = generate_rule_summary(by_sector, policy_news)

    # 5. 研报解读
    research_news = by_sector.get("research", []) if "research" in by_sector else []
    research_items = [n for n in all_news if n.get("category") == "research"]
    print("[AI] Generating research summaries...")
    research_highlights = generate_research_summary(research_items)

    # 6. 关键词追踪
    print("[AI] Extracting keywords...")
    keywords = extract_keywords(all_news)
    keywords = compute_trends(keywords, DATA_DIR)

    # 7. 公司动态
    print("[TRACKING] Company updates...")
    company_updates = classify_company_news(all_news)

    # 8. 组装输出数据
    output = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "daily_summary": summary.get("daily_summary", ""),
        "investment_insight": summary.get("investment_insight", ""),
        "sector_summaries": summary.get("sector_summaries", {}),
        "key_events": summary.get("key_events", []),
        "keywords": keywords,
        "news": {sector: items for sector, items in by_sector.items() if items},
        "policy": policy_news,
        "research_highlights": research_highlights,
        "company_updates": company_updates,
    }

    # 9. 写入文件
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(os.path.join(DATA_DIR, "history"), exist_ok=True)

    latest_path = os.path.join(DATA_DIR, "latest.json")
    with open(latest_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[SAVED] {latest_path}")

    history_path = os.path.join(DATA_DIR, "history", f"{output['date']}.json")
    with open(history_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[SAVED] {history_path}")

    keywords_path = os.path.join(DATA_DIR, "keywords.json")
    with open(keywords_path, "w", encoding="utf-8") as f:
        json.dump({"date": output["date"], "keywords": keywords}, f, ensure_ascii=False, indent=2)

    # 10. 生成自包含HTML文件（双击即可打开）
    print("[BUILD] Generating standalone HTML...")
    _build_standalone_html(output)

    # 11. 邮件推送
    from email_push import send_daily_email
    send_daily_email(output)

    # 12. 自动推送到GitHub（如果配置了git remote）
    _git_push_if_configured()

    print("\n" + "=" * 50)
    print("Pipeline completed!")
    print(f"Total news: {len(all_news)}, Keywords: {len(keywords)}, Sectors: {sum(1 for v in by_sector.values() if v)}")


def _git_push_if_configured():
    """爬虫完成后自动git push，触发GitHub Pages部署"""
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    try:
        result = subprocess.run(
            ["git", "remote"],
            cwd=project_dir,
            capture_output=True, text=True, timeout=10
        )
        if "origin" not in result.stdout:
            return
        print("[GIT] Pushing data to GitHub...")
        subprocess.run(["git", "add", "site/data/", "AI Investment Daily Brief.html"],
                       cwd=project_dir, capture_output=True, timeout=30)
        result = subprocess.run(
            ["git", "diff", "--staged", "--quiet"],
            cwd=project_dir, capture_output=True, timeout=10
        )
        if result.returncode != 0:
            today = datetime.now().strftime("%Y-%m-%d")
            subprocess.run(
                ["git", "commit", "-m", f"📊 Update daily intel - {today}"],
                cwd=project_dir, capture_output=True, timeout=30
            )
            subprocess.run(["git", "push"], cwd=project_dir, capture_output=True, timeout=60)
            print("[GIT] Pushed! GitHub Pages will auto-deploy.")
        else:
            print("[GIT] No changes to push.")
    except Exception as e:
        print(f"[GIT] Push skipped: {e}")


def _build_standalone_html(output: dict):
    """生成自包含HTML文件，双击即可在浏览器中查看"""
    site_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "site")

    # 读取CSS
    css_path = os.path.join(site_dir, "css", "style.css")
    with open(css_path, "r", encoding="utf-8") as f:
        css_content = f.read()

    # 读取JS
    js_path = os.path.join(site_dir, "js", "app.js")
    with open(js_path, "r", encoding="utf-8") as f:
        js_content = f.read()

    # 读取HTML模板
    html_path = os.path.join(site_dir, "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()

    # 将JSON数据嵌入JS
    json_data = json.dumps(output, ensure_ascii=False)
    injected_js = f"const EMBEDDED_DATA = {json_data};\n"

    # 修改JS：如果EMBEDDED_DATA存在则直接使用，否则走fetch
    patched_js = injected_js + js_content.replace(
        'async function loadData(date) {',
        'async function loadData(date) {\n    if (!date && typeof EMBEDDED_DATA !== "undefined") { currentData = EMBEDDED_DATA; renderAll(EMBEDDED_DATA); return EMBEDDED_DATA; }'
    )

    # 构建自包含HTML
    standalone = html_content
    # 移除外部CSS引用
    standalone = standalone.replace('<link rel="stylesheet" href="css/style.css">', f'<style>\n{css_content}\n</style>')
    # 移除外部JS引用
    standalone = standalone.replace('<script src="js/app.js"></script>', f'<script>\n{patched_js}\n</script>')

    # 输出文件
    out_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "AI Investment Daily Brief.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(standalone)
    print(f"[SAVED] {out_path}")


if __name__ == "__main__":
    run_pipeline()
