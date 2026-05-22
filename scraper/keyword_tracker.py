"""关键词提取与热度追踪模块"""

import json
import os
from collections import Counter
from anthropic import Anthropic

try:
    from config import CLAUDE_API_KEY, DATA_DIR
except ImportError:
    CLAUDE_API_KEY = ""
    DATA_DIR = "../site/data"

SECTOR_KEYWORDS = {
    "computing": ["算力", "GPU", "芯片", "服务器", "数据中心", "光模块", "液冷", "IDC", "智算中心",
                   "半导体", "国产芯片", "信创", "自主可控", "国产替代", "EDA", "光刻机"],
    "ai_app": ["大模型", "AIGC", "Agent", "LLM", "GPT", "AI应用", "AI搜索", "AI编程",
               "低空经济", "eVTOL", "无人机", "飞行汽车", "低空管理",
               "军工AI", "国防信息化", "智能装备", "军用无人机"],
    "physical_ai": ["物理AI", "机器人", "具身智能", "自动驾驶", "人形机器人", "智驾"],
}

KEYWORD_PROMPT = """你是一位专业的投资分析师，请从以下当日新闻中提取AI产业链相关的投资关键词。

## 要求
1. 提取15-25个最重要的关键词
2. 每个关键词标注所属赛道和重要程度(1-5)
3. 优先提取：政策关键词、技术趋势词、公司名称、产品名称

## 输出格式（严格JSON）
```json
{{
  "keywords": [
    {{"word": "关键词", "sector": "赛道代码", "weight": 5}},
    ...
  ]
}}
```

赛道代码: computing(算力与国产替代), ai_app(AI应用，含低空经济/军工AI), physical_ai(物理AI)

## 当日新闻标题
{titles}
"""


def extract_keywords(all_news: list) -> list:
    """从新闻中提取关键词"""
    # 1. 先用规则方法快速统计
    rule_keywords = _rule_based_extract(all_news)

    # 2. 再用AI补充提取
    ai_keywords = _ai_extract(all_news)

    # 3. 合并去重，AI结果优先
    return _merge_keywords(rule_keywords, ai_keywords)


def compute_trends(keywords: list, data_dir: str = DATA_DIR) -> list:
    """计算关键词趋势（与昨日对比）"""
    yesterday_file = os.path.join(data_dir, "keywords.json")
    yesterday_data = {}
    if os.path.exists(yesterday_file):
        try:
            with open(yesterday_file, "r", encoding="utf-8") as f:
                old = json.load(f)
                for kw in old.get("keywords", []):
                    yesterday_data[kw["word"]] = kw.get("count", 0)
        except Exception:
            pass

    for kw in keywords:
        old_count = yesterday_data.get(kw["word"], 0)
        new_count = kw.get("count", 0)
        if new_count > old_count:
            kw["trend"] = "up"
        elif new_count < old_count:
            kw["trend"] = "down"
        else:
            kw["trend"] = "stable"
    return keywords


def _rule_based_extract(all_news: list) -> list:
    """基于规则的关键词提取"""
    all_keywords = Counter()
    for news in all_news:
        text = (news.get("title", "") + " " + news.get("content", "")).lower()
        for sector, kws in SECTOR_KEYWORDS.items():
            for kw in kws:
                if kw.lower() in text:
                    all_keywords[(kw, sector)] += 1

    results = []
    raw = all_keywords.most_common(30)

    # 去重：如果短词是长词的子串，且同赛道，则合并到长词
    deduped = {}
    for (word, sector), count in raw:
        # 检查是否已有包含此词的更长关键词
        skip = False
        for existing_word in list(deduped.keys()):
            ew, es = existing_word
            if es == sector and word in ew and word != ew:
                # 短词是长词子串，跳过短词，把计数加到长词
                deduped[existing_word]["count"] += count
                deduped[existing_word]["weight"] = min(5, deduped[existing_word]["count"])
                skip = True
                break
            if es == sector and ew in word and word != ew:
                # 长词包含已有短词，替换为长词
                count += deduped[existing_word]["count"]
                del deduped[existing_word]
                break
        if not skip:
            deduped[(word, sector)] = {
                "word": word,
                "sector": sector,
                "count": count,
                "weight": min(5, count),
                "trend": "stable",
            }

    results = sorted(deduped.values(), key=lambda x: x["weight"], reverse=True)[:25]
    return results


def _ai_extract(all_news: list) -> list:
    """AI关键词提取"""
    if not CLAUDE_API_KEY:
        return []

    titles = "\n".join([f"- {n['title']} ({n.get('source', '')})" for n in all_news[:50]])
    prompt = KEYWORD_PROMPT.format(titles=titles)

    try:
        client = Anthropic(api_key=CLAUDE_API_KEY)
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        json_str = _extract_json(text)
        result = json.loads(json_str)
        keywords = result.get("keywords", [])
        for kw in keywords:
            kw["count"] = kw.get("weight", 1)
            kw["trend"] = "stable"
        return keywords
    except Exception as e:
        print(f"[ERROR] AI keyword extraction failed: {e}")
        return []


def _merge_keywords(rule_kws: list, ai_kws: list) -> list:
    """合并规则和AI关键词"""
    merged = {}
    # 先加入规则结果
    for kw in rule_kws:
        merged[kw["word"]] = kw.copy()
    # AI结果覆盖/补充
    for kw in ai_kws:
        word = kw["word"]
        if word in merged:
            merged[word]["weight"] = max(merged[word]["weight"], kw.get("weight", 1))
            if kw.get("sector"):
                merged[word]["sector"] = kw["sector"]
        else:
            merged[word] = kw.copy()
    return sorted(merged.values(), key=lambda x: x.get("weight", 0), reverse=True)[:25]


def _extract_json(text: str) -> str:
    if "```json" in text:
        start = text.index("```json") + 7
        end = text.index("```", start)
        return text[start:end].strip()
    if "```" in text:
        start = text.index("```") + 3
        end = text.index("```", start)
        return text[start:end].strip()
    if "{" in text:
        start = text.index("{")
        end = text.rindex("}") + 1
        return text[start:end]
    return text
