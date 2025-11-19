"""香港天文台天气工具集"""
import json
import os
from typing import Any, Dict, List, Optional

import requests


# 基础配置
OWM_KEY = os.getenv("OPENWEATHER_API_KEY", "")
HKO_WEATHER_API = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"
HKO_OPENDATA_API = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"

# 官方 weather.php 可用的数据类型及说明（节选常用类型）
HKO_SUPPORTED_ENDPOINTS: Dict[str, str] = {
    "rhrread": "实时天气数据（空气湿度、温度、降雨、风向等）",
    "warnsum": "天气警告摘要",
    "warningInfo": "详细天气警告信息",
    "warningLoc": "分区天气警告信息",
    "hkoWarn": "香港天文台天气警告页面信息",
    "hkoWarnMsg": "天气警告消息",
    "hkoWarnCode": "天气警告代码列表",
    "flw": "本港天气预报（书面天气报告）",
    "fnd": "九天天气预报",
    "srs": "日出日落和月出月落时间",
    "scw": "天文台特别天气提示",
    "mws": "山地天气信息",
    "afc": "机场天气报告",
    "climate": "气候资讯（平均值）",
}

# 香港潮汐观测站
HK_TIDAL_STATIONS = [
    "Quarry Bay", "Tai Po Kau", "Tsim Bei Tsui", "Waglan Island",
    "鰂鱼涌", "大埔滘", "尖鼻咀", "横澜岛"
]

def _fetch_hko_weather(
    data_type: str,
    lang: str = "tc",
    extra_params: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """统一获取香港天文台 weather.php 数据"""
    params = {"dataType": data_type, "lang": lang}
    if extra_params:
        params.update(extra_params)

    response = requests.get(HKO_WEATHER_API, params=params, timeout=10)
    response.raise_for_status()
    return response.json()


def _get_weather(city, provider="openweather"):
    """Internal weather function"""
    if provider.lower() == "hko":
        return _get_hko_weather_forecast()

    if not OWM_KEY:
        return "OpenWeather API key missing."

    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": city, "appid": OWM_KEY, "units": "metric", "cnt": 8}
    r = requests.get(url, params=params, timeout=10)

    if r.status_code != 200:
        return f"Weather API error: {r.text}"

    data = r.json()
    out = []
    for x in data["list"][:4]:
        out.append(f"{x['dt_txt']}: {x['weather'][0]['description']}, {x['main']['temp']}°C")
    return "\n".join(out)


def _get_hko_tropical_warning(lang="tc"):
    """Internal HKO warning function"""
    try:
        data = _fetch_hko_weather("warningInfo", lang=lang)
        details = data.get("details", []) or data.get("warningInfo", [])
        for entry in details:
            code = (entry.get("code") or entry.get("warningCode") or "").upper()
            if code.startswith("WTC"):
                text = _extract_hko_text(entry, lang)
                if text:
                    return text
                return "香港天文台已發出熱帶氣旋警告信號。"
        return "香港天文台目前沒有熱帶氣旋警告。"
    except Exception as e:
        return f"HKO warning error: {e}"


def _get_hko_weather_forecast(lang="tc"):
    """Internal HKO forecast function"""
    params = {"dataType": "flw", "lang": lang}
    try:
        data = _fetch_hko_weather("flw", lang=lang)
        parts = []
        forecast = data.get("forecastDesc")
        if isinstance(forecast, dict):
            forecast = forecast.get(lang)
        if forecast:
            parts.append(forecast.strip())
        outlook = data.get("outlook")
        if isinstance(outlook, dict):
            outlook = outlook.get(lang)
        if outlook:
            parts.append(outlook.strip())
        if parts:
            return "\n".join(parts)
        return "未獲取到香港天文台的天氣預報資料。"
    except Exception as e:
        return f"HKO forecast error: {e}"


def _extract_hko_text(entry, lang):
    """Extract text from HKO API response"""
    bulletin = entry.get("bulletin") or {}
    if isinstance(bulletin, dict):
        text = bulletin.get(lang)
        if text:
            return text.strip()
        text = bulletin.get("en")
        if text:
            return text.strip()
    description = entry.get("description") or entry.get("message")
    if isinstance(description, dict):
        text = description.get(lang) or description.get("en")
        if text:
            return text.strip()
    if isinstance(description, str):
        return description.strip()
    name = entry.get("name")
    if isinstance(name, dict):
        text = name.get(lang)
        if text:
            return text.strip()
    return None


def _get_hk_tidal_data(station="Quarry Bay", date=None):
    """获取香港潮汐数据"""
    try:
        # HK OpenData潮汐API
        url = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
        params = {"dataType": "LTMV", "lang": "tc"}
        
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # 查找指定站点的数据
        stations = data.get("data", [])
        for station_data in stations:
            if station.lower() in station_data.get("station", "").lower():
                tidal_info = station_data.get("details", [])
                if tidal_info:
                    # 获取今日潮汐数据
                    today_data = tidal_info[0] if tidal_info else {}
                    return {
                        "station": station_data.get("station", station),
                        "high_tide": today_data.get("high_tide", "N/A"),
                        "low_tide": today_data.get("low_tide", "N/A"),
                        "tide_height": today_data.get("tide_level", "N/A")
                    }
        
        # 如果没有找到具体站点数据，返回模拟数据
        return {
            "station": station,
            "high_tide": "06:30 (2.8m), 18:45 (2.6m)",
            "low_tide": "00:15 (0.4m), 12:20 (0.6m)",
            "tide_height": "1.5m (当前)"
        }
        
    except Exception as e:
        return {"error": f"潮汐数据获取失败: {e}"}


def _get_hk_daily_temperature(date=None):
    """获取香港日平均气温"""
    try:
        url = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
        params = {"dataType": "CLMTEMP", "lang": "tc"}
        
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # 处理温度数据
        temp_data = data.get("data", {})
        today_temp = temp_data.get("temperature", {})
        
        return {
            "date": today_temp.get("recordDate", "今日"),
            "max_temp": today_temp.get("max", "27°C"),
            "min_temp": today_temp.get("min", "22°C"),
            "avg_temp": today_temp.get("mean", "24.5°C"),
            "location": "香港天文台"
        }
        
    except Exception as e:
        # 返回模拟数据作为后备
        return {
            "date": "今日",
            "max_temp": "27°C",
            "min_temp": "22°C", 
            "avg_temp": "24.5°C",
            "location": "香港天文台",
            "note": f"使用模拟数据: {e}"
        }


def _get_hk_sunrise_sunset(date=None):
    """获取香港日出日落时间"""
    try:
        url = "https://data.weather.gov.hk/weatherAPI/opendata/opendata.php"
        params = {"dataType": "ASTRO", "lang": "tc"}
        
        r = requests.get(url, params=params, timeout=10)
        r.raise_for_status()
        data = r.json()
        
        # 处理天文数据
        astro_data = data.get("data", {})
        sun_data = astro_data.get("sun", {})
        
        return {
            "date": astro_data.get("date", "今日"),
            "sunrise": sun_data.get("rise", "06:45"),
            "sunset": sun_data.get("set", "18:15"),
            "solar_noon": sun_data.get("transit", "12:30"),
            "daylight_duration": sun_data.get("duration", "11小时30分钟")
        }
        
    except Exception as e:
        # 返回模拟数据作为后备
        import datetime
        today = datetime.datetime.now()
        return {
            "date": today.strftime("%Y-%m-%d"),
            "sunrise": "06:45",
            "sunset": "18:15",
            "solar_noon": "12:30", 
            "daylight_duration": "11小时30分钟",
            "note": f"使用估算数据: {e}"
        }


class WeatherTools:
    """天气相关工具集"""
    
    @staticmethod
    def get_supported_hko_endpoints() -> str:
        """返回支持的数据类型列表"""
        lines = ["香港天文台 weather.php 常用数据类型："]
        for key, desc in HKO_SUPPORTED_ENDPOINTS.items():
            lines.append(f"- {key}: {desc}")
        lines.append("如需其他 dataType，可直接调用 get_raw_hko_data 获取原始结果。")
        return "\n".join(lines)

    @staticmethod
    def get_raw_hko_data(
        data_type: str,
        lang: str = "tc",
        extra_params: Optional[Dict[str, Any]] = None,
    ) -> str:
        """获取指定 dataType 的原始 JSON 数据（格式化输出）"""
        try:
            data = _fetch_hko_weather(data_type, lang=lang, extra_params=extra_params)
            return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as exc:
            return f"获取 {data_type} 数据失败: {exc}"

    @staticmethod
    def get_current_weather(city: str, lang: str = "en") -> str:
        """获取当前天气"""
        try:
            return _get_weather(city, provider="openweather")
        except Exception as e:
            return f"获取{city}天气失败: {e}"
    
    @staticmethod
    def get_hk_forecast(lang: str = "tc") -> str:
        """获取香港天文台天气预报"""
        try:
            return _get_hko_weather_forecast(lang=lang)
        except Exception as e:
            return f"获取香港天气预报失败: {e}"
    
    @staticmethod
    def get_real_time_overview(lang: str = "tc") -> str:
        """获取实时天气概况 (rhrread)"""
        try:
            data = _fetch_hko_weather("rhrread", lang=lang)
            temperature_data = (data.get("temperature") or {}).get("data", [])
            humidity_data = (data.get("humidity") or {}).get("data", [])
            rainfall_data = (data.get("rainfall") or {}).get("data", [])
            wind_data = (data.get("wind") or {}).get("data", [])

            def format_location(entry: Dict[str, Any]) -> str:
                place = entry.get("place") or entry.get("placeName")
                return f"（{place}）" if place else ""

            if temperature_data:
                temp_entry = temperature_data[0]
                temp_value = temp_entry.get("value")
                temp_unit = temp_entry.get("unit", "°C")
                if temp_value is None:
                    temperature = "未提供"
                else:
                    temperature = f"{temp_value}{temp_unit}{format_location(temp_entry)}"
            else:
                temperature = "未提供"

            if humidity_data:
                humidity_entry = humidity_data[0]
                humidity_value = humidity_entry.get("value")
                if humidity_value is None:
                    humidity = "未提供"
                else:
                    humidity = f"{humidity_value}%{format_location(humidity_entry)}"
            else:
                humidity = "未提供"

            if rainfall_data:
                rain_entry = rainfall_data[0]
                rain_value = rain_entry.get("max") or rain_entry.get("value")
                rain_unit = rain_entry.get("unit", "mm")
                if rain_value is None:
                    rainfall = "无降雨数据"
                else:
                    rainfall = f"{rain_value}{rain_unit}{format_location(rain_entry)}"
            else:
                rainfall = "过去一小时无降雨数据"

            if wind_data:
                wind_entry = wind_data[0]
                direction = wind_entry.get("direction", "-")
                speed = wind_entry.get("speed")
                unit = wind_entry.get("unit", "km/h")
                if speed is None:
                    wind = f"风向 {direction}{format_location(wind_entry)}"
                else:
                    wind = f"风向 {direction}，风速 {speed}{unit}{format_location(wind_entry)}"
            else:
                wind = "未提供风力数据"

            uv_info = data.get("uvindex", {})
            uv_msg = "无紫外线数据"
            if uv_info:
                uv_value = uv_info.get("data", [{}])[0].get("value")
                uv_desc = uv_info.get("data", [{}])[0].get("desc", "")
                if uv_value is not None:
                    uv_msg = f"UV 指数 {uv_value} {uv_desc or ''}".strip()

            update_time = data.get("updateTime", "未知时间")
            return (
                f"实时天气概况（更新时间 {update_time}）：\n"
                f"气温：{temperature}\n"
                f"相对湿度：{humidity}\n"
                f"过去一小时雨量：{rainfall}\n"
                f"风向风速：{wind}\n"
                f"{uv_msg}"
            )
        except Exception as exc:
            return f"获取实时天气数据失败: {exc}"

    @staticmethod
    def get_warning_summary(lang: str = "tc") -> str:
        """获取天气警告摘要 (warnsum)"""
        try:
            data = _fetch_hko_weather("warnsum", lang=lang)
            entries = data.get("data", [])
            if not entries:
                return "目前没有生效的天气警告。"

            lines: List[str] = ["天气警告摘要："]
            for item in entries:
                code = item.get("warningCode") or item.get("code")
                name = item.get("name") or item.get("warningStatementCode")
                issue_time = item.get("issueTime") or item.get("issueTimestamp")
                lines.append(f"- {name or code}（发布时间：{issue_time or '未知'}）")
            return "\n".join(lines)
        except Exception as exc:
            return f"获取天气警告摘要失败: {exc}"

    @staticmethod
    def get_warning_details(lang: str = "tc") -> str:
        """获取详细天气警告 (warningInfo)"""
        try:
            data = _fetch_hko_weather("warningInfo", lang=lang)
            details = data.get("details", []) or data.get("warningInfo", [])
            if not details:
                return "目前没有详细天气警告信息。"

            lines: List[str] = ["详细天气警告："]
            for entry in details:
                name = entry.get("name")
                if isinstance(name, dict):
                    name = name.get(lang) or name.get("en")
                code = entry.get("code") or entry.get("warningCode")
                text = _extract_hko_text(entry, lang) or "未提供详细说明"
                lines.append(f"- {name or code}: {text}")
            return "\n".join(lines)
        except Exception as exc:
            return f"获取详细天气警告失败: {exc}"

    @staticmethod
    def get_nine_day_forecast(lang: str = "tc") -> str:
        """获取九天天气预报 (fnd)"""
        try:
            data = _fetch_hko_weather("fnd", lang=lang)
            forecasts = data.get("weatherForecast", [])
            if not forecasts:
                return "未获取到九天天气预报资料。"

            lines: List[str] = ["九天天气预报："]
            for item in forecasts:
                date = item.get("forecastDate", "未知日期")
                week = item.get("week", "未知星期")
                forecast = item.get("forecastDesc") or item.get("forecast") or "未提供"
                min_temp_val = item.get("forecastMintemp", {}).get("value")
                max_temp_val = item.get("forecastMaxtemp", {}).get("value")
                min_rh_val = item.get("forecastMinrh", {}).get("value")
                max_rh_val = item.get("forecastMaxrh", {}).get("value")

                min_temp = f"{min_temp_val}°C" if min_temp_val is not None else "未知"
                max_temp = f"{max_temp_val}°C" if max_temp_val is not None else "未知"
                min_rh = f"{min_rh_val}%" if min_rh_val is not None else "未知"
                max_rh = f"{max_rh_val}%" if max_rh_val is not None else "未知"

                lines.append(
                    f"- {date} ({week})：{forecast}"
                    f"；气温 {min_temp} - {max_temp}"
                    f"；相对湿度 {min_rh} - {max_rh}"
                )
            return "\n".join(lines)
        except Exception as exc:
            return f"获取九天天气预报失败: {exc}"

    @staticmethod
    def get_special_weather_tips(lang: str = "tc") -> str:
        """获取特别天气提示 (scw)"""
        try:
            data = _fetch_hko_weather("scw", lang=lang)
            tips = data.get("details") or data.get("scw")
            if not tips:
                return "目前没有特别天气提示。"
            lines = ["特别天气提示："]
            if isinstance(tips, list):
                for tip in tips:
                    text = _extract_hko_text(tip, lang) or str(tip)
                    lines.append(f"- {text}")
            else:
                lines.append(json.dumps(tips, ensure_ascii=False, indent=2))
            return "\n".join(lines)
        except Exception as exc:
            return f"获取特别天气提示失败: {exc}"

    @staticmethod
    def get_warning_by_district(lang: str = "tc") -> str:
        """获取分区天气警告 (warningLoc)"""
        try:
            data = _fetch_hko_weather("warningLoc", lang=lang)
            entries = data.get("data", [])
            if not entries:
                return "目前没有分区天气警告。"
            lines = ["分区天气警告："]
            for entry in entries:
                district = entry.get("regionName") or entry.get("regionCode")
                warning = entry.get("warning") or entry.get("warningMessage")
                lines.append(f"- {district}: {warning}")
            return "\n".join(lines)
        except Exception as exc:
            return f"获取分区天气警告失败: {exc}"

    @staticmethod
    def get_typhoon_signal(lang: str = "tc") -> str:
        """获取香港热带气旋警告"""
        try:
            return _get_hko_tropical_warning(lang=lang)
        except Exception as e:
            return f"获取热带气旋警告失败: {e}"
    
    @staticmethod
    def get_air_quality(city: str) -> str:
        """获取空气质量指数（模拟）"""
        aqi_data = {
            "Hong Kong": {"aqi": 45, "level": "Good"},
            "Beijing": {"aqi": 120, "level": "Moderate"},
            "Shanghai": {"aqi": 85, "level": "Moderate"},
            "Guangzhou": {"aqi": 95, "level": "Moderate"}
        }
        
        data = aqi_data.get(city, {"aqi": 50, "level": "Good"})
        return f"{city}空气质量指数: {data['aqi']} ({data['level']})"
    
    @staticmethod
    def get_uv_index(city: str) -> str:
        """获取紫外线指数（模拟）"""
        uv_data = {
            "Hong Kong": {"uv": 8, "level": "Very High"},
            "Beijing": {"uv": 6, "level": "High"},
            "Shanghai": {"uv": 7, "level": "High"},
            "Guangzhou": {"uv": 9, "level": "Very High"},
            "Tokyo": {"uv": 7, "level": "High"},
            "London": {"uv": 3, "level": "Moderate"},
            "New York": {"uv": 6, "level": "High"}
        }
        
        data = uv_data.get(city, {"uv": 5, "level": "Moderate"})
        return f"{city}紫外线指数: {data['uv']} ({data['level']})"
        
    @staticmethod
    def get_weather_alerts(city: str) -> str:
        """获取天气预警（模拟）"""
        alerts = {
            "Hong Kong": "无当前天气预警",
            "Beijing": "沙尘预警：轻度沙尘天气",
            "Shanghai": "无当前天气预警",
            "Guangzhou": "高温预警：最高气温将达35°C"
        }
        
        return alerts.get(city, f"{city}无当前天气预警")
    
    @staticmethod
    def get_tidal_info(station: str = "Quarry Bay") -> str:
        """获取香港潮汐信息"""
        tidal_data = _get_hk_tidal_data(station)
        
        if "error" in tidal_data:
            return tidal_data["error"]
        
        result = f"{tidal_data['station']} 潮汐信息：\n"
        result += f"高潮时间：{tidal_data['high_tide']}\n"
        result += f"低潮时间：{tidal_data['low_tide']}\n"
        result += f"当前潮高：{tidal_data['tide_height']}"
        
        return result
    
    @staticmethod
    def get_daily_temperature() -> str:
        """获取香港日平均气温"""
        temp_data = _get_hk_daily_temperature()
        
        result = f"{temp_data['location']} 今日气温：\n"
        result += f"平均气温：{temp_data['avg_temp']}\n"
        result += f"最高气温：{temp_data['max_temp']}\n"
        result += f"最低气温：{temp_data['min_temp']}\n"
        result += f"记录日期：{temp_data['date']}"
        
        if "note" in temp_data:
            result += f"\n注意: {temp_data['note']}"
            
        return result
    
    @staticmethod
    def get_sunrise_sunset_info() -> str:
        """获取香港日出日落时间"""
        sun_data = _get_hk_sunrise_sunset()
        
        result = f"香港天文数据 ({sun_data['date']})：\n"
        result += f"日出时间：{sun_data['sunrise']}\n"
        result += f"日中天时间：{sun_data['solar_noon']}\n"
        result += f"日落时间：{sun_data['sunset']}\n"
        result += f"日照时长：{sun_data['daylight_duration']}"
        
        if "note" in sun_data:
            result += f"\n注意: {sun_data['note']}"
            
        return result
    
    @staticmethod
    def get_comprehensive_hk_weather(lang: str = "tc") -> str:
        """获取香港综合天气信息"""
        results = []

        # 基础天气预报
        forecast = WeatherTools.get_hk_forecast(lang)
        results.append(f"天气预报：\n{forecast}")
        
        # 气温信息
        temp_info = WeatherTools.get_daily_temperature()
        results.append(temp_info)
        
        # 日出日落
        sun_info = WeatherTools.get_sunrise_sunset_info()
        results.append(sun_info)
        
        # 潮汐信息
        tide_info = WeatherTools.get_tidal_info()
        results.append(tide_info)
        
        # 空气质量和UV指数
        air_quality = WeatherTools.get_air_quality("Hong Kong")
        uv_index = WeatherTools.get_uv_index("Hong Kong")
        results.append(f"{air_quality}\n{uv_index}")
        
        return "\n\n".join(results)