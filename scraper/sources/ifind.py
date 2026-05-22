"""同花顺iFinD新闻源 - 研报、快讯、公告（需API key，降级跳过）"""

from datetime import datetime
from .base import fetch_json, classify_sector

# iFinD开放API基础URL
IFIND_BASE_URL = "https://quantapi.10jqka.com.cn"


def _check_config() -> tuple[str, str] | None:
    try:
        from config import IFIND_API_KEY, IFIND_API_SECRET
        if IFIND_API_KEY and IFIND_API_SECRET:
            return IFIND_API_KEY, IFIND_API_SECRET
    except ImportError:
        pass
    return None


def scrape_reports() -> list[dict]:
    """通过iFinD API抓取研报"""
    creds = _check_config()
    if not creds:
        print("[SKIP] iFinD API not configured")
        return []
    api_key, api_secret = creds
    params = {
        "appkey": api_key,
        "indcode": "",
        "keyword": "AI",
        "page": 1,
        "pagesize": 20,
    }
    data = fetch_json(f"{IFIND_BASE_URL}/api/report/list", params=params)
    return _parse_report_data(data)


def scrape_news() -> list[dict]:
    """通过iFinD API抓取快讯"""
    creds = _check_config()
    if not creds:
        return []
    api_key, api_secret = creds
    params = {
        "appkey": api_key,
        "keyword": "AI 人工智能 算力 芯片 机器人",
        "page": 1,
        "pagesize": 20,
    }
    data = fetch_json(f"{IFIND_BASE_URL}/api/news/list", params=params)
    return _parse_news_data(data)


def _parse_report_data(data: dict) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", {}).get("list", [])
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        results.append({
            "title": title,
            "source": item.get("org", "iFinD研报"),
            "url": item.get("url", ""),
            "date": item.get("date", "")[:10] if item.get("date") else datetime.now().strftime("%Y-%m-%d"),
            "content": item.get("summary", "")[:500] if item.get("summary") else "",
            "category": "research",
            "sector": classify_sector(title, item.get("summary", "")),
        })
    return results


def _parse_news_data(data: dict) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", {}).get("list", [])
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        results.append({
            "title": title,
            "source": "iFinD快讯",
            "url": item.get("url", ""),
            "date": item.get("date", "")[:10] if item.get("date") else datetime.now().strftime("%Y-%m-%d"),
            "content": item.get("content", "")[:500] if item.get("content") else "",
            "category": "industry",
            "sector": classify_sector(title, item.get("content", "")),
        })
    return results


def scrape() -> list[dict]:
    creds = _check_config()
    if not creds:
        print("[SKIP] iFinD: API not configured, skipping")
        return []
    results = []
    results.extend(scrape_reports())
    results.extend(scrape_news())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"iFinD: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
