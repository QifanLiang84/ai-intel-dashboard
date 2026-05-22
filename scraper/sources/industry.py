"""行业资讯 - IT桔子投融资、公司动态"""

from datetime import datetime
from .base import fetch_page, fetch_json, polite_delay, classify_sector

# IT桔子投融资事件
ITJUZI_FUNDING_URL = "https://www.itjuzi.com/investevent"

# IT桔子大公司动态
ITJUZI_COMPANY_URL = "https://www.itjuzi.com/company"

# 东方财富投融资事件API（备用）
EM_FUNDING_API = "https://datacenter-web.eastmoney.com/api/data/v1/get"


def _parse_itjuzi_funding(soup) -> list[dict]:
    results = []
    if not soup:
        return results
    for row in soup.select(".invest-event-item") + soup.select("tr"):
        company_el = row.select_one(".company-name") or row.select_one("a")
        if not company_el:
            continue
        company = company_el.get_text(strip=True)
        if not company:
            continue
        amount_el = row.select_one(".amount") or row.select_one(".money")
        amount = amount_el.get_text(strip=True) if amount_el else "未披露"
        investor_el = row.select_one(".investor") or row.select_one(".invst")
        investor = investor_el.get_text(strip=True) if investor_el else ""
        industry_el = row.select_one(".industry") or row.select_one(".tag")
        industry = industry_el.get_text(strip=True) if industry_el else ""
        date_el = row.select_one(".date") or row.select_one("time")
        date_text = date_el.get_text(strip=True) if date_el else ""
        title = f"{company}完成{amount}融资"
        if investor:
            title += f" - {investor}"
        content = f"行业: {industry}, 金额: {amount}, 投资方: {investor}" if industry else f"金额: {amount}, 投资方: {investor}"
        results.append({
            "title": title,
            "source": "IT桔子",
            "url": company_el.get("href", ""),
            "date": date_text or datetime.now().strftime("%Y-%m-%d"),
            "content": content,
            "category": "funding",
            "sector": classify_sector(company, industry),
        })
    return results


def _parse_itjuzi_company(soup) -> list[dict]:
    results = []
    if not soup:
        return results
    for item in soup.select(".company-item") + soup.select("tr"):
        name_el = item.select_one(".company-name") or item.select_one("a")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)
        if not name:
            continue
        desc_el = item.select_one(".desc") or item.select_one(".company-desc")
        desc = desc_el.get_text(strip=True) if desc_el else ""
        date_el = item.select_one(".date") or item.select_one("time")
        date_text = date_el.get_text(strip=True) if date_el else ""
        results.append({
            "title": f"{name}动态",
            "source": "IT桔子",
            "url": name_el.get("href", ""),
            "date": date_text or datetime.now().strftime("%Y-%m-%d"),
            "content": desc,
            "category": "company",
            "sector": classify_sector(name, desc),
        })
    return results


def _parse_em_funding(data: dict) -> list[dict]:
    """东方财富投融资API备用方案"""
    results = []
    if not data or "result" not in data:
        return results
    result = data.get("result") or {}
    items = result.get("data", [])
    for item in items:
        title = item.get("TITLE", "") or item.get("title", "")
        if not title:
            continue
        raw_date = item.get("DATE") or item.get("date") or ""
        date_str = raw_date[:10] if len(str(raw_date)) >= 10 else datetime.now().strftime("%Y-%m-%d")
        results.append({
            "title": title,
            "source": "东方财富",
            "url": item.get("URL", item.get("url", "")),
            "date": date_str,
            "content": item.get("SUMMARY", item.get("summary", ""))[:500],
            "category": "funding",
            "sector": classify_sector(title, item.get("SUMMARY", "")),
        })
    return results


def scrape_funding() -> list[dict]:
    """抓取投融资事件"""
    soup = fetch_page(ITJUZI_FUNDING_URL)
    items = _parse_itjuzi_funding(soup)
    if not items:
        # 备用：东方财富API
        params = {
            "sortColumns": "NOTICE_DATE",
            "sortTypes": -1,
            "pageSize": 20,
            "pageNumber": 1,
            "reportName": "RPT_VENTURE_INVESTEVENT",
            "columns": "ALL",
            "filter": '(INDUSTRY="人工智能")',
        }
        data = fetch_json(EM_FUNDING_API, params=params)
        items = _parse_em_funding(data)
    return [i for i in items if _is_ai_related(i["title"] + " " + i["content"])]


def scrape_company() -> list[dict]:
    """抓取公司动态"""
    soup = fetch_page(ITJUZI_COMPANY_URL)
    items = _parse_itjuzi_company(soup)
    return [i for i in items if _is_ai_related(i["title"] + " " + i["content"])]


def _is_ai_related(text: str) -> bool:
    keywords = [
        "AI", "人工智能", "大模型", "算力", "芯片", "GPU", "机器人", "自动驾驶",
        "GPT", "LLM", "AIGC", "具身智能", "低空", "国产替代", "半导体",
        "OpenAI", "英伟达", "华为", "百度", "科大讯飞", "字节", "寒武纪",
        "优必选", "eVTOL", "信创", "军工",
    ]
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def scrape() -> list[dict]:
    results = []
    results.extend(scrape_funding())
    polite_delay()
    results.extend(scrape_company())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"Industry: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
