"""公共爬虫工具函数"""

import time
import random
import requests
from bs4 import BeautifulSoup

try:
    from config import REQUEST_TIMEOUT, REQUEST_DELAY, MAX_RETRIES, USER_AGENT
except ImportError:
    REQUEST_TIMEOUT = 15
    REQUEST_DELAY = 2
    MAX_RETRIES = 3
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"


def create_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    return s


def fetch_page(url: str, session: requests.Session = None, encoding: str = None) -> BeautifulSoup | None:
    s = session or create_session()
    for attempt in range(MAX_RETRIES):
        try:
            resp = s.get(url, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            if encoding:
                resp.encoding = encoding
            else:
                resp.encoding = resp.apparent_encoding
            return BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY + random.uniform(0, 1))
            else:
                print(f"[ERROR] Failed to fetch {url}: {e}")
                return None


def fetch_json(url: str, session: requests.Session = None, params: dict = None) -> dict | list | None:
    s = session or create_session()
    for attempt in range(MAX_RETRIES):
        try:
            resp = s.get(url, params=params, timeout=REQUEST_TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(REQUEST_DELAY + random.uniform(0, 1))
            else:
                print(f"[ERROR] Failed to fetch JSON {url}: {e}")
                return None


def polite_delay():
    time.sleep(REQUEST_DELAY + random.uniform(0.5, 1.5))


# 无关行业黑名单，用于过滤研报
EXCLUDED_INDUSTRIES = [
    "房地产", "地产", "物业", "租赁",
    "零售", "社服", "社会服务", "旅游", "酒店", "餐饮",
    "商社", "美护", "美容", "护理", "化妆品",
    "传媒", "影视", "游戏", "营销", "广告",
    "医药", "生物", "医疗", "中药", "CXO", "器械", "药店",
    "汽车", "零部件", "乘用车", "商用车", "新能源车",
    "食品", "饮料", "白酒", "啤酒", "乳制品",
    "纺织", "服装", "家电", "轻工",
    "建筑", "建材", "钢铁", "煤炭", "有色", "石化",
    "银行", "保险", "证券", "非银",
    "农业", "养殖", "饲料",
    "环保", "公用事业", "交运", "快递",
    "机场", "航空", "工程机械", "港口", "航运", "公路", "铁路",
]


def is_excluded_industry(title: str, content: str = "") -> bool:
    text = (title + " " + content).lower()
    for kw in EXCLUDED_INDUSTRIES:
        if kw in text:
            return True
    return False


# 赛道关键词映射 - 精简为3大赛道
SECTOR_KEYWORDS = {
    "computing": [
        "算力", "GPU", "芯片", "服务器", "数据中心", "英伟达", "NVIDIA", "AMD",
        "寒武纪", "海光信息", "华为昇腾", "光模块", "液冷", "IDC", "智算",
        "半导体", "国产芯片", "中芯国际", "龙芯中科", "EDA", "光刻", "信创",
        "自主可控", "国产替代", "华大九天", "中国软件",
    ],
    "ai_app": [
        "大模型", "AIGC", "Agent", "LLM", "GPT", "OpenAI", "百度", "科大讯飞",
        "字节跳动", "月之暗面", "智谱", "文心", "通义", "Kimi", "Sora",
        "AI应用", "AI办公", "AI搜索", "AI编程",
        "低空经济", "eVTOL", "无人机", "低空管理", "亿航智能", "峰飞航空",
        "小鹏汇天", "低空", "飞行汽车", "通航", "空中出租",
        "军工AI", "军用AI", "国防信息化", "智能装备", "中航沈飞", "航天彩虹",
        "高德红外", "军用无人机", "军工", "国防", "兵器",
        "操作系统", "工业软件",
    ],
    "physical_ai": [
        "物理AI", "机器人", "具身智能", "自动驾驶", "特斯拉", "Figure",
        "优必选", "小鹏", "人形机器人", "工业机器人", "无人驾驶", "智驾",
    ],
}


def classify_sector(title: str, content: str = "") -> str:
    text = (title + " " + content).lower()
    scores = {}
    for sector, keywords in SECTOR_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw.lower() in text)
        if score > 0:
            scores[sector] = score
    if scores:
        return max(scores, key=scores.get)
    return "ai_app"
