"""
通用对话工具集
"""


class GeneralTools:
    """通用对话工具集"""
    
    @staticmethod
    def get_greeting_response(query: str) -> str:
        """生成问候回复"""
        greetings = {
            "你好": "你好！我是你的AI助手，有什么可以帮助你的吗？",
            "hello": "Hello! I'm your AI assistant. How can I help you today?",
            "谢谢": "不客气！很高兴能帮到你。还有其他需要帮助的吗？",
            "thank": "You're welcome! Happy to help. Is there anything else you need?",
            "再见": "再见！祝你有美好的一天！",
            "goodbye": "Goodbye! Feel free to come back anytime. Have a great day!"
        }
        
        query_lower = query.lower()
        for key, response in greetings.items():
            if key in query_lower or key in query:
                return response
        return "我在这里帮助你，请告诉我你需要什么。"
    
    @staticmethod
    def get_capability_info() -> str:
        """返回系统能力介绍"""
        return """我的能力包括：
    天气查询 - 实时天气、预报、热带气旋警告
    金融信息 - 股票价格、汇率、加密货币、市场指数
    交通状况 - MTR、巴士、道路交通、停车场信息
    知识查询 - 本地文档搜索、专业知识解答
    通用对话 - 日常问答、信息查询、对话交流

    你可以直接问我任何问题！"""