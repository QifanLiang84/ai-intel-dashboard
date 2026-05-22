"""Claude AI 摘要生成模块"""

import json
from anthropic import Anthropic

try:
    from config import CLAUDE_API_KEY
except ImportError:
    CLAUDE_API_KEY = ""

SECTOR_NAMES = {
    "computing": "算力与国产替代",
    "ai_app": "AI应用",
    "physical_ai": "物理AI",
}

SUMMARY_PROMPT = """你是一位专业的投资分析师，专注于AI产业链研究。请根据以下当日新闻，生成投资情报摘要。

## 要求
1. 每日总摘要：200字以内，概括当日AI产业链最重要的事件和趋势
2. 各赛道分摘要：每个赛道100字以内的核心要点
3. 关键事件：列出3-5个最值得关注的重点事件
4. 投资建议：2-3条简明的投资方向提示

## 输出格式（严格JSON）
```json
{{
  "daily_summary": "今日AI产业链重点关注...",
  "investment_insight": "1. ... 2. ... 3. ...",
  "sector_summaries": {{
    "computing": "算力与国产替代赛道要点（含GPU/芯片/服务器/半导体/信创/EDA/光刻等）...",
    "ai_app": "AI应用赛道要点（含大模型/AIGC/Agent/低空经济/军工AI/国防信息化等）...",
    "physical_ai": "物理AI赛道要点（含机器人/具身智能/自动驾驶等）..."
  }},
  "key_events": [
    "事件1",
    "事件2",
    "事件3"
  ]
}}
```

## 当日新闻数据
{news_data}
"""

RESEARCH_PROMPT = """你是一位专业投资分析师，请对以下券商研报生成简要解读。

## 要求
- 用通俗易懂的语言解释研报核心观点
- 点出对投资者的关键启示
- 每篇研报解读200字以内

## 输出格式（严格JSON）
```json
{{
  "research_highlights": [
    {{
      "title": "研报标题",
      "source": "券商名称",
      "sector": "赛道代码",
      "summary": "AI解读内容...",
      "key_point": "核心观点一句话"
    }}
  ]
}}
```

## 研报数据
{research_data}
"""


def _get_client() -> Anthropic | None:
    if not CLAUDE_API_KEY:
        print("[WARN] Claude API key not configured, skipping AI summary")
        return None
    return Anthropic(api_key=CLAUDE_API_KEY)


def generate_daily_summary(news_by_sector: dict, policy_news: list) -> dict:
    """生成每日摘要"""
    client = _get_client()
    if not client:
        return _empty_summary()

    news_data = {"政策动向": [n["title"] for n in policy_news[:10]]}
    for sector, items in news_by_sector.items():
        sector_name = SECTOR_NAMES.get(sector, sector)
        news_data[sector_name] = [f"- {n['title']} ({n['source']})" for n in items[:10]]

    prompt = SUMMARY_PROMPT.format(news_data=json.dumps(news_data, ensure_ascii=False, indent=2))

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        # 提取JSON
        json_str = _extract_json(text)
        return json.loads(json_str)
    except Exception as e:
        print(f"[ERROR] AI summary generation failed: {e}")
        return _empty_summary()


def generate_research_summary(research_news: list) -> list:
    """生成研报AI解读"""
    client = _get_client()
    if not client or not research_news:
        return []

    research_data = []
    for n in research_news[:10]:
        research_data.append({
            "title": n["title"],
            "source": n.get("source", ""),
            "sector": n.get("sector", "ai_app"),
            "content": n.get("content", "")[:300],
        })

    prompt = RESEARCH_PROMPT.format(research_data=json.dumps(research_data, ensure_ascii=False, indent=2))

    try:
        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=2000,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text
        json_str = _extract_json(text)
        result = json.loads(json_str)
        return result.get("research_highlights", [])
    except Exception as e:
        print(f"[ERROR] Research summary generation failed: {e}")
        return []


def _extract_json(text: str) -> str:
    """从AI回复中提取JSON"""
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
        # 找到最后一个}
        end = text.rindex("}") + 1
        return text[start:end]
    return text


def _empty_summary() -> dict:
    return {
        "daily_summary": "AI摘要未生成（API未配置或Key无效）",
        "investment_insight": "",
        "sector_summaries": {k: "" for k in SECTOR_NAMES},
        "key_events": [],
    }


def generate_rule_summary(news_by_sector: dict, policy_news: list) -> dict:
    """基于规则的摘要生成（API不可用时的降级方案）"""
    # 总摘要：汇总各赛道新闻数量和头条
    sector_counts = []
    sector_summaries = {}
    key_events = []

    for sector, name in SECTOR_NAMES.items():
        items = news_by_sector.get(sector, [])
        count = len(items)
        sector_counts.append(f"{name}{count}条")
        if items:
            top3 = [i["title"] for i in items[:3]]
            sector_summaries[sector] = f"今日{name}相关新闻{count}条。重点关注：" + "；".join(top3)
            # 每个赛道取1条关键事件
            key_events.append(items[0]["title"])
        else:
            sector_summaries[sector] = f"今日{name}相关新闻0条。"

    policy_count = len(policy_news)
    policy_text = f"政策动向{policy_count}条" if policy_count else ""

    all_parts = sector_counts
    if policy_text:
        all_parts.append(policy_text)

    daily_summary = f"今日AI产业链情报汇总：{'，'.join(all_parts)}。"

    # 从政策新闻中提取关键事件
    for p in policy_news[:2]:
        key_events.insert(0, p["title"])

    investment_insight = ""
    if news_by_sector.get("computing"):
        investment_insight += "1. 算力与国产替代赛道有动态，关注相关标的；"
    if news_by_sector.get("ai_app"):
        investment_insight += "2. AI应用赛道活跃，关注大模型商业化进展；"
    if news_by_sector.get("physical_ai"):
        investment_insight += "3. 物理AI赛道有新动态，关注机器人/自动驾驶方向。"

    return {
        "daily_summary": daily_summary,
        "investment_insight": investment_insight,
        "sector_summaries": sector_summaries,
        "key_events": key_events[:5],
    }
