"""36氪 AI/创投频道新闻源"""

import re
from datetime import datetime
from .base import fetch_page, fetch_json, polite_delay, classify_sector

# 36氪 AI频道
KR36_AI_URL = "https://36kr.com/information/AI"

# 36氪创投频道
KR36_VC_URL = "https://36kr.com/information/venture"

# 36氪搜索AI相关
KR36_SEARCH_API = "https://gateway.36kr.com/api/mis/nav/home/nav/rank/hot"


def _parse_article_list(soup, source_name: str) -> list[dict]:
    results = []
    if not soup:
        return results
    for article in soup.select("article") + soup.select(".article-item") + soup.select(".kr-flow-article-item"):
        link = article.select_one("a")
        if not link:
            continue
        title_el = article.select_one(".article-item-title") or article.select_one("h2") or article.select_one("a")
        title = title_el.get_text(strip=True) if title_el else ""
        if not title:
            title = link.get_text(strip=True)
        if not title or len(title) < 4:
            continue
        href = link.get("href", "")
        if href.startswith("//"):
            href = "https:" + href
        elif href.startswith("/"):
            href = "https://36kr.com" + href
        date_text = ""
        time_el = article.select_one(".kr-flow-article-item_time") or article.select_one("time") or article.select_one(".time")
        if time_el:
            date_text = time_el.get_text(strip=True)
        summary_el = article.select_one(".article-item-desc") or article.select_one(".desc")
        content = summary_el.get_text(strip=True) if summary_el else ""
        results.append({
            "title": title,
            "source": source_name,
            "url": href,
            "date": date_text or datetime.now().strftime("%Y-%m-%d"),
            "content": content,
            "category": "industry",
            "sector": classify_sector(title, content),
        })
    return results


def _parse_hot_api(data: dict) -> list[dict]:
    results = []
    if not data or "data" not in data:
        return results
    items = data.get("data", {}).get("hotRankList", [])
    for item in items:
        title = item.get("title", "")
        if not title:
            continue
        results.append({
            "title": title,
            "source": "36氪热榜",
            "url": f"https://36kr.com/p/{item.get('entityId', '')}",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "content": item.get("description", ""),
            "category": "industry",
            "sector": classify_sector(title, item.get("description", "")),
        })
    return results


def scrape_ai() -> list[dict]:
    """抓取36氪AI频道"""
    soup = fetch_page(KR36_AI_URL)
    items = _parse_article_list(soup, "36氪")
    # 只保留AI相关
    return [i for i in items if _is_ai_related(i["title"] + " " + i["content"])]


def scrape_vc() -> list[dict]:
    """抓取36氪创投频道"""
    soup = fetch_page(KR36_VC_URL)
    items = _parse_article_list(soup, "36氪创投")
    return [i for i in items if _is_ai_related(i["title"] + " " + i["content"])]


def scrape_hot() -> list[dict]:
    """抓取36氪热榜"""
    data = fetch_json(KR36_SEARCH_API)
    items = _parse_hot_api(data)
    return [i for i in items if _is_ai_related(i["title"] + " " + i["content"])]


def _is_ai_related(text: str) -> bool:
    keywords = [
        "AI", "人工智能", "大模型", "算力", "芯片", "GPU", "机器人", "自动驾驶",
        "GPT", "LLM", "AIGC", "具身智能", "低空", "国产替代", "半导体",
        "OpenAI", "英伟达", "华为", "百度", "科大讯飞", "字节",
    ]
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def scrape() -> list[dict]:
    results = []
    results.extend(scrape_ai())
    polite_delay()
    results.extend(scrape_vc())
    polite_delay()
    results.extend(scrape_hot())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"36Kr: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
