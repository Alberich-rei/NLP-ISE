"""Traffic agent handling transportation related queries."""
from __future__ import annotations

import re

from tools import TrafficTools


class TrafficAgent:
    """Agent responsible for traffic related questions."""

    def __init__(self, llm, system_prompt: str | None = None):
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

    def run(self, user_query: str, query: str) -> str:
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
            route_pattern = r"\b\d{1,3}[A-Z]?\b"
            matches = re.findall(route_pattern, query)
            route = matches[0] if matches else "general"

            bus_info = self.tools.get_bus_info(route)
            results.append(f"巴士信息：{bus_info}")

        # 道路交通查询
        if any(term in query_lower or term in query for term in ["road", "traffic", "道路", "交通", "挤塞"]):
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
            locations = ["Central", "Causeway Bay", "Tsim Sha Tsui", "Mong Kok"]
            location = "Central"

            for loc in locations:
                if loc.lower() in query_lower:
                    location = loc
                    break

            chinese_locations = {
                "中环": "Central",
                "铜锣湾": "Causeway Bay",
                "尖沙咀": "Tsim Sha Tsui",
                "旺角": "Mong Kok",
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

        if not results:
            general_info = self.tools.get_traffic_conditions()
            results.append(f"交通信息：{general_info}")

        combined_result = "\n\n".join(results)
        prompt = (
            f"Traffic query: {user_query}\nTraffic information:\n{combined_result}\n"
            "Provide a comprehensive traffic response."
        )
        return self._call_llm(prompt)
