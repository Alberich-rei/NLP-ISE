import re
from typing import Any, List, Dict

from utils.reranker import rerank
from tools import WeatherTools, FinanceTools, TrafficTools, RAGTools, GeneralTools
from utils.source_selector import select_sources


def get_traffic_info(location: str = "Hong Kong", mode: str = "general") -> str:
    """获取交通信息（模拟实现）"""
    if mode == "mtr":
        return f"MTR Status in {location}: All lines operating normally."
    elif mode == "bus":
        return f"Bus Status in {location}: Normal service on all routes."
    elif mode == "road":
        return f"Road Traffic in {location}: Light to moderate traffic conditions."
    else:
        return f"General Traffic Info for {location}: Public transport and roads operating normally."


class WeatherAgent:
    """天气查询代理"""
    def __init__(self, llm):
        self.llm = llm
        self.name = "WeatherAgent"
        self.tools = WeatherTools()
        
    def _extract_city(self, query: str) -> str:
        """从查询中提取城市名"""
        cities = ["Hong Kong", "Beijing", "Shanghai", "Guangzhou", "Shenzhen", "Tokyo", "London", "New York"]
        query_upper = query.upper()
        
        for city in cities:
            if city.upper() in query_upper:
                return city
        
        # 中文城市名映射
        chinese_cities = {
            "香港": "Hong Kong", "北京": "Beijing", "上海": "Shanghai", 
            "广州": "Guangzhou", "深圳": "Shenzhen"
        }
        
        for ch_city, en_city in chinese_cities.items():
            if ch_city in query:
                return en_city
                
        return "Hong Kong"  # 默认城市
        
    def __init__(self, llm, system_prompt: str = None):
        self.llm = llm
        self.name = "WeatherAgent"
        self.tools = WeatherTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)

    def run(self, query: str, **kwargs) -> str:
        query_lower = query.lower()
        has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in query)
        lang = "tc" if has_chinese else "en"
        city = self._extract_city(query)

        results: List[str] = []

        # dataType 原始数据请求，直接返回原始 JSON
        raw_match = re.search(r"datatype\s*=?\s*([a-z0-9_]+)", query, re.IGNORECASE)
        if raw_match:
            data_type = raw_match.group(1).lower()
            raw_data = self.tools.get_raw_hko_data(data_type, lang=lang)
            if len(raw_data) > 4000:
                raw_data = raw_data[:4000] + "\n...(数据已截断，如需完整内容请直接调用官方接口)"
            return raw_data

        def matches(keywords: List[str]) -> bool:
            for word in keywords:
                if word.lower() in query_lower or word in query:
                    return True
            return False

        handled = False
        hko_checks = [
            (["支持的接口", "接口列表", "数据类型有哪些", "supported endpoints", "hko endpoints", "weather api 数据类型", "datatype 列表"], lambda: self.tools.get_supported_hko_endpoints()),
            (["实时天气", "實時天氣", "current weather", "rhrread", "最新天气", "最新天氣", "即时天气", "即時天氣"], lambda: self.tools.get_real_time_overview(lang=lang)),
            (["九天", "九日", "9-day", "九天天氣", "九天天气", "fnd"], lambda: self.tools.get_nine_day_forecast(lang=lang)),
            (["警告摘要", "警告總覽", "警報總覽", "warnsum", "warning summary"], lambda: self.tools.get_warning_summary(lang=lang)),
            (["警告详情", "警告詳情", "warning info", "warninginfo"], lambda: self.tools.get_warning_details(lang=lang)),
            (["分区警告", "分區警告", "district warning", "warningloc", "各区警告", "各區警告"], lambda: self.tools.get_warning_by_district(lang=lang)),
            (["特别天气提示", "特別天氣提示", "special weather tip", "scw", "weather tip"], lambda: self.tools.get_special_weather_tips(lang=lang)),
        ]

        for keywords, handler in hko_checks:
            if matches(keywords):
                results.append(handler())
                handled = True
                break

        if not handled:
            # 热带气旋警告
            if any(term in query_lower or term in query for term in ["热带气旋", "颱風", "typhoon", "signal", "风球"]):
                typhoon_info = self.tools.get_typhoon_signal(lang=lang)
                results.append(f"热带气旋警告：\n{typhoon_info}")

            # 潮汐查询
            elif any(term in query_lower or term in query for term in ["潮汐", "潮高", "tide", "tidal"]):
                station = "Quarry Bay"  # 默认站点
                if "鱂鱼涌" in query or "quarry bay" in query_lower:
                    station = "Quarry Bay"
                elif "大埔滘" in query or "tai po" in query_lower:
                    station = "Tai Po Kau"
                elif "尖鼻咀" in query or "tsim bei" in query_lower:
                    station = "Tsim Bei Tsui"

                tidal_info = self.tools.get_tidal_info(station)
                results.append(tidal_info)

            # 日出日落查询
            elif any(term in query_lower or term in query for term in ["日出", "日落", "sunrise", "sunset", "日中天"]):
                sun_info = self.tools.get_sunrise_sunset_info()
                results.append(sun_info)

            # 气温查询
            elif any(term in query_lower or term in query for term in ["日平均气温", "今日气温", "daily temp", "最高气温", "最低气温"]):
                temp_info = self.tools.get_daily_temperature()
                results.append(temp_info)

            # 香港综合天气
            elif ("香港" in query or "hong kong" in query_lower) and any(term in query_lower for term in ["综合", "详细", "comprehensive", "全面"]):
                comprehensive_info = self.tools.get_comprehensive_hk_weather(lang=lang)
                results.append(comprehensive_info)

            # 一般香港天气预报
            elif "香港" in query or "hong kong" in query_lower:
                forecast = self.tools.get_hk_forecast(lang=lang)
                results.append(f"香港天气预报：\n{forecast}")

                if "空气" in query or "air" in query_lower:
                    air_quality = self.tools.get_air_quality("Hong Kong")
                    results.append(f"空气质量：{air_quality}")

                if "紫外线" in query or "uv" in query_lower:
                    uv_info = self.tools.get_uv_index("Hong Kong")
                    results.append(f"紫外线指数：{uv_info}")

            # 一般城市天气
            else:
                weather = self.tools.get_current_weather(city, lang=lang)
                results.append(f"{city}天气：\n{weather}")

                if "空气" in query or "air" in query_lower or "aqi" in query_lower:
                    air_quality = self.tools.get_air_quality(city)
                    results.append(f"空气质量：{air_quality}")

                if "紫外线" in query or "uv" in query_lower:
                    uv_info = self.tools.get_uv_index(city)
                    results.append(f"紫外线指数：{uv_info}")

        combined_result = "\n\n".join(results)
        if not combined_result:
            combined_result = "未获取到相关天气信息。"

        prompt = (
            f"Weather query: {query}\nWeather information:\n{combined_result}\n"
            "Provide a comprehensive and helpful weather response."
        )
        return self._call_llm(prompt)


class FinanceAgent:
    """金融查询代理"""
    def __init__(self, llm, system_prompt: str = None):
        self.llm = llm
        self.name = "FinanceAgent"
        self.tools = FinanceTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)
        
    def _extract_symbol(self, query: str) -> str:
        """从查询中提取股票代码或相关符号"""
        query_upper = query.upper()
        
        # 常见股票代码
        common_stocks = ["AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "BABA", "TCEHY"]
        for stock in common_stocks:
            if stock in query_upper:
                return stock
        
        # 中文股票名称映射
        chinese_stocks = {
            "腾讯": "TCEHY",
            "阿里巴巴": "BABA", 
            "苹果": "AAPL",
            "特斯拉": "TSLA",
            "微软": "MSFT",
            "谷歌": "GOOGL"
        }
        
        for chinese_name, symbol in chinese_stocks.items():
            if chinese_name in query:
                return symbol
        
        # 排除常见非股票词汇
        excluded_words = ["FROM", "TO", "AND", "OR", "THE", "IS", "ARE", "WAS", "WERE", 
                         "WHAT", "HOW", "WHY", "WHEN", "WHERE", "WHICH", "ABOUT", "TODAY",
                         "PRICE", "STOCK", "SHARE", "MARKET", "INDEX"]
        
        # 从查询中提取可能的股票代码
        words = query_upper.split()
        for word in words:
            if (len(word) >= 2 and len(word) <= 5 and 
                word.isalpha() and 
                word not in excluded_words):
                return word
                
        return "AAPL"  # 默认
        
    def run(self, query: str) -> str:
        query_lower = query.lower()
        results = []
        
        # 恒生指数专门处理
        if any(term in query for term in ["恒生指数", "恒指", "HSI"]) and any(term in query for term in ["升跌", "百分比", "涨跌", "收市"]):
            hsi_info = self.tools.analyze_market_sentiment(query)
            results.append(f"恒生指数分析：{hsi_info}")
        
        # 香港股市整体查询
        elif any(term in query for term in ["香港股市", "港股", "港交所"]):
            hk_market = self.tools.get_hk_market_summary()
            results.append(f"香港市场摘要：{hk_market}")
        
        # 股票查询
        elif any(term in query_lower for term in ["stock", "share", "股票", "股价"]):
            symbol = self._extract_symbol(query)
            stock_info = self.tools.get_stock_price(symbol)
            results.append(f"股票信息：\n{stock_info}")
        
        # 汇率查询
        elif any(term in query_lower for term in ["exchange", "rate", "汇率", "currency"]):
            # 简单的汇率提取逻辑
            if "usd" in query_lower and "hkd" in query_lower:
                forex = self.tools.get_forex_rate("USD", "HKD")
            elif "eur" in query_lower:
                forex = self.tools.get_forex_rate("EUR", "HKD")
            else:
                forex = self.tools.get_forex_rate()
            results.append(f"汇率：{forex}")
        
        # 市场指数查询
        elif any(term in query_lower for term in ["index", "market", "指数", "市场"]):
            if "hsi" in query_lower or "恒指" in query:
                index_info = self.tools.get_market_index("HSI")
            elif "hstech" in query_lower or "科技" in query:
                index_info = self.tools.get_market_index("HSTECH")
            elif "nasdaq" in query_lower:
                index_info = self.tools.get_market_index("NASDAQ")
            elif "dow" in query_lower:
                index_info = self.tools.get_market_index("DOW")
            else:
                index_info = self.tools.get_market_index("HSI")
            results.append(f"指数信息：{index_info}")
        
        # 加密货币查询
        elif any(term in query_lower for term in ["crypto", "bitcoin", "btc", "ethereum", "eth", "加密", "比特币", "以太坊"]):
            if "btc" in query_lower or "bitcoin" in query_lower or "比特币" in query:
                crypto = self.tools.get_crypto_price("BTC")
            elif "eth" in query_lower or "ethereum" in query_lower or "以太坊" in query:
                crypto = self.tools.get_crypto_price("ETH")
            else:
                crypto = self.tools.get_crypto_price("BTC")
            results.append(f"加密货币：{crypto}")
        
        # 经济新闻
        elif any(term in query_lower for term in ["news", "economic", "新闻", "经济"]):
            news = self.tools.get_economic_news()
            results.append(f"新闻：{news}")
        
        # 如果没有匹配到具体类型，智能分析查询内容
        else:
            # 尝试智能分析
            analysis = self.tools.analyze_market_sentiment(query)
            results.append(f"分析：{analysis}")
            results.append("如需具体股票或指数，请在问题中包含名称或代码。")
        
        combined_result = "\n\n".join(results)
        prompt = f"Finance query: {query}\nFinancial information:\n{combined_result}\nProvide a comprehensive financial response."
        return self._call_llm(prompt)


class TrafficAgent:
    """交通信息代理"""
    def __init__(self, llm, system_prompt: str = None):
        self.llm = llm
        self.name = "TrafficAgent"
        self.tools = TrafficTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)
        
    def run(self, query: str) -> str:
        query_lower = query.lower()
        results = []
        
        # MTR查询
        if any(term in query_lower or term in query for term in ["mtr", "地铁", "subway", "metro"]):
            # 检测具体线路
            if "荃湾" in query or "tsuen wan" in query_lower:
                mtr_info = self.tools.get_mtr_status("tsuen_wan")
            elif "港岛" in query or "island" in query_lower:
                mtr_info = self.tools.get_mtr_status("island")
            elif "观塘" in query or "kwun tong" in query_lower:
                mtr_info = self.tools.get_mtr_status("kwun_tong")
            else:
                mtr_info = self.tools.get_mtr_status()
            results.append(f"地铁信息：{mtr_info}")
        
        # 巴士查询
        if any(term in query_lower or term in query for term in ["bus", "巴士", "公交"]):
            # 尝试提取路线号
            import re
            route_pattern = r'\b\d{1,3}[A-Z]?\b'
            matches = re.findall(route_pattern, query)
            route = matches[0] if matches else "general"
            
            bus_info = self.tools.get_bus_info(route)
            results.append(f"巴士信息：{bus_info}")
        
        # 道路交通查询
        if any(term in query_lower or term in query for term in ["road", "traffic", "道路", "交通", "挤塞"]):
            # 检测区域
            if "九龙" in query or "kowloon" in query_lower:
                traffic = self.tools.get_traffic_conditions("Kowloon")
            elif "新界" in query or "new territories" in query_lower:
                traffic = self.tools.get_traffic_conditions("New Territories")
            elif "过海" in query or "cross harbour" in query_lower:
                traffic = self.tools.get_traffic_conditions("Cross Harbour")
            else:
                traffic = self.tools.get_traffic_conditions()
            results.append(f"道路交通：{traffic}")
        
        # 停车查询
        if any(term in query_lower or term in query for term in ["parking", "停车"]):
            # 提取地点
            locations = ["Central", "Causeway Bay", "Tsim Sha Tsui", "Mong Kok"]
            location = "Central"
            
            for loc in locations:
                if loc.lower() in query_lower:
                    location = loc
                    break
            
            # 中文地名映射
            chinese_locations = {
                "中环": "Central", "铜锣湾": "Causeway Bay", 
                "尖沙咀": "Tsim Sha Tsui", "旺角": "Mong Kok"
            }
            
            for ch_loc, en_loc in chinese_locations.items():
                if ch_loc in query:
                    location = en_loc
                    break
            
            parking_info = self.tools.get_parking_info(location)
            results.append(f"停车信息：{parking_info}")
        
        # 渡轮查询
        if any(term in query_lower or term in query for term in ["ferry", "渡轮", "渡船"]):
            ferry_info = self.tools.get_ferry_schedule()
            results.append(f"渡轮信息：{ferry_info}")
        
        # 航班查询
        if any(term in query_lower for term in ["flight", "airport", "航班", "机场"]):
            flight_info = self.tools.get_flight_info()
            results.append(f"航班信息：{flight_info}")
        
        # 如果没有匹配到具体类型，提供综合交通信息
        if not results:
            general_info = self.tools.get_traffic_conditions()
            results.append(f"交通信息：{general_info}")
        
        combined_result = "\n\n".join(results)
        prompt = f"Traffic query: {query}\nTraffic information:\n{combined_result}\nProvide a comprehensive traffic response."
        return self._call_llm(prompt)


class GeneralAgent:
    """通用对话代理"""
    def __init__(self, llm, system_prompt: str = None):
        self.llm = llm
        self.name = "GeneralAgent"
        self.tools = GeneralTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)

    def run(self, query: str) -> str:
        """处理一般性对话和问题"""
        query_lower = query.lower()

        # 检查是否是问候语
        if any(greeting in query_lower or greeting in query for greeting in 
               ["你好", "hello", "谢谢", "thank", "再见", "goodbye"]):
            return self.tools.get_greeting_response(query)

        # 检查是否询问系统能力
        if any(word in query_lower or word in query for word in 
               ["能做什么", "功能", "能力", "what can you do", "capabilities", "help"]):
            return self.tools.get_capability_info()

        # 其他一般性问题直接调用LLM
        return self._call_llm(f"请回答以下问题：{query}")


class RAGAgent:
    """本地知识库查询代理"""
    def __init__(self, llm, retriever, system_prompt: str = None):
        self.llm = llm
        self.retriever = retriever
        self.name = "RAGAgent"
        self.tools = RAGTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)
        
    def run(self, query: str, fallback_to_llm: bool = False) -> str:
        # 检查知识库状态
        status = self.tools.check_knowledge_base_status(self.retriever)
        if "未初始化" in status:
            if fallback_to_llm:
                # 直接调用LLM回答一般问题
                return self._call_llm(f"请回答以下问题：{query}")
            return "知识库系统不可用，请先初始化RAG系统。"
        
        # 搜索相关文档
        docs_content = self.tools.search_documents(self.retriever, query, top_k=5)
        
        if not docs_content or docs_content[0] == "知识库不可用":
            if fallback_to_llm:
                # 没有相关文档时直接调用LLM
                return self._call_llm(f"请回答以下问题：{query}")
            return self._call_llm(f"我没有找到关于'{query}'的相关信息。请尝试其他问题或检查知识库内容。")
        
        # 使用重排序优化结果
        try:
            docs = self.retriever.get_relevant_documents(query)
            if docs:
                reranked = rerank(query, docs)[:5]
                context = "\n---\n".join([doc.page_content for doc in reranked])
            else:
                context = "\n---\n".join(docs_content)
        except Exception:
            context = "\n---\n".join(docs_content)
        
        # 获取文档摘要信息
        summary = self.tools.get_document_summary(self.retriever, query)
        
        prompt = f"""基于以下知识库内容回答问题。如果基于提供的内容无法回答问题，请明确说明。

知识库状态：{summary}

相关内容：
{context}

Question: {query}

Answer:"""
        return self._call_llm(prompt)


class AgentRouter:
    """代理路由器"""
    def __init__(self, llm, retriever):
        self.weather_agent = WeatherAgent(llm)
        self.finance_agent = FinanceAgent(llm)
        self.traffic_agent = TrafficAgent(llm)
        self.rag_agent = RAGAgent(llm, retriever)
        self.general_agent = GeneralAgent(llm)
        
    def _classify_intent(self, query: str) -> str:
        """分类查询意图 - 使用source_selector进行意图识别"""
        try:
            result = select_sources(query)
            return result.get("intent", "rag")
        except Exception as e:
            print(f"Intent classification error: {e}")
            return "rag"  # 默认回退到RAG
    
    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, str]:
        """处理用户输入并路由到相应代理"""
        query = input_data.get("input", "")
        context = input_data.get("context", "")
        has_history = input_data.get("has_history", False)
        
        # 如果有上下文历史，将其加入到查询中以便代理理解
        if has_history and context:
            enhanced_query = f"Context from previous conversation:\n{context}\n\nCurrent question: {query}"
        else:
            enhanced_query = query
        
        intent = self._classify_intent(query)  # 使用source_selector进行意图识别
        print(f"Intent detected: {intent}")
        
        if intent == "weather":
            result = self.weather_agent.run(enhanced_query)
        elif intent == "finance":
            result = self.finance_agent.run(enhanced_query)
        elif intent == "traffic":
            result = self.traffic_agent.run(enhanced_query)
        elif intent == "general":
            result = self.general_agent.run(enhanced_query)
        else:
            # 先尝试RAG，如果没有相关信息则回退到通用LLM
            result = self.rag_agent.run(enhanced_query, fallback_to_llm=True)
            
        return {"output": result}


def create_tool_agent(llm, retriever) -> AgentRouter:
    """创建多代理系统"""
    return AgentRouter(llm, retriever)
