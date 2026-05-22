"""财联社电报 - 从Next.js页面提取数据"""

import re
import json
from datetime import datetime
from .base import create_session, polite_delay, classify_sector, is_excluded_industry

# 财联社电报页面
CLS_TELEGRAPH_URL = "https://www.cls.cn/telegraph"

# 财联社AI话题页面
CLS_AI_URL = "https://www.cls.cn/subject/900041"


def _fetch_next_data(url: str) -> dict | None:
    """从财联社Next.js页面中提取__NEXT_DATA__"""
    s = create_session()
    try:
        resp = s.get(url, timeout=15)
        resp.raise_for_status()
        match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', resp.text)
        if match:
            return json.loads(match.group(1))
    except Exception as e:
        print(f"[ERROR] Failed to fetch CLS page {url}: {e}")
    return None


def _parse_telegraph_items(items: list) -> list[dict]:
    """解析财联社电报数据"""
    results = []
    for item in items:
        title = item.get("title", "") or item.get("brief", "")
        if not title:
            continue
        if is_excluded_industry(title):
            continue
        content = item.get("brief", item.get("content", ""))
        date_str = item.get("ctime", item.get("published_at", ""))
        if isinstance(date_str, (int, float)):
            from datetime import timezone
            date_str = datetime.fromtimestamp(date_str, tz=timezone.utc).strftime("%Y-%m-%d")
        elif isinstance(date_str, str) and len(date_str) >= 10:
            date_str = date_str[:10]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        item_id = item.get("id", item.get("docId", ""))
        results.append({
            "title": title[:100],
            "source": "财联社",
            "url": f"https://www.cls.cn/detail/{item_id}" if item_id else "",
            "date": date_str,
            "content": (content or "")[:500],
            "category": "industry",
            "sector": classify_sector(title, content or ""),
        })
    return results


def scrape_telegraph() -> list[dict]:
    """抓取财联社电报"""
    data = _fetch_next_data(CLS_TELEGRAPH_URL)
    if not data:
        return []
    telegraph = data.get("props", {}).get("initialState", {}).get("telegraph", {})
    items = telegraph.get("telegraphList", [])
    all_items = _parse_telegraph_items(items)
    # 筛选AI相关
    return [i for i in all_items if _is_ai_related(i["title"] + " " + i["content"])]


def scrape_ai_subject() -> list[dict]:
    """抓取财联社AI话题页"""
    data = _fetch_next_data(CLS_AI_URL)
    if not data:
        return []
    # AI话题页数据结构可能不同，尝试多种路径
    items = []
    initial_state = data.get("props", {}).get("initialState", {})
    # 路径1: subject.articles
    subject = initial_state.get("subject", {})
    items = subject.get("articleList", subject.get("articles", []))
    # 路径2: detail
    if not items:
        detail = initial_state.get("detail", {})
        items = detail.get("articleList", [])
    return _parse_telegraph_items(items)


def _is_ai_related(text: str) -> bool:
    keywords = [
        "AI", "人工智能", "大模型", "算力", "芯片", "GPU", "机器人", "自动驾驶",
        "GPT", "LLM", "AIGC", "具身智能", "低空", "国产替代", "半导体",
        "OpenAI", "英伟达", "华为", "百度", "科大讯飞", "字节",
        "军工", "无人机", "eVTOL", "信创", "光模块", "智算",
    ]
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def scrape() -> list[dict]:
    """抓取财联社所有数据"""
    results = []
    results.extend(scrape_telegraph())
    polite_delay()
    results.extend(scrape_ai_subject())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"CLS: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
