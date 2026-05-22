"""易懂舆情监控 - 需要Cookie登录后抓取"""

from datetime import datetime
from .base import fetch_json, polite_delay, classify_sector, is_excluded_industry

# 易懂舆情监控
YIDONG_BASE = "https://nmas.valueonline.cn/nmas"

# 热门新闻API
YIDONG_HOT_API = f"{YIDONG_BASE}/api/sentiment/hotNews"

# 搜索API
YIDONG_SEARCH_API = f"{YIDONG_BASE}/api/sentiment/search"

# 舆情列表API
YIDONG_LIST_API = f"{YIDONG_BASE}/api/sentiment/list"


def _get_cookie() -> str:
    """从配置中获取易懂Cookie"""
    try:
        from config import YIDONG_COOKIE
        if YIDONG_COOKIE:
            return YIDONG_COOKIE
    except ImportError:
        pass
    return ""


def _fetch_with_cookie(url: str, params: dict = None) -> dict | list | None:
    """带Cookie的请求"""
    import requests
    cookie = _get_cookie()
    if not cookie:
        return None

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Cookie": cookie,
        "Referer": f"{YIDONG_BASE}/index",
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if data.get("success") or data.get("result"):
            return data
        else:
            print(f"  [易懂] API returned error: {data.get('errorMsg', 'unknown')}")
            return None
    except Exception as e:
        print(f"  [易懂] Request failed: {e}")
        return None


def scrape_hot_news() -> list[dict]:
    """抓取易懂热门新闻"""
    data = _fetch_with_cookie(YIDONG_HOT_API, {"page": 1, "pageSize": 20})
    if not data:
        return []
    return _parse_news_data(data, "易懂舆情")


def scrape_ai_news() -> list[dict]:
    """抓取易懂AI相关舆情"""
    results = []
    for keyword in ["AI", "人工智能", "算力", "芯片", "机器人"]:
        params = {
            "keyword": keyword,
            "page": 1,
            "pageSize": 10,
        }
        data = _fetch_with_cookie(YIDONG_SEARCH_API, params)
        if data:
            items = _parse_news_data(data, "易懂舆情")
            results.extend(items)
        polite_delay()
    return results


def _parse_news_data(data: dict, source_name: str) -> list[dict]:
    """解析易懂返回的新闻数据"""
    results = []
    items = data.get("result", [])
    if isinstance(items, dict):
        items = items.get("list", items.get("data", []))
    if not isinstance(items, list):
        return results

    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        if is_excluded_industry(title):
            continue
        content = item.get("content", item.get("summary", item.get("brief", "")))
        url = item.get("url", item.get("link", ""))
        date_str = item.get("publishDate", item.get("date", item.get("ctime", "")))
        if isinstance(date_str, str) and len(date_str) >= 10:
            date_str = date_str[:10]
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        results.append({
            "title": title,
            "source": source_name,
            "url": url,
            "date": date_str,
            "content": (content or "")[:500],
            "category": "industry",
            "sector": classify_sector(title, content or ""),
        })
    return results


def scrape() -> list[dict]:
    """抓取易懂舆情监控"""
    cookie = _get_cookie()
    if not cookie:
        print("[SKIP] 易懂舆情: Cookie未配置，请在config.py中设置YIDONG_COOKIE")
        return []
    print(f"  [易懂] Using cookie ({len(cookie)} chars)")
    results = []
    results.extend(scrape_hot_news())
    results.extend(scrape_ai_news())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"易懂舆情: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
