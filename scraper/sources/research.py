"""东方财富研报中心 - 仅保留AI产业链相关研报"""

from datetime import datetime
from .base import fetch_page, fetch_json, polite_delay, classify_sector, is_excluded_industry

# 东方财富研报中心 - 行业研报
RESEARCH_INDUSTRY_URL = "https://data.eastmoney.com/report/industry.jshtml"

# 东方财富研报搜索API
RESEARCH_API = "https://reportapi.eastmoney.com/report/list"


def _parse_research_api(data: dict) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", [])
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        # 双重过滤：黑名单 + AI白名单
        if is_excluded_industry(title, item.get("summary", "")):
            continue
        if not _is_ai_related(title, item.get("summary", "")):
            continue
        info_code = item.get("infoCode", "")
        results.append({
            "title": title,
            "source": item.get("orgSName", "券商研报"),
            "url": f"https://data.eastmoney.com/report/zw_industry.jshtml?infocode={info_code}" if info_code else "",
            "date": item.get("publishDate", "")[:10] if item.get("publishDate") else datetime.now().strftime("%Y-%m-%d"),
            "content": item.get("summary", "")[:500] if item.get("summary") else "",
            "category": "research",
            "sector": classify_sector(title, item.get("summary", "")),
        })
    return results


def _parse_research_page(soup) -> list[dict]:
    results = []
    if not soup:
        return results
    for row in soup.select("tr") + soup.select(".report-item"):
        title_el = row.select_one(".title") or row.select_one("a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if not title or len(title) < 6:
            continue
        if is_excluded_industry(title):
            continue
        if not _is_ai_related(title, ""):
            continue
        href = title_el.get("href", "")
        if href.startswith("/"):
            href = "https://data.eastmoney.com" + href
        source_el = row.select_one(".org") or row.select_one(".source")
        source = source_el.get_text(strip=True) if source_el else "券商研报"
        date_el = row.select_one(".date") or row.select_one("time")
        date_text = date_el.get_text(strip=True) if date_el else ""
        results.append({
            "title": title,
            "source": source,
            "url": href,
            "date": date_text or datetime.now().strftime("%Y-%m-%d"),
            "content": "",
            "category": "research",
            "sector": classify_sector(title),
        })
    return results


# 搜索关键词对应的行业分类 - 仅保留AI产业链相关
SEARCH_KEYWORDS = [
    ("人工智能", "ai_app"),
    ("AI", "ai_app"),
    ("算力", "computing"),
    ("半导体", "computing"),
    ("芯片", "computing"),
    ("机器人", "physical_ai"),
    ("自动驾驶", "physical_ai"),
    ("低空经济", "ai_app"),
    ("军工", "ai_app"),
    ("信创", "computing"),
]


def scrape_by_api() -> list[dict]:
    """通过API抓取研报"""
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    for keyword, sector in SEARCH_KEYWORDS:
        params = {
            "industryCode": "*",
            "pageSize": 10,
            "industry": keyword,
            "rating": "",
            "ratingChange": "",
            "beginTime": today,
            "endTime": today,
            "pageNo": 1,
            "fields": "",
            "qType": 1,
            "orgCode": "",
            "code": "",
            "rcode": "",
            "p": 1,
            "pageNum": 1,
            "pageNumber": 1,
        }
        data = fetch_json(RESEARCH_API, params=params)
        items = _parse_research_api(data)
        for item in items:
            item["sector"] = sector
        results.extend(items)
        polite_delay()
    return results


def scrape_by_page() -> list[dict]:
    """通过页面解析抓取研报（备用方案）"""
    soup = fetch_page(RESEARCH_INDUSTRY_URL)
    items = _parse_research_page(soup)
    return [i for i in items if _is_ai_related(i["title"], i.get("content", ""))]


def _is_ai_related(title: str, content: str = "") -> bool:
    keywords = [
        "AI", "人工智能", "大模型", "算力", "芯片", "GPU", "机器人", "自动驾驶",
        "低空", "军工", "国产替代", "半导体", "具身智能", "AIGC", "信创",
    ]
    text = (title + " " + content).lower()
    return any(kw.lower() in text for kw in keywords)


def scrape() -> list[dict]:
    results = scrape_by_api()
    if not results:
        results = scrape_by_page()
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"Research: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
