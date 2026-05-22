"""代表性公司动态追踪模块"""

# AI产业链国内外代表性公司（3大赛道）
TRACKED_COMPANIES = {
    "computing": [
        {"name": "英伟达", "name_en": "NVIDIA", "ticker": "NVDA"},
        {"name": "AMD", "name_en": "AMD", "ticker": "AMD"},
        {"name": "华为", "name_en": "Huawei", "ticker": ""},
        {"name": "寒武纪", "name_en": "Cambricon", "ticker": "688256"},
        {"name": "海光信息", "name_en": "Hygon", "ticker": "688041"},
        {"name": "中芯国际", "name_en": "SMIC", "ticker": "688981"},
        {"name": "龙芯中科", "name_en": "Loongson", "ticker": "688047"},
        {"name": "中国软件", "name_en": "China Software", "ticker": "600536"},
        {"name": "华大九天", "name_en": "Empyrean", "ticker": "301269"},
    ],
    "ai_app": [
        {"name": "OpenAI", "name_en": "OpenAI", "ticker": ""},
        {"name": "谷歌", "name_en": "Google", "ticker": "GOOGL"},
        {"name": "百度", "name_en": "Baidu", "ticker": "BIDU"},
        {"name": "科大讯飞", "name_en": "iFlytek", "ticker": "002230"},
        {"name": "字节跳动", "name_en": "ByteDance", "ticker": ""},
        {"name": "月之暗面", "name_en": "Moonshot AI", "ticker": ""},
        {"name": "智谱AI", "name_en": "Zhipu AI", "ticker": ""},
        {"name": "亿航智能", "name_en": "EHang", "ticker": "EH"},
        {"name": "峰飞航空", "name_en": "AutoFlight", "ticker": ""},
        {"name": "小鹏汇天", "name_en": "XPeng AeroHT", "ticker": ""},
        {"name": "中航沈飞", "name_en": "SAC", "ticker": "600760"},
        {"name": "航天彩虹", "name_en": "CH Aerospace", "ticker": "002389"},
        {"name": "高德红外", "name_en": "Guide Infrared", "ticker": "002414"},
    ],
    "physical_ai": [
        {"name": "特斯拉", "name_en": "Tesla", "ticker": "TSLA"},
        {"name": "Figure AI", "name_en": "Figure AI", "ticker": ""},
        {"name": "小鹏汽车", "name_en": "XPeng", "ticker": "XPEV"},
        {"name": "优必选", "name_en": "UBTECH", "ticker": "9880"},
    ],
}

# 公司名到赛道的反向映射
_COMPANY_SECTOR_MAP = {}
for sector, companies in TRACKED_COMPANIES.items():
    for c in companies:
        _COMPANY_SECTOR_MAP[c["name"]] = sector
        if c.get("name_en"):
            _COMPANY_SECTOR_MAP[c["name_en"]] = sector


def get_tracked_company_names() -> list[str]:
    """获取所有追踪公司名称列表"""
    names = []
    for companies in TRACKED_COMPANIES.values():
        for c in companies:
            names.append(c["name"])
            if c.get("name_en"):
                names.append(c["name_en"])
    return names


def classify_company_news(news_list: list) -> dict:
    """将新闻按代表性公司归类"""
    company_updates = {sector: [] for sector in TRACKED_COMPANIES}

    for news in news_list:
        text = (news.get("title", "") + " " + news.get("content", "")).lower()
        for name, sector in _COMPANY_SECTOR_MAP.items():
            if name.lower() in text:
                company_updates[sector].append({
                    "name": name,
                    "event": news["title"],
                    "date": news.get("date", ""),
                    "url": news.get("url", ""),
                    "source": news.get("source", ""),
                })
                break

    # 去重
    for sector in company_updates:
        seen = set()
        unique = []
        for item in company_updates[sector]:
            key = (item["name"], item["event"])
            if key not in seen:
                seen.add(key)
                unique.append(item)
        company_updates[sector] = unique

    return company_updates


def get_company_profile(name: str) -> dict | None:
    """获取公司基本信息"""
    for sector, companies in TRACKED_COMPANIES.items():
        for c in companies:
            if c["name"] == name or c.get("name_en") == name:
                return {**c, "sector": sector}
    return None
