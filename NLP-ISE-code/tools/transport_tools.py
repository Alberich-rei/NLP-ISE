# # transport_tools.py
import requests
import re
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_fixed

# --------------------------
# 高德地图 API 配置（替换为你的 Key）
# --------------------------
AMAP_API_KEY = "889ac99c9fdbcf19d899c34b26adddd9"  # 替换成你申请的 Key
AMAP_GEOCODE_URL = "https://restapi.amap.com/v3/geocode/geo"  # 地理编码（地址→经纬度）
AMAP_POI_SEARCH_URL = "https://restapi.amap.com/v3/place/around"  # 周边 POI 搜索
AMAP_ROUTE_URL = "https://restapi.amap.com/v3/direction/driving"  # 驾车路线规划
AMAP_POI_KEYWORD_URL = "https://restapi.amap.com/v3/place/text"  # 关键词 POI 搜索

class TransportTools:
    """
    基于高德地图 API 实现：
    1. 地理编码（地址→经纬度）
    2. 周边 POI 搜索（支持类型/店名搜索）
    3. 驾车路线规划
    """

    # -----------------------------
    # 1. 地理编码（地址→经纬度）
    # -----------------------------
    def geocode(self, address: str):
        """高德地理编码 API：返回 (lon, lat)"""
        params = {
            "key": AMAP_API_KEY,
            "address": address,
            # "city": "北京",  # 可选：限定城市，提高精度（你的场景是清华大学，限定北京）
            "output": "json"
        }
        try:
            r = requests.get(AMAP_GEOCODE_URL, params=params, timeout=8)
            r.raise_for_status()
            data = r.json()

            # 解析结果（高德返回的格式："locations": "116.31575,39.99596"）
            if data["status"] == "1" and len(data["geocodes"]) > 0:
                lon, lat = data["geocodes"][0]["location"].split(",")
                return float(lon), float(lat)
            else:
                print(f"❌ 地理编码失败：{data.get('info', '无错误信息')}")
                return None
        except Exception as e:
            print(f"❌ 地理编码错误：{e}")
            return None

    # -----------------------------
    # 2 POI 搜索（核心：调用高德周边搜索 API）
    # -----------------------------
    def find_poi(self, lon: float, lat: float, keyword: str, city: str, return_top_n: int = 1):
        print(f"\n===== POI 搜索调试 =====")
        print(f"输入参数：lon={lon}, lat={lat}, keyword={keyword}, return_top_n={return_top_n}")

        # --------------------------
        # 调用高德周边 POI 搜索 API
        # --------------------------
        params = {
            "key": AMAP_API_KEY,
            "location": f"{lon},{lat}",  # 中心点经纬度
            "keywords": keyword,  # 搜索关键词（中文优先）
            "city": city,  # 限定城市（提高准确度）
            "radius": 2000,  # 搜索半径2公里（和之前一致）
            "offset": 20,  # 每页记录数据
            "page": 1,  # 第1页（免费版最多10页，这里取第1页足够）
            "output": "json",
            "sortrule": "distance"  # 按距离排序（高德直接支持，无需本地排序）
        }

        try:
            print(f"高德 API 请求参数：{params}")
            r = requests.get(AMAP_POI_SEARCH_URL, params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            # 解析高德返回的POI数据
            if data["status"] != "1":
                print(f"❌ POI 搜索失败：{data.get('info', '无错误信息')}")
                return None

            pois = data.get("pois", [])
            print(f"高德 API 返回原始 POI 数量：{len(pois)}")

            # 整理结果（适配之前的格式）
            result = []
            for poi in pois[:return_top_n]:
                result.append({
                    "name": poi.get("name", "Unnamed POI"),
                    "lon": float(poi.get("location", "").split(",")[0]) if poi.get("location") else lon,
                    "lat": float(poi.get("location", "").split(",")[1]) if poi.get("location") else lat,
                    "distance": int(poi.get("distance", 0))  # 高德直接返回距离（米）
                })

            # 打印最终结果
            print(f"最终返回 POI 数量：{len(result)}")
            for i, poi in enumerate(result):
                print(f"  结果 {i+1}：{poi}")
            print("========================\n")

            return result

        except Exception as e:
            print(f"❌ POI 搜索错误：{e}")
            import traceback
            traceback.print_exc()
            return None

    # -----------------------------
    # 3. 关键词POI搜索（无距离限制,非周边搜索）
    # -----------------------------
    def search_poi_by_keyword(self, keyword: str, city: str = "全国", return_top_n: int = 5) -> List[Dict]:
        """关键词搜索POI（不受距离限制，支持全国/指定城市）"""
        params = {
            "key": AMAP_API_KEY,
            "keywords": keyword,
            "city": city,  # 可指定城市（如"北京"），默认全国
            "offset": return_top_n,
            "page": 1,
            "output": "json",
            "extensions": "base"  # 返回基础信息（名称、地址、经纬度）
        }
        try:
            r = requests.get(AMAP_POI_KEYWORD_URL, params=params, timeout=20)
            r.raise_for_status()
            data = r.json()
            if data["status"] == "1" and int(data["count"]) > 0:
                pois = data["pois"][:return_top_n]
                # 格式化返回结果（包含name、address、经纬度）
                return [
                    {
                        "name": poi.get("name", "Unknown Name"),
                        "lon": float(poi.get("location", "").split(",")[0]) if poi.get("location") else 0.0,
                        "lat": float(poi.get("location", "").split(",")[1]) if poi.get("location") else 0.0,
                        "address": poi.get("address", "Unknown Address"),
                        "city": poi.get("cityname", "Unknown City")
                    }
                    for poi in pois
                ]
            return []
        except Exception as e:
            print(f"❌ 关键词POI搜索错误：{e}")
            return []

    # -----------------------------
    # 4. 路线规划（调用高德路线规划 API，支持4种方式+详细导航）
    # -----------------------------
    def get_route(self, start, end, route_type="driving"):
        """
        start/end：(lon, lat) 格式
        route_type：driving（驾车）/ walking（步行）/ cycling（骑行）/ transit（公交）
        返回：含详细导航指引的路线信息，或 None
        """
        # 1. 配置不同出行方式的 API 地址和参数
        route_config = {
            "driving": {
                "url": "https://restapi.amap.com/v3/direction/driving",
                "strategy": 0,  # 最快路线
                "steps_key": "steps"  # 导航步骤字段名
            },
            "walking": {
                "url": "https://restapi.amap.com/v3/direction/walking",
                "strategy": 11,  # 最短距离
                "steps_key": "steps"
            },
            "cycling": {
                "url": "https://restapi.amap.com/v3/direction/bicycling",
                "strategy": 13,  # 最快路线（骑行）
                "steps_key": "steps"
            },
            "transit": {
                "url": "https://restapi.amap.com/v3/direction/transit/integrated",
                "city": "北京",  # 公交默认城市（可根据位置动态调整）
                "strategy": 0,  # 最快捷公交
                "steps_key": "segments"  # 公交路段字段名（和其他方式不同）
            }
        }

        # 校验路线类型，默认驾车
        if route_type not in route_config:
            route_type = "driving"
        config = route_config[route_type]

        # 2. 构建请求参数
        params = {
            "key": AMAP_API_KEY,
            "origin": f"{start[0]},{start[1]}",
            "destination": f"{end[0]},{end[1]}",
            "output": "json",
            "strategy": config["strategy"],
            "show_steps": "true"  # 关键：请求返回详细导航步骤
        }
        # 公交额外参数（必填）
        if route_type == "transit":
            params["city"] = config["city"]
            params["cityd"] = config["city"]  # 起点和终点同市（可扩展跨市）

        try:
            r = requests.get(config["url"], params=params, timeout=15)
            r.raise_for_status()
            data = r.json()

            # 3. 解析基础路线信息（距离、时长）
            if data["status"] != "1" or len(data["route"]["paths"]) == 0:
                print(f"❌ 路线规划失败：{data.get('info', '无错误信息')}")
                return None

            path = data["route"]["paths"][0]
            duration_seconds = int(path.get("duration", 0))
            distance_meters = int(path.get("distance", 0))
            duration_min = duration_seconds // 60
            distance_km = round(distance_meters / 1000, 2)

            # 4. 解析详细导航指引（核心：按出行方式格式化步骤）
            navigation_steps = []
            steps = path.get(config["steps_key"], [])

            if route_type in ["driving", "cycling"]:
                # 驾车/骑行：转向 + 道路名称 + 距离
                for idx, step in enumerate(steps, 1):
                    action = step.get("action", "继续行驶")  # 转向动作（左转、右转、直行）
                    road = step.get("road", "无名道路")  # 道路名称
                    distance = step.get("distance", 0)  # 该步骤距离（米）
                    # 格式化步骤（比如：1. 直行500米，进入阜通东大街）
                    step_text = f"{idx}. {action}{distance}米，进入{road}"
                    navigation_steps.append(step_text)

            elif route_type == "walking":
                # 步行：方向 + 描述 + 距离
                for idx, step in enumerate(steps, 1):
                    direction = step.get("direction", "向前")  # 方向（向东、向西北）
                    instruction = step.get("instruction", "步行")  # 动作描述
                    distance = step.get("distance", 0)  # 步长（米）
                    # 格式化步骤（比如：1. 向东步行300米，经过华联超市）
                    step_text = f"{idx}. {direction}{instruction}{distance}米"
                    navigation_steps.append(step_text)

            elif route_type == "transit":
                # 公交：线路 + 站点（上/下） + 换乘提示
                for idx, segment in enumerate(steps, 1):
                    seg_type = segment.get("type", "")  # 路段类型（bus地铁、walk步行）
                    if seg_type == "bus":
                        # 公交路段：线路名称 + 上车站点 + 下车站点 + 站数
                        line_name = segment.get("busline", {}).get("name", "未知线路")
                        depart_stop = segment.get("busline", {}).get("departure_stop", {}).get("name", "未知站点")
                        arrive_stop = segment.get("busline", {}).get("arrival_stop", {}).get("name", "未知站点")
                        stop_num = segment.get("busline", {}).get("stop_num", 0)  # 站数
                        step_text = f"{idx}. 乘坐{line_name}（{depart_stop}→{arrive_stop}），共{stop_num}站"
                    elif seg_type == "walk":
                        # 步行换乘：距离 + 方向
                        distance = segment.get("distance", 0)
                        direction = segment.get("direction", "步行")
                        step_text = f"{idx}. {direction}前往{depart_stop if 'depart_stop' in locals() else '下一站'}，步行{distance}米"
                    else:
                        step_text = f"{idx}. 步行{segment.get('distance', 0)}米"
                    navigation_steps.append(step_text)

            # 5. 组装最终返回结果
            return {
                "route_type": route_type,
                "distance_km": distance_km,
                "duration_min": duration_min,
                "navigation_steps": navigation_steps,  # 详细导航步骤
                "total_steps": len(navigation_steps)  # 总步骤数
            }

        except Exception as e:
            print(f"❌ 路线规划错误：{e}")
            return None