"""Weather agent handling Hong Kong Observatory integrations."""
from __future__ import annotations

import re
from typing import List

from tools import WeatherTools


class WeatherAgent:
    """Agent responsible for weather related questions."""

    def __init__(self, llm, system_prompt: str | None = None):
        self.llm = llm
        self.name = "WeatherAgent"
        self.tools = WeatherTools()
        self.system_prompt = system_prompt

    def _extract_city(self, query: str) -> str:
        """Try to pull out a city name from the query text."""
        cities = [
            "Hong Kong",
            "Beijing",
            "Shanghai",
            "Guangzhou",
            "Shenzhen",
            "Tokyo",
            "London",
            "New York",
        ]
        query_upper = query.upper()

        for city in cities:
            if city.upper() in query_upper:
                return city

        # Chinese aliases for the supported cities
        chinese_cities = {
            "香港": "Hong Kong",
            "北京": "Beijing",
            "上海": "Shanghai",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
        }

        for ch_city, en_city in chinese_cities.items():
            if ch_city in query:
                return en_city

        return "Hong Kong"  # 默认城市

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
            (
                [
                    "支持的接口",
                    "接口列表",
                    "数据类型有哪些",
                    "supported endpoints",
                    "hko endpoints",
                    "weather api 数据类型",
                    "datatype 列表",
                ],
                lambda: self.tools.get_supported_hko_endpoints(),
            ),
            (
                [
                    "实时天气",
                    "實時天氣",
                    "current weather",
                    "rhrread",
                    "最新天气",
                    "最新天氣",
                    "即时天气",
                    "即時天氣",
                ],
                lambda: self.tools.get_real_time_overview(lang=lang),
            ),
            (
                ["九天", "九日", "9-day", "九天天氣", "九天天气", "fnd"],
                lambda: self.tools.get_nine_day_forecast(lang=lang),
            ),
            (
                ["警告摘要", "警告總覽", "警報總覽", "warnsum", "warning summary"],
                lambda: self.tools.get_warning_summary(lang=lang),
            ),
            (
                ["警告详情", "警告詳情", "warning info", "warninginfo"],
                lambda: self.tools.get_warning_details(lang=lang),
            ),
            (
                ["分区警告", "分區警告", "district warning", "warningloc", "各区警告", "各區警告"],
                lambda: self.tools.get_warning_by_district(lang=lang),
            ),
            (
                ["特别天气提示", "特別天氣提示", "special weather tip", "scw", "weather tip"],
                lambda: self.tools.get_special_weather_tips(lang=lang),
            ),
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
            elif ("香港" in query or "hong kong" in query_lower) and any(
                term in query_lower for term in ["综合", "详细", "comprehensive", "全面"]
            ):
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
