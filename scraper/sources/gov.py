"""政府官方新闻源 - 修复URL + 增加更多政策来源"""

from datetime import datetime
from .base import fetch_page, fetch_json, polite_delay, classify_sector, is_excluded_industry

# 国务院政策
GOV_POLICY_URL = "https://www.gov.cn/zhengce/"

# 工信部
MIIT_URL = "https://www.miit.gov.cn/jgsj/zzgs/wjfb/"

# 发改委
NDRC_URL = "https://www.ndrc.gov.cn/xxgk/zcfb/"

# 工信部公开数据API（更可靠）
MIIT_API = "https://www.miit.gov.cn/api-gateway/jpaas-publish-server/publish-column/columnFileList"


def _parse_gov_cn(soup, source_name: str, base_url: str) -> list[dict]:
    results = []
    if not soup:
        return results
    for item in soup.select("li") + soup.select(".news_item") + soup.select("tr") + soup.select(".list-item"):
        link = item.select_one("a")
        if not link or not link.get("href"):
            continue
        title = link.get_text(strip=True)
        if not title or len(title) < 6:
            continue
        if is_excluded_industry(title):
            continue
        href = link["href"]
        if href.startswith("/"):
            href = base_url + href
        elif not href.startswith("http"):
            href = base_url + "/" + href
        date_text = ""
        date_span = item.select_one(".date") or item.select_one("span") or item.select_one("time")
        if date_span:
            date_text = date_span.get_text(strip=True)
        results.append({
            "title": title,
            "source": source_name,
            "url": href,
            "date": date_text or datetime.now().strftime("%Y-%m-%d"),
            "content": "",
            "category": "policy",
            "sector": classify_sector(title),
        })
    return results


def scrape_gov_policy() -> list[dict]:
    """抓取国务院政策"""
    soup = fetch_page(GOV_POLICY_URL)
    return _parse_gov_cn(soup, "国务院", "https://www.gov.cn")


def scrape_miit() -> list[dict]:
    """抓取工信部公告"""
    # 先尝试API
    try:
        params = {
            "cid": "2c5c3957bea04a58a8e0fa7b06a7f8c3",
            "pagesize": 20,
            "pageno": 1,
        }
        data = fetch_json(MIIT_API, params=params)
        if data and isinstance(data, dict):
            items = data.get("data", {}).get("list", [])
            results = []
            for item in items:
                title = item.get("title", "")
                if not title or is_excluded_industry(title):
                    continue
                results.append({
                    "title": title,
                    "source": "工信部",
                    "url": item.get("url", f"https://www.miit.gov.cn{jitem.get('filePath', '')}" if item.get("filePath") else ""),
                    "date": item.get("publishDate", "")[:10] if item.get("publishDate") else datetime.now().strftime("%Y-%m-%d"),
                    "content": item.get("summary", "")[:300] if item.get("summary") else "",
                    "category": "policy",
                    "sector": classify_sector(title),
                })
            return results
    except Exception:
        pass
    # 降级：HTML解析
    soup = fetch_page(MIIT_URL, encoding="utf-8")
    return _parse_gov_cn(soup, "工信部", "https://www.miit.gov.cn")


def scrape_ndrc() -> list[dict]:
    """抓取发改委通知"""
    soup = fetch_page(NDRC_URL, encoding="utf-8")
    return _parse_gov_cn(soup, "发改委", "https://www.ndrc.gov.cn")


def classify_policy_from_news(news_list: list) -> list:
    """从普通新闻中提取政策类新闻（标题含政策关键词）"""
    policy_keywords = [
        "政策", "规划", "意见", "通知", "公告", "方案", "办法", "条例",
        "工信部", "发改委", "国务院", "财政部", "商务部", "科技部",
        "扶持", "补贴", "激励", "监管", "审批", "试点",
    ]
    results = []
    for news in news_list:
        title = news.get("title", "")
        if any(kw in title for kw in policy_keywords):
            if not is_excluded_industry(title):
                results.append({
                    "title": title,
                    "source": news.get("source", ""),
                    "url": news.get("url", ""),
                    "date": news.get("date", ""),
                    "content": news.get("content", ""),
                    "category": "policy",
                    "sector": classify_sector(title, news.get("content", "")),
                })
    return results


def scrape() -> list[dict]:
    """抓取所有政府官方新闻"""
    results = []
    results.extend(scrape_gov_policy())
    polite_delay()
    results.extend(scrape_miit())
    polite_delay()
    results.extend(scrape_ndrc())
    return results


if __name__ == "__main__":
    items = scrape()
    print(f"Government sources: {len(items)} items")
    for item in items[:5]:
        print(f"  [{item['source']}] {item['title']}")
