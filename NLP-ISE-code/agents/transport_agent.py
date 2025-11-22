# transport_agent.py
from __future__ import annotations
import re
from tools import TransportTools

LOCATION_MARKERS = [
    "i am at", "i'm at", "i am in", "i'm in",
    "我在", "位于","地处", "坐标在", "地址是"
]

# 识别"最近"的关键词
NEAREST_MARKERS = [
    "nearest", "closest", "最近"
]

# 基础路线需求关键词（无具体方式时，默认驾车）
BASE_NAV_MARKERS = ["怎么去", "怎么走", "如何到达", "路线", "导航到", "前往", "route to", "navigate to",
                    "how to get to"]

class TransportAgent:
    def __init__(self, llm, system_prompt: str | None = None):
        self.llm = llm
        self.tools = TransportTools()
        self.name = "TransportTools"
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        """Call LLM with optional system prompt."""
        if self.system_prompt:
            final_prompt = f"{self.system_prompt}\n\n{prompt}"
        else:
            final_prompt = prompt
        return self.llm(final_prompt)

    # 1. 解析英文提问 + 中英文关键词体系（新增has_nearest识别）
    def parse(self, q: str):
        q_lower = q.lower()
        original_q = q.strip()  # 去除首尾空格，避免干扰
        location = None
        poi = None
        nead_route = False
        has_nearest = False
        route_type = None  # 新增：路线类型（driving/walking/cycling/None）

        # a) 位置提取
        chinese_separators = r"(?:,|，|。|！|？|、|；|\s|附近|周边|旁边|有哪些|在哪里|怎么去|如何到达|找|求)"
        for marker in LOCATION_MARKERS:
            if marker in ["i am at", "i'm at", "i am in", "i'm in"]:
                pattern = re.escape(marker) + r"\s+(.*?)" + chinese_separators
            else:
                pattern = re.escape(marker) + r"\s*(.*?)" + chinese_separators

            m = re.search(pattern, original_q, re.IGNORECASE | re.DOTALL)
            if m:
                location_candidate = m.group(1)
                if location_candidate:
                    location = location_candidate.strip()
                    if len(location) > 2:
                        break
                else:
                    continue

        # b) 模糊POI提取（支持多语境+分界词）
        # 定义POI相关语境关键词（中英文）+ 结束分界词（匹配到这些词就停止提取POI）
        poi_context_keywords = {
            "zh": ["我要去", "我想去", "想去", "要去", "找", "查找", "附近的", "周边的", "旁边的", "有哪些", "哪里有",
                   "规划去", "附近有", "前往"],
            "en": ["want to go to", "go to", "find", "look for", "nearby", "around", "route to", "navigate to",
                   "drive to", "walk to", "cycle to"]
        }
        poi_stop_keywords = {
            "zh": ["的", "啊", "呀", "呢", "吧", "吗", "，", "。", "！", "？", "、", "；", "路线", "驾车", "步行", "骑行",
                   "方式", "怎么去", "如何到达"],
            "en": ["the", "a", "an", "and", "or", "to", "for", "in", "on", "at", ",", ".", "!", "?", ";", "route",
                   "drive", "walk", "cycle", "way", "how"]
        }

        all_context_keywords = poi_context_keywords["zh"] + poi_context_keywords["en"]
        # 优化1：优先匹配中文分界词，避免英文短词误匹配
        all_stop_keywords = poi_stop_keywords["zh"] + poi_stop_keywords["en"]
        q_lower = original_q.lower()
        poi_candidate = None
        poi = ""  # 初始化poi变量

        for context_kw in all_context_keywords:
            if context_kw in poi_context_keywords["en"]:
                match = re.search(re.escape(context_kw), q_lower, re.IGNORECASE)
            else:
                match = re.search(re.escape(context_kw), original_q)

            if match:
                start_idx = match.end()
                remaining_text = original_q[start_idx:].strip()
                stop_idx = len(remaining_text)

                # 优化2：遍历分界词时，区分中英文，避免跨语言误匹配
                for stop_kw in all_stop_keywords:
                    stop_match = None
                    if stop_kw in poi_stop_keywords["en"]:
                        # 英文分界词只匹配英文语境后的文本，避免匹配中文中的字母
                        if context_kw in poi_context_keywords["en"]:
                            stop_match = re.search(re.escape(stop_kw), remaining_text.lower(), re.IGNORECASE)
                    else:
                        # 中文分界词只匹配中文语境后的文本
                        if context_kw in poi_context_keywords["zh"]:
                            stop_match = re.search(re.escape(stop_kw), remaining_text)

                    if stop_match:
                        current_stop_idx = stop_match.start()
                        # 取最早出现的分界词位置
                        if current_stop_idx < stop_idx:
                            stop_idx = current_stop_idx

                poi_candidate = remaining_text[:stop_idx].strip()
                if len(poi_candidate) >= 2:
                    # 优化3：将提取到的候选POI赋值给poi
                    poi = poi_candidate
                    break  # 找到有效POI就停止

        # 最终兜底：没提取到任何POI时，默认"奶茶店"
        if not poi:
            poi = "奶茶店"

        # c) 优化：识别路线需求 + 三种路线方式（驾车/步行/骑行）
        # 定义路线方式关键词（中英文对应）
        ROUTE_TYPE_MARKERS = {
            "driving": ["驾车", "开车", "drive", "driving"],
            "walking": ["步行", "走路", "walk", "walking"],
            "cycling": ["骑行", "骑车", "自行车", "cycle", "cycling", "bike"],
            "transit": ["公交", "公共交通", "乘车", "乘坐公交", "bus", "transit", "public transport"]
        }

        need_route = False
        # 步骤1：判断是否需要路线
        all_nav_markers = BASE_NAV_MARKERS + [kw for kws in ROUTE_TYPE_MARKERS.values() for kw in kws]
        need_route = any(tag in q_lower or tag in original_q for tag in all_nav_markers)

        # 步骤2：识别具体路线方式（优先级：驾车>步行>骑行，可根据需求调整）
        if need_route:
            for route_type_key, markers in ROUTE_TYPE_MARKERS.items():
                if any(tag in q_lower or tag in original_q for tag in markers):
                    route_type = route_type_key
                    break
            # 兜底：无具体方式时，默认驾车
            if not route_type:
                route_type = "driving"

        # d) 判断是否需要"最近"的POI
        has_nearest = any(tag in q_lower or tag in original_q for tag in NEAREST_MARKERS)

        # 返回值新增 route_type（路线方式），方便后续调用API
        return location, poi, need_route, has_nearest, route_type

    # ----------------------------------------------------------------
    # 主执行入口
    # ----------------------------------------------------------------
    def run(self, question: str):
        location, poi, need_route, has_nearest, route_type = self.parse(question)

        if not location:
            # return "I could not detect your current location."
            error_text = f"I could not detect your current location."
            return self._call_llm(self.build_prompt(question, error_text))

        # 1) 地理编码
        start = self.tools.geocode(location)
        print("Location:", location)
        print("start:", start)
        if not start:
            error_text = f"Could not find the location: {location}"
            return self._call_llm(self.build_prompt(question, error_text))
            # return f"Could not find the location: {location}"

        # # 2) 搜索 POI（支持最近1个或10个）
        print("poi:", poi)

        # 根据has_nearest决定返回数量：True返回1个，False返回最多10个
        poi_objs = self.tools.find_poi(
            start[0],
            start[1],
            keyword=poi,
            return_top_n=1 if has_nearest else 10
        )

        is_nearby_found = len(poi_objs) > 0
        keyword_poi_objs = []
        if not is_nearby_found:
            print(f"⚠️  周边2km未找到{poi}，触发关键词搜索...")
            keyword_poi_objs = self.tools.search_poi_by_keyword(keyword=poi, return_top_n=5)

        # -------------------------------
        # 不需要路线 → 输出POI信息（分场景处理）
        # -------------------------------
        if not need_route:
            # 场景1：周边找到POI（1个或10个）
            if is_nearby_found:
                if has_nearest:
                    # 只返回最近1个（带地址，更实用）
                    poi_text = f"""
        From **{location}**, the nearest **{poi}** is:

        • **Name:** {poi_objs[0]['name']}
        • **Address:** {poi_objs[0].get('address', 'Unknown Address')}
        • **Coordinate:** ({poi_objs[0]['lat']:.6f}, {poi_objs[0]['lon']:.6f})
        • **Distance:** {poi_objs[0]['distance']} meters
                    """.strip()
                else:
                    # 返回最多10个，按距离排序
                    poi_list = []
                    for i, poi_obj in enumerate(poi_objs, 1):
                        poi_list.append(f"""
        {i}. **{poi_obj['name']}**
           - Address: {poi_obj.get('address', 'Unknown Address')}
           - Coordinate: ({poi_obj['lat']:.6f}, {poi_obj['lon']:.6f})
           - Distance: {poi_obj['distance']} meters
                        """.strip())

                    poi_text = f"""
        From **{location}**, here are the nearest 10 **{poi}** locations (sorted by distance):

        {"\n\n".join(poi_list)}
                    """.strip()
                poi_text += "\n\nLet me know if you want directions to any of these places!"

            # 场景2：周边未找到，但关键词搜索到（无距离限制，返回前5个）
            elif keyword_poi_objs:
                poi_list = []
                for i, poi_obj in enumerate(keyword_poi_objs, 1):
                    poi_list.append(f"""
        {i}. **{poi_obj['name']}**
           - Address: {poi_obj.get('address', 'Unknown Address')}
           - City: {poi_obj.get('city', 'Unknown City')}
           - Coordinate: ({poi_obj['lat']:.6f}, {poi_obj['lon']:.6f})
                        """.strip())

                poi_text = f"""
        No {poi} found within 2km of **{location}**, but we found these nationwide results matching "{poi}":

        {"\n\n".join(poi_list)}

        If you want directions to one of them, please provide a more detailed address (e.g., "{poi_obj['name']}, {poi_obj['city']}").
                """.strip()

            # 场景3：周边和关键词搜索都未找到
            else:
                poi_text = f"""
        Sorry, no locations matching "{poi}" were found:
        - No nearby {poi} within 2km of **{location}**
        - No nationwide results for "{poi}" in the database

        Please check if the location name is correct, or provide more details (e.g., "Starbucks Coffee, Shanghai").
                """.strip()

            return self._call_llm(self.build_prompt(question, poi_text))


        # -------------------------------
        # 3) 需要路线：规划路线（只针对最近的POI）
        # -------------------------------
        nearest_poi = None
        route_info = None

        # 场景1：周边找到POI → 用最近的1个规划路线
        if is_nearby_found:
            nearest_poi = poi_objs[0]  # 周边POI已按距离排序，第一个是最近的

        # 场景2：周边未找到，关键词搜索到POI
        elif keyword_poi_objs:
            # 关键词搜索仅1个结果 → 直接用该POI
            if len(keyword_poi_objs) == 1:
                nearest_poi = keyword_poi_objs[0]
            # 关键词搜索多个结果 → 提示用户选择
            else:
                poi_list_text = "\n".join([
                    f"{i}. **{p['name']}** (Address: {p.get('address', 'Unknown')}, City: {p.get('city', 'Unknown')})"
                    for i, p in enumerate(keyword_poi_objs, 1)
                ])
                route_text = f"""
        We found {len(keyword_poi_objs)} results matching "{poi}":

        {poi_list_text}

        To plan your route accurately, please specify which one you want to go to (e.g., "I want to go to {keyword_poi_objs[0]['name']}").
                """.strip()
                return self._call_llm(self.build_prompt(question, route_text))

        # 场景3：所有搜索都未找到POI
        else:
            route_text = f"""
        Sorry, we couldn't find any location matching "{poi}" to plan the route:
        - No nearby {poi} within 2km of **{location}**
        - No nationwide results for "{poi}"

        Please verify the location name or provide a more detailed address (e.g., "McDonald's, Beijing Chaoyang District").
            """.strip()
            return self._call_llm(self.build_prompt(question, route_text))

        # -------------------------------
        # 执行路线规划（仅当确定目标POI后）
        # -------------------------------
        if nearest_poi:
            # 校验POI经纬度有效性
            if nearest_poi['lon'] == 0.0 or nearest_poi['lat'] == 0.0:
                route_text = f"Sorry, we couldn't get the coordinates of {nearest_poi['name']}, so route planning failed."
                return self._call_llm(self.build_prompt(question, route_text))

        end = [nearest_poi["lon"], nearest_poi["lat"]]
        route = self.tools.get_route(start, end, route_type=route_type)  # 传入路线类型

        if not route:
            error_text = f"Route calculation failed."
            return self._call_llm(self.build_prompt(question, error_text))
            # return "Route calculation failed."

        # 映射路线类型为中文（提升可读性）
        route_type_cn = {
            "driving": "驾车",
            "walking": "步行",
            "cycling": "骑行",
            "transit": "公交"
        }.get(route["route_type"], "驾车")

        # 生成详细导航文本（分基础信息 + 步骤指引）
        navigation_text = "\n".join(route["navigation_steps"])
        text = f"""
        【从 {location} 到最近的 {poi}】

        🏪 目的地信息：
        • 名称：{nearest_poi['name']}
        • 坐标：({nearest_poi['lat']:.6f}, {nearest_poi['lon']:.6f})
        • 直线距离：{nearest_poi['distance']} 米

        🚌 出行方式：{route_type_cn}
        📊 路线概览：
        • 总距离：{route['distance_km']} 公里
        • 预计耗时：{route['duration_min']} 分钟
        • 导航步骤：{route['total_steps']} 步

        🧭 详细导航指引：
        {navigation_text}

        💡 提示：路线为实时规划，实际耗时可能受交通/路况影响
        """.strip()

        return self._call_llm(self.build_prompt(question, text))

    # ----------------------------------------------------------------
    # LLM Prompt 构建（适配多POI列表输出）
    # ----------------------------------------------------------------
    def build_prompt(self, user_question: str, info: str) -> str:
        """
        Prompt 输出格式：
        - 自动匹配用户输入语言（中文/英文）
        - 结构化呈现POI列表/导航指引
        - 自然友好，符合日常交流习惯
        """
        return f"""
    Your Role: A helpful, professional map assistant that responds in the SAME LANGUAGE as the user's question.

    User's Question:
    {user_question}

    Raw Map Data (DO NOT modify this data; only use it to generate responses):
    {info}

    Key Instructions:
    1. Language Matching (Critical!):
       - First, detect the user's input language: if it contains Chinese characters (e.g., 我、奶茶店、北京), respond in CHINESE; otherwise, respond in ENGLISH.
       - Use natural, colloquial expressions (avoid rigid formal language; like chatting with a friend).
       - Unit Adaptation: For Chinese responses, use "米" "公里" "分钟"; for English responses, use "meters" "km" "minutes" (keep consistency with the raw data's units).

    2. Response Structure (Clear & Easy to Read):
       A. If the data includes MULTIPLE POIs (e.g., 10 results):
          - For Chinese: Number them as "1. 2. 3. ..."，and include each POI's name, distance, and key location info.
          - For English: List them as "1. 2. 3. ..."，and include each POI's name, distance, and key location details.
          - Highlight the nearest POI (if marked as "nearest") with a brief note (e.g., "👉 最近的：" in Chinese / "👉 Closest: " in English).

       B. If the data includes ONLY ONE POI:
          - Concisely present its name, distance from the user, and basic location.
          - If navigation steps are provided, integrate them smoothly (not just list steps; add logical connections like "首先" "接着" "最后" in Chinese / "First" "Then" "Finally" in English).

       C. If the data includes DIRECTIONS (navigation steps):
          - For Chinese: Simplify complex navigation terms (e.g., "直行500米进入阜通东大街" → "先直行500米，然后进入阜通东大街").
          - For English: Paraphrase rigid step-by-step instructions into natural guidance (e.g., "1. Go straight 500m onto Futong East St" → "First, go straight for 500 meters onto Futong East Street").
          - Keep navigation steps concise but complete (avoid overly technical jargon; e.g., use "右转" instead of "向右转" in Chinese / "turn right" instead of "make a right turn" in English).

    3. Critical Rules (Must Follow!):
       - NEVER invent new information (e.g., fake POIs, distances, navigation steps, or locations not in the raw data).
       - NEVER omit key details (e.g., POI names, distances, estimated time for directions).
       - If the raw data says "Route calculation failed" or "No nearby POIs found", convey the message politely (e.g., "很抱歉，路线计算失败啦～" in Chinese / "Sorry, route calculation failed." in English).
       - Keep the response length appropriate: Not too long (avoid redundant repetition) but not too short (cover all necessary info).

    Example Responses (For Reference Only):
    - Example 1 (Chinese user asking for multiple POIs):
      "根据你的位置（北京市朝阳区阜通东大街6号），附近的奶茶店有这些哦：
      1. coco都可（望京店）- 800米
      2. 蜜雪冰城（清华园店）- 1.2公里
      3. 喜茶（朝阳大悦城店）- 1.5公里
      👉 最近的是coco都可（望京店），步行10分钟就能到～"

    - Example 2 (English user asking for directions):
      "From your location (6 Futong East Street, Chaoyang District), the nearest milk tea shop is Coco (Wangjing Branch), 800 meters away. Here's how to get there on foot:
      First, walk east for 200 meters past Hualian Supermarket. Then, turn left onto Wangjing Street and walk straight for 300 meters. Finally, turn right and walk another 300 meters—you'll find the shop on your left. The total journey takes about 10 minutes."

    Please generate a response that meets all the above requirements!
    """
