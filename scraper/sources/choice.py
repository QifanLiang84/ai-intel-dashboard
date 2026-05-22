"""东方财富Choice新闻源 - 研报、行情、资讯（需API key，降级跳过）"""

from datetime import datetime
from .base import fetch_json, classify_sector

# Choice API基础URL
CHOICE_BASE_URL = "https://choiceapi.eastmoney.com"


def _check_config() -> tuple[str, str] | None:
    try:
        from config import CHOICE_API_KEY, CHOICE_API_SECRET
        if CHOICE_API_KEY and CHOICE_API_SECRET:
            return CHOICE_API_KEY, CHOICE_API_SECRET
    except ImportError:
        pass
    return None


def scrape_reports() -> list[dict]:
    """通过Choice API抓取研报"""
    creds = _check_config()
    if not creds:
        return []
    api_key, _ = creds
    params = {
        "apikey": api_key,
        "keyword": "AI 人工智能 算力",
        "type": "report",
        "page": 1,
        "pagesize": 20,
    }
    data = fetch_json(f"{CHOICE_BASE_URL}/api/report/list", params=params)
    return _parse_data(data, "Choice研报", "research")


def scrape_news() -> list[dict]:
    """通过Choice API抓取资讯"""
    creds = _check_config()
    if not creds:
        return []
    api_key, _ = creds
    params = {
        "apikey": api_key,
        "keyword": "AI 人工智能 算力 芯片 机器人",
        "type": "news",
        "page": 1,
        "pagesize": 20,
    }
    data = fetch_json(f"{CHOICE_BASE_URL}/api/news/list", params=params)
    return _parse_data(data, "Choice资讯", "industry")


def _parse_data(data: dict, source_name: str, category: str) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", [])
    if isinstance(items, dict):
        items = items.get("list", items.get("items", []))
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        results.append({
            "title": title,
            "source": item.get("source", source_name),
            "url": item.get("url", ""),
            "date": item.get("date", item.get("publishDate", ""))[:10] if item.get("date") or item.get("publishDate") else datetime.now().strftime("%Y-%m-%d"),
            "content": (item.get("summary") or item.get("content", ""))[:500],
            "category": category,
            "sector": classify_sector(title, item.get("summary", "")),
        })
    return results


def scrape() -> list[dict]:
    creds = _check_config()
    if not creds:
        print("[SKIP] Choice: API not configured, skipping")
        return []
    results = []
    results.extend(scrape_reports())
    results.extend(scrape_news())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"Choice: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
