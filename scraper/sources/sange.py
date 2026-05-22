"""扩展研报来源 - 东方财富多维度搜索 + 三个皮匠/慧博等外链"""

from datetime import datetime
from urllib.parse import quote
from .base import fetch_page, fetch_json, polite_delay, classify_sector, is_excluded_industry

# 东方财富研报搜索API（主数据源）
RESEARCH_API = "https://reportapi.eastmoney.com/report/list"

# 三个皮匠报告（外链）
SGPJ_URL = "https://www.sgpjbg.com/search.html"

# 精确搜索关键词 - 只搜AI产业链相关，避免无关行业混入
SEARCH_KEYWORDS = [
    ("人工智能", "ai_app"),
    ("AI大模型", "ai_app"),
    ("算力基础设施", "computing"),
    ("AI芯片", "computing"),
    ("GPU服务器", "computing"),
    ("半导体设备", "computing"),
    ("信创产业", "computing"),
    ("EDA软件", "computing"),
    ("光模块", "computing"),
    ("人形机器人", "physical_ai"),
    ("自动驾驶", "physical_ai"),
    ("具身智能", "physical_ai"),
    ("低空经济", "ai_app"),
    ("军工信息化", "ai_app"),
]


def _parse_research_api(data: dict) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", [])
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        # 双重过滤：黑名单 + AI相关关键词校验
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


def scrape_eastmoney() -> list[dict]:
    """东方财富研报 - 精确关键词搜索"""
    results = []
    today = datetime.now().strftime("%Y-%m-%d")
    for keyword, sector in SEARCH_KEYWORDS:
        params = {
            "industryCode": "*",
            "pageSize": 5,
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


def get_external_links() -> list[dict]:
    """返回三个皮匠等外部研报搜索链接（供用户手动查阅）"""
    links = []
    links.append({
        "title": "三个皮匠报告 - AI产业链相关研报",
        "source": "三个皮匠报告",
        "url": f"{SGPJ_URL}?kw=AI",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "content": "点击查看三个皮匠报告网站上的AI相关研报",
        "category": "research",
        "sector": "ai_app",
    })
    return links


def _is_ai_related(title: str, content: str = "") -> bool:
    """校验是否AI产业链相关"""
    ai_keywords = [
        "AI", "人工智能", "大模型", "算力", "芯片", "GPU", "服务器", "数据中心",
        "机器人", "自动驾驶", "具身智能", "低空经济", "eVTOL",
        "军工AI", "国防信息化", "国产替代", "半导体", "信创",
        "AIGC", "GPT", "LLM", "Agent", "光模块", "液冷",
        "智算", "EDA", "光刻", "自主可控",
    ]
    text = (title + " " + content).lower()
    return any(kw.lower() in text for kw in ai_keywords)


def scrape() -> list[dict]:
    """抓取所有研报数据"""
    # 东方财富精确搜索
    results = scrape_eastmoney()

    # 添加外部研报网站链接
    external = get_external_links()
    results.extend(external)

    return results


if __name__ == "__main__":
    items = scrape()
    print(f"Extended research: {len(items)} items")
    for item in items[:10]:
        print(f"  [{item['source']}] {item['title']}")
