
from llm.hk_llm import HKGAIModel
import json

llm = HKGAIModel(system_prompt="You route queries. Only output JSON.")

WEATHER_KEYWORDS = [
    "weather",
    "temperature", 
    "forecast",
    "rain",
    "typhoon",
    "cyclone",
    "storm",
    "tide",
    "tidal",
    "sunrise",
    "sunset",
    "氣溫",
    "天氣",
    "下雨",
    "颱風", 
    "風暴",
    "潮汐",
    "潮高",
    "日出",
    "日落",
    "日中天",
    "天气",
    "气温",
]

HK_MARKERS = ["hong kong", "香港", "hk"]
TYPHOON_MARKERS = ["typhoon", "cyclone", "颱風", "熱帶氣旋", "tropical cyclone", "風球", "signal"]
FINANCE_KEYWORDS = [
    "stock",
    "price",
    "share",
    "ticker",
    "index",
    "market",
    "forex",
    "crypto",
    "恒生指数",
    "恆生指數",
    "恒指",
    "hsi",
    "hang seng",
    "升跌",
    "涨跌",
    "百分比",
    "收市",
    "收盘",
    "市場",
    "股價",
    "股票",
    "金融",
    "汇率",
    "加密货币",
    "比特币",
    "港股",
    "香港股市",
    "港交所",
]

TRAFFIC_KEYWORDS = [
    "traffic",
    "transport",
    "mtr",
    "bus",
    "road",
    "subway",
    "ferry",
    "flight",
    "交通",
    "巴士",
    "地铁",
    "道路",
    "运输",
    "渡轮",
    "航班",
]

GENERAL_KEYWORDS = [
    "你好",
    "hello",
    "谢谢",
    "thank",
    "再见",
    "goodbye",
    "怎么样",
    "如何",
    "什么是",
    "what is",
    "为什么",
    "why",
    "怎么做",
    "how to",
    "介绍",
    "解释",
]

LOCATION_MARKERS = [
    "i am at", "i'm at", "i am in", "i'm in",
    "我在", "位于","地处", "坐标在", "地址是"
]

# 基础路线需求关键词（无具体方式时，默认驾车）
NAVIGATION_MARKERS = ["怎么去", "怎么走", "如何到达", "路线", "导航到", "前往", "route to", "navigate to",
                    "how to get to"]

ACTION_KEYWORDS = ["我要去", "我想去", "想去", "要去", "找", "查找", "附近的", "周边的", "旁边的", "有哪些", "哪里有",
                   "规划去", "附近有", "前往", "最近的"
                "want to go to", "go to", "find", "look for", "nearby", "around", "route to", "navigate to",
                   "drive to", "walk to", "cycle to", "nearest", "cloest"]

#联网搜索
WEB_KEYWORDS =["联网","网上","网络","社交媒体","浏览器",
                    "internet","social media","web"] 

# 添加新的关键词列表(个人信息或者相关词语触发)
RAG_KEYWORDS = [
    "数据库", "database", "文档搜索", "document search", 
    "数据库查询", "search in database","my family","我家","my home","my house","个人信息","personal information"
]

def _contains_any(text: str, keywords) -> bool:
    return any(keyword in text for keyword in keywords)


def _parse_json_response(raw: str):
    stripped = raw.strip()
    if not stripped:
        raise ValueError("empty response")

    if stripped.startswith("```"):
        parts = stripped.split("```")
        for part in parts:
            candidate = part.strip()
            if not candidate:
                continue
            if candidate.lower().startswith("json"):
                candidate = candidate[4:].strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue
        raise ValueError("no valid JSON block found")

    return json.loads(stripped)


def select_sources(query: str):
    cleaned = query.strip()
    lowered = cleaned.lower()

    if not cleaned:
        return {"intent": "general", "sources": ["general_agent"]}

    # 检查是否为一般性对话（优先级最高）
    if _contains_any(lowered, GENERAL_KEYWORDS) or _contains_any(cleaned, GENERAL_KEYWORDS):
        # 但如果同时包含专业领域关键词，则按专业领域处理
        has_rag = _contains_any(lowered, RAG_KEYWORDS) or _contains_any(cleaned, RAG_KEYWORDS)
        has_web = _contains_any(lowered, WEB_KEYWORDS) or _contains_any(cleaned, WEB_KEYWORDS)
        has_weather = _contains_any(lowered, WEATHER_KEYWORDS) or _contains_any(cleaned, WEATHER_KEYWORDS)
        has_finance = _contains_any(lowered, FINANCE_KEYWORDS)
        has_traffic = _contains_any(lowered, TRAFFIC_KEYWORDS) or _contains_any(cleaned, TRAFFIC_KEYWORDS)
        has_location = _contains_any(lowered, LOCATION_MARKERS)
        has_poi = _contains_any(lowered, ACTION_KEYWORDS)
        has_nav = _contains_any(lowered, NAVIGATION_MARKERS)
        
        if not (has_weather or has_finance or has_traffic or has_location or has_poi or has_nav or has_rag or has_web):
            return {"intent": "general", "sources": ["general_agent"]}

    if _contains_any(lowered, WEATHER_KEYWORDS) or _contains_any(cleaned, WEATHER_KEYWORDS):
        sources = {"weather_tool"}
        intent = "weather"
        if _contains_any(lowered, HK_MARKERS):
            sources.add("hong_kong_forecast_tool")
        if _contains_any(lowered, TYPHOON_MARKERS) or _contains_any(cleaned, TYPHOON_MARKERS):
            sources.add("hong_kong_warning_tool")
        return {"intent": intent, "sources": sorted(sources)}

    if _contains_any(lowered, FINANCE_KEYWORDS):
        return {"intent": "finance", "sources": ["finance_tool"]}
        
    if _contains_any(lowered, TRAFFIC_KEYWORDS) or _contains_any(cleaned, TRAFFIC_KEYWORDS):
        return {"intent": "traffic", "sources": ["traffic_tool"]}

    if _contains_any(lowered, LOCATION_MARKERS) and _contains_any(lowered, ACTION_KEYWORDS):
        return {"intent": "transport", "sources": ["transport_tool"]}

    if _contains_any(lowered, ACTION_KEYWORDS) and _contains_any(lowered, NAVIGATION_MARKERS):
        return {"intent": "transport", "sources": ["transport_tool"]}

    if _contains_any(lowered, LOCATION_MARKERS) and _contains_any(lowered, NAVIGATION_MARKERS):
        return {"intent": "transport", "sources": ["transport_tool"]}
    
    if _contains_any(lowered, WEB_KEYWORDS) :#联网
        return {"intent": "web", "sources": ["web_tool"]}
    
    if _contains_any(lowered, RAG_KEYWORDS) :#rag
        return {"intent": "rag", "sources": ["local_rag"]}

    prompt = (
        "You are a routing classifier. Respond with JSON only, e.g. {\"intent\":\"rag\",\"sources\":[\"local_rag\"]}. "
        "Valid intents: rag, weather, finance, traffic, transport, general, other. "
        "Valid sources: local_rag, weather_tool, hong_kong_warning_tool, hong_kong_forecast_tool, finance_tool, traffic_tool, transport_tool, general_agent. "
        "Include local_rag when unsure.\n"
        f"Query: {cleaned}"
    )

    try:
        out = llm(prompt)
        data = _parse_json_response(out)
        sources = data.get("sources") or []
        if not isinstance(sources, list):
            sources = ["local_rag"]

        normalized_sources = []
        for source in sources:
            if source == "weather_tool" or source in {"hong_kong_warning_tool", "hong_kong_forecast_tool"}:
                if "weather_tool" not in normalized_sources:
                    normalized_sources.append("weather_tool")
                if source in {"hong_kong_warning_tool", "hong_kong_forecast_tool"} and source not in normalized_sources:
                    normalized_sources.append(source)
            elif source == "finance_tool":
                if "finance_tool" not in normalized_sources:
                    normalized_sources.append("finance_tool")
            elif source == "traffic_tool":
                if "traffic_tool" not in normalized_sources:
                    normalized_sources.append("traffic_tool")
            elif source == "transport_tool":
                if "transport_tool" not in normalized_sources:
                    normalized_sources.append("transport_tool")
            elif source == "general_agent":
                if "general_agent" not in normalized_sources:
                    normalized_sources.append("general_agent")
            elif source == "web_tool":
                if "web_tool" not in normalized_sources:
                    normalized_sources.append("web_tool")
            elif source == "local_rag":
                if "local_rag" not in normalized_sources:
                    normalized_sources.append("local_rag")

        if not normalized_sources:
            normalized_sources = ["local_rag"]

        if "intent" not in data:
            data["intent"] = "gernral"

        if "weather_tool" in normalized_sources:
            data["intent"] = "weather"
        elif "finance_tool" in normalized_sources:
            data["intent"] = "finance"
        elif "traffic_tool" in normalized_sources:
            data["intent"] = "traffic"
        elif "transport_tool" in normalized_sources:
            data["intent"] = "transport"
        elif "general_agent" in normalized_sources:
            data["intent"] = "general"
        elif "web_tool" in normalized_sources:
            data["intent"] = "web"
        elif "local_rag" in normalized_sources:
            data["intent"] = "rag"
        else:
            normalized_sources = ["local_rag"]#?
            data["intent"] = "general"
         # 默认将意图设置为 general
        if data["intent"] not in ["weather", "finance", "traffic", "transport", "general", "web", "rag"]:
            data["intent"] = "general"

        data["sources"] = normalized_sources
        return data
    except Exception:
        return {"intent": "general", "sources": ["general_agent"]}
