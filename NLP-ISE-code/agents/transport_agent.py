# transport_agent.py
from __future__ import annotations
import re
import json
from tools import TransportTools

LOCATION_MARKERS = [
    "当前位置", "在", "位于", "at", "in", "i am at", "i'm at", "i am in", "i'm in"
]
BASE_NAV_MARKERS = ["怎么去", "如何到达", "路线", "导航", "go to", "navigate to", "route to"]
NEAREST_MARKERS = ["最近", "邻近", "最近的", "nearest", "closest", "nearby"]

# # ---------------------- 新增：常见城市库（中英文）----------------------
# COMMON_CITIES = {
#     # 中国主要城市（中文名+拼音+英文缩写）
#     "zh": [
#         "北京", "上海", "广州", "深圳", "杭州", "南京", "成都", "重庆", "武汉", "西安",
#         "天津", "苏州", "郑州", "长沙", "青岛", "宁波", "无锡", "厦门", "大连", "沈阳",
#         "济南", "佛山", "东莞", "福州", "合肥", "昆明", "哈尔滨", "长春", "石家庄", "南宁",
#         "常州", "温州", "嘉兴", "绍兴", "金华", "台州", "泉州", "惠州", "珠海", "中山"
#     ],
#     "en": [
#         "beijing", "shanghai", "guangzhou", "shenzhen", "hangzhou", "nanjing", "chengdu", "chongqing",
#         "wuhan", "xian", "tianjin", "suzhou", "zhengzhou", "changsha", "qingdao", "ningbo", "wuxi",
#         "xiamen", "dalian", "shenyang", "jinan", "foshan", "dongguan", "fuzhou", "hefei", "kunming",
#         "harbin", "changchun", "shijiazhuang", "nanning", "changzhou", "wenzhou", "jiaxing", "shaoxing",
#         "jinhua", "taizhou", "quanzhou", "huizhou", "zhuhai", "zhongshan",
#         # 国际常见城市
#         "new york", "london", "tokyo", "paris", "berlin", "tokyo", "seoul", "hong kong", "singapore"
#     ],
#     # 排除词：容易误判为城市的区县/商圈名
#     "exclude": [
#         "朝阳", "海淀", "丰台", "石景山", "通州", "顺义", "昌平", "大兴", "亦庄", "房山",
#         "门头沟", "怀柔", "平谷", "密云", "延庆",  # 北京区县
#         "浦东", "徐汇", "长宁", "静安", "普陀", "虹口", "杨浦", "闵行", "宝山", "嘉定",
#         "金山", "松江", "青浦", "奉贤", "崇明",  # 上海区县
#         "天河", "越秀", "荔湾", "海珠", "白云", "黄埔", "番禺", "花都", "南沙", "增城",
#         "从化",  # 广州区县
#         "南山", "福田", "罗湖", "盐田", "宝安", "龙岗", "龙华", "坪山", "光明", "大鹏",  # 深圳区县
#         "张江", "陆家嘴", "徐家汇", "五角场", "中关村", "CBD", "科技园", "开发区"
#     ]
# }

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

    def _build_prompt_parse(self, user_query: str) -> str:
        """构建结构化Prompt，引导模型输出标准化JSON（强化格式约束）"""
        prompt_template = """
        你是一个严格的智能出行需求解析助手，仅负责提取关键信息并输出JSON，不添加任何额外文字、解释或注释！
        必须从用户的中英文提问中提取以下6个字段，严格按照指定格式返回：
        1. city: 用户当前所在城市（未提及填null，值为字符串或null）
        2. location: 用户当前所在具体位置（街道/商圈/地标等，未提及填null，值为字符串或null）
        3. poi: 用户想去的目标地点（必须提取，无明确目标时强制填"奶茶店"，值为字符串）
        4. need_route: 是否需要规划路线（是填true，否填false，值为布尔值）
        5. has_nearest: 是否需要找"最近"的目标地点（是填true，否填false，值为布尔值），注意：只有出现”最近“，”最短“等有”最“词汇才是true，否则出现”附近“”周边“什么的都是false
        6. route_type: 出行方式（仅need_route为true时有效，可选值：driving/walking/cycling/transit/null；无明确方式填"driving"，值为字符串）

        解析规则：
        - 中英文混合提问需正确识别（例："I'm in Beijing, want to drive to 故宫" → city=Beijing，poi=故宫，route_type=driving）
        - 含"附近/周边/nearest/around" → has_nearest=true
        - 含"怎么去/如何到达/go to/navigate to" → need_route=true
        - 出行方式优先级：驾车>步行>骑行>公交，无明确方式默认driving

        输出要求：
        - 仅返回JSON字符串，无其他内容（包括无代码块标记、无说明文字）
        - 字段名严格一致（小写，如"city"而非"City"）
        - 布尔值用true/false（小写），字符串用双引号，null无引号
        - 示例格式（必须完全遵循）：
        {{
            "city": "上海",
            "location": "虹桥火车站",
            "poi": "东方明珠",
            "need_route": true,
            "has_nearest": false,
            "route_type": "driving"
        }}

        用户提问：{user_query}
        """
        return prompt_template.format(user_query=user_query.strip())

    def _parse_llm_json(self, llm_output: str) -> dict:
        """解析LLM输出的JSON字符串，处理格式异常"""
        try:
            # 清理LLM输出的干扰字符（如代码块标记、多余空格、注释）
            cleaned_output = llm_output.strip()
            # 去除可能的代码块标记（```json 或 ```）
            if cleaned_output.startswith("```"):
                cleaned_output = cleaned_output.split("```")[1].strip()
                if cleaned_output.startswith("json"):
                    cleaned_output = cleaned_output[4:].strip()
            # 去除多余逗号（LLM常犯的错误）
            cleaned_output = re.sub(r",\s*}", "}", cleaned_output)
            cleaned_output = re.sub(r",\s*]", "]", cleaned_output)
            # 解析JSON
            return json.loads(cleaned_output)
        except json.JSONDecodeError as e:
            print(f"LLM输出JSON解析失败：{e}，原始输出：{llm_output}")
            return {}
        except Exception as e:
            print(f"解析LLM结果异常：{e}")
            return {}

    def parse(self, q: str):
        """
        对外暴露的解析接口
        :param q: 用户提问字符串
        :return: (city, location, poi, need_route, has_nearest, route_type)
        """
        # 1. 构建Prompt（强化格式约束）
        prompt = self._build_prompt_parse(q)
        # 2. 调用大模型（获取字符串输出）
        llm_output = self._call_llm(prompt)
        # 3. 解析JSON字符串（处理格式异常）
        result = self._parse_llm_json(llm_output)
        # 4. 提取字段+兜底默认值（确保不报错）
        city = result.get("city")  # 允许为null
        location = result.get("location")  # 允许为null
        # poi必须有值，兜底"奶茶店"
        poi = result.get("poi", "奶茶店") if result.get("poi") is not None else "奶茶店"
        # 布尔值兜底false
        need_route = bool(result.get("need_route", False))
        has_nearest = bool(result.get("has_nearest", False))

        # d) 判断是否需要"最近"的POI，用强制性关键词覆盖甄别，ai大模型甄别模糊，经常出错
        q_lower = q.lower()
        original_q = q.strip()  # 去除首尾空格，避免干扰
        has_nearest = any(tag in q_lower or tag in original_q for tag in NEAREST_MARKERS)

        # 出行方式校验+兜底
        valid_route_types = ["driving", "walking", "cycling", "transit"]
        route_type = result.get("route_type", "driving")
        route_type = route_type if route_type in valid_route_types else "driving"

        # 5. 最终格式校准（避免None和字符串"null"混淆）
        city = city if city not in [None, "null"] else None
        location = location if location not in [None, "null"] else None

        return city, location, poi, need_route, has_nearest, route_type

    # def extract_city(text: str, text_lower: str) -> str:
    #     """从文本中提取城市（支持中英文）"""
    #     # 1. 优先匹配英文城市（不区分大小写）
    #     for en_city in COMMON_CITIES["en"]:
    #         # 匹配完整单词（避免部分匹配，如"shanghai"不匹配"shanghai road"中的"shanghai"）
    #         pattern = r"\b" + re.escape(en_city) + r"\b"
    #         if re.search(pattern, text_lower):
    #             # 还原城市名首字母大写（如"shanghai"→"Shanghai"）
    #             return en_city.capitalize()
    #
    #     # 2. 匹配中文城市（排除区县/商圈干扰）
    #     for zh_city in COMMON_CITIES["zh"]:
    #         if zh_city in text:
    #             # 检查是否为干扰词的一部分（如"朝阳区"中的"朝阳"不应该匹配）
    #             is_exclude = False
    #             for exclude in COMMON_CITIES["exclude"]:
    #                 if zh_city in exclude or exclude in zh_city:
    #                     is_exclude = True
    #                     break
    #             if not is_exclude:
    #                 return zh_city
    #
    #     return None
    #
    # # 1. 解析英文提问 + 中英文关键词体系（新增has_nearest识别）
    # def parse(self, q: str):
    #     q_lower = q.lower()
    #     original_q = q.strip()  # 去除首尾空格，避免干扰
    #     location = None
    #     poi = None
    #     nead_route = False
    #     has_nearest = False
    #     route_type = None  # 新增：路线类型（driving/walking/cycling/None）
    #     city = None  # 新增：当前所在城市
    #
    #     # a) 位置提取
    #     chinese_separators = r"(?:,|，|。|！|？|、|；|\s|附近|周边|旁边|有哪些|在哪里|怎么去|如何到达|找|求)"
    #     for marker in LOCATION_MARKERS:
    #         if marker in ["i am at", "i'm at", "i am in", "i'm in"]:
    #             pattern = re.escape(marker) + r"\s+(.*?)" + chinese_separators
    #         else:
    #             pattern = re.escape(marker) + r"\s*(.*?)" + chinese_separators
    #
    #         m = re.search(pattern, original_q, re.IGNORECASE | re.DOTALL)
    #         if m:
    #             location_candidate = m.group(1)
    #             if location_candidate:
    #                 location = location_candidate.strip()
    #                 if len(location) > 2:
    #                     break
    #             else:
    #                 continue
    #
    #     # 步骤1：从已提取的location中提取城市
    #     if location:
    #         city = self.extract_city(location, location.lower())
    #     # 步骤2：如果location中没有城市，直接从原始提问中提取
    #     if not city:
    #         city = self.extract_city(original_q, q_lower)
    #
    #     # b) 模糊POI提取（支持多语境+分界词）
    #     # 定义POI相关语境关键词（中英文）+ 结束分界词（匹配到这些词就停止提取POI）
    #     poi_context_keywords = {
    #         "zh": ["我要去", "我想去", "想去", "要去", "找", "查找", "附近的", "周边的", "旁边的", "有哪些", "哪里有",
    #                "规划去", "附近有", "前往"],
    #         "en": ["want to go to", "go to", "find", "look for", "nearby", "around", "route to", "navigate to",
    #                "drive to", "walk to", "cycle to"]
    #     }
    #     poi_stop_keywords = {
    #         "zh": ["的", "啊", "呀", "呢", "吧", "吗", "，", "。", "！", "？", "、", "；", "路线", "驾车", "步行", "骑行",
    #                "方式", "怎么去", "如何到达"],
    #         "en": ["the", "a", "an", "and", "or", "to", "for", "in", "on", "at", ",", ".", "!", "?", ";", "route",
    #                "drive", "walk", "cycle", "way", "how"]
    #     }
    #
    #     all_context_keywords = poi_context_keywords["zh"] + poi_context_keywords["en"]
    #     # 优化1：优先匹配中文分界词，避免英文短词误匹配
    #     all_stop_keywords = poi_stop_keywords["zh"] + poi_stop_keywords["en"]
    #     q_lower = original_q.lower()
    #     poi_candidate = None
    #     poi = ""  # 初始化poi变量
    #
    #     for context_kw in all_context_keywords:
    #         if context_kw in poi_context_keywords["en"]:
    #             match = re.search(re.escape(context_kw), q_lower, re.IGNORECASE)
    #         else:
    #             match = re.search(re.escape(context_kw), original_q)
    #
    #         if match:
    #             start_idx = match.end()
    #             remaining_text = original_q[start_idx:].strip()
    #             stop_idx = len(remaining_text)
    #
    #             # 优化2：遍历分界词时，区分中英文，避免跨语言误匹配
    #             for stop_kw in all_stop_keywords:
    #                 stop_match = None
    #                 if stop_kw in poi_stop_keywords["en"]:
    #                     # 英文分界词只匹配英文语境后的文本，避免匹配中文中的字母
    #                     if context_kw in poi_context_keywords["en"]:
    #                         stop_match = re.search(re.escape(stop_kw), remaining_text.lower(), re.IGNORECASE)
    #                 else:
    #                     # 中文分界词只匹配中文语境后的文本
    #                     if context_kw in poi_context_keywords["zh"]:
    #                         stop_match = re.search(re.escape(stop_kw), remaining_text)
    #
    #                 if stop_match:
    #                     current_stop_idx = stop_match.start()
    #                     # 取最早出现的分界词位置
    #                     if current_stop_idx < stop_idx:
    #                         stop_idx = current_stop_idx
    #
    #             poi_candidate = remaining_text[:stop_idx].strip()
    #             if len(poi_candidate) >= 2:
    #                 # 优化3：将提取到的候选POI赋值给poi
    #                 poi = poi_candidate
    #                 break  # 找到有效POI就停止
    #
    #     # 最终兜底：没提取到任何POI时，默认"奶茶店"
    #     if not poi:
    #         poi = "奶茶店"
    #
    #     # c) 优化：识别路线需求 + 三种路线方式（驾车/步行/骑行）
    #     # 定义路线方式关键词（中英文对应）
    #     ROUTE_TYPE_MARKERS = {
    #         "driving": ["驾车", "开车", "drive", "driving"],
    #         "walking": ["步行", "走路", "walk", "walking"],
    #         "cycling": ["骑行", "骑车", "自行车", "cycle", "cycling", "bike"],
    #         "transit": ["公交", "公共交通", "乘车", "乘坐公交", "bus", "transit", "public transport"]
    #     }
    #
    #     need_route = False
    #     # 步骤1：判断是否需要路线
    #     all_nav_markers = BASE_NAV_MARKERS + [kw for kws in ROUTE_TYPE_MARKERS.values() for kw in kws]
    #     need_route = any(tag in q_lower or tag in original_q for tag in all_nav_markers)
    #
    #     # 步骤2：识别具体路线方式（优先级：驾车>步行>骑行，可根据需求调整）
    #     if need_route:
    #         for route_type_key, markers in ROUTE_TYPE_MARKERS.items():
    #             if any(tag in q_lower or tag in original_q for tag in markers):
    #                 route_type = route_type_key
    #                 break
    #         # 兜底：无具体方式时，默认驾车
    #         if not route_type:
    #             route_type = "driving"
    #
    #     # d) 判断是否需要"最近"的POI
    #     has_nearest = any(tag in q_lower or tag in original_q for tag in NEAREST_MARKERS)
    #
    #     # 返回值新增 route_type（路线方式），方便后续调用API
    #     return location, poi, need_route, has_nearest, route_type

    # ----------------------------------------------------------------
    # 主执行入口
    # ----------------------------------------------------------------
    def run(self, question: str):
        city, location, poi, need_route, has_nearest, route_type = self.parse(question)

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
            city=city,
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
            nearest_poi = keyword_poi_objs[0]

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
