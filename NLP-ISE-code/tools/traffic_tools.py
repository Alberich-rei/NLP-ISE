"""
交通相关工具集
"""


class TrafficTools:
    """交通相关工具集"""
    
    @staticmethod
    def get_mtr_status(line: str = "all") -> str:
        """获取MTR状态"""
        mtr_lines = {
            "all": "所有MTR线路运作正常",
            "tsuen_wan": "荃湾线：正常服务",
            "island": "港岛线：正常服务",
            "kwun_tong": "观塘线：正常服务",
            "tseung_kwan_o": "将军澳线：正常服务",
            "east_rail": "东铁线：正常服务"
        }
        
        return mtr_lines.get(line.lower(), f"MTR {line}线：正常服务")
    
    @staticmethod
    def get_bus_info(route: str = "general") -> str:
        """获取巴士信息"""
        if route == "general":
            return "香港巴士服务：九巴、城巴、新巴均正常运营"
        else:
            return f"巴士路线 {route}：正常服务，预计到站时间5-10分钟"
    
    @staticmethod
    def get_traffic_conditions(area: str = "Hong Kong") -> str:
        """获取道路交通状况"""
        traffic_data = {
            "Hong Kong": "香港岛：交通畅顺",
            "Kowloon": "九龙区：轻微挤塞",
            "New Territories": "新界区：交通正常",
            "Cross Harbour": "过海隧道：轻微挤塞"
        }
        
        return traffic_data.get(area, f"{area}：交通状况正常")
    
    @staticmethod
    def get_parking_info(location: str) -> str:
        """获取停车场信息（模拟）"""
        parking_data = {
            "Central": {"available": 45, "total": 200, "rate": "HK$25/hour"},
            "Causeway Bay": {"available": 12, "total": 150, "rate": "HK$30/hour"},
            "Tsim Sha Tsui": {"available": 28, "total": 180, "rate": "HK$22/hour"},
            "Mong Kok": {"available": 67, "total": 250, "rate": "HK$18/hour"}
        }
        
        data = parking_data.get(location, {"available": 50, "total": 100, "rate": "HK$20/hour"})
        return f"{location}停车场：可用车位 {data['available']}/{data['total']}，收费 {data['rate']}"
    
    @staticmethod
    def get_ferry_schedule(route: str = "Central-TST") -> str:
        """获取渡轮时刻表"""
        ferry_routes = {
            "Central-TST": "中环-尖沙咀：每10-15分钟一班，服务时间 06:30-23:30",
            "Wan Chai-TST": "湾仔-尖沙咀：每15-20分钟一班，服务时间 07:00-23:00",
            "North Point-Hung Hom": "北角-红磡：每20分钟一班，服务时间 06:45-22:30"
        }
        
        return ferry_routes.get(route, f"渡轮路线 {route}：请查询具体时刻表")
    
    @staticmethod
    def get_flight_info(airport: str = "HKG") -> str:
        """获取航班信息（模拟）"""
        airport_info = {
            "HKG": "香港国际机场：航班正常起降，平均延误15分钟，天气良好",
            "PVG": "上海浦东机场：航班正常，轻微延误",
            "PEK": "北京首都机场：受天气影响，部分航班延误",
            "NRT": "东京成田机场：航班正常运行"
        }
        return airport_info.get(airport.upper(), f"{airport}机场：请查询具体航班信息")
        
    @staticmethod
    def get_taxi_info(area: str = "Hong Kong") -> str:
        """获取出租车信息（模拟）"""
        taxi_info = {
            "Hong Kong": "香港岛红色出租车：载客量正常，等待时间5-8分钟",
            "Kowloon": "九龙绿色出租车：服务正常，等待时间3-6分钟",
            "New Territories": "新界红色出租车：载客量较少，等待时间10-15分钟"
        }
        return taxi_info.get(area, f"{area}出租车信息：请查询具体情况")
        
    @staticmethod
    def get_ride_sharing_info() -> str:
        """获取网约车信息（模拟）"""
        return "Uber/Grab: 服务正常，当前等待时间5-12分钟，无特殊加价"