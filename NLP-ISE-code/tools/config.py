"""
工具包配置文件
"""

# 工具导入映射
TOOL_IMPORTS = {
    'weather': 'tools.weather_tools.WeatherTools',
    'finance': 'tools.finance_tools.FinanceTools', 
    'traffic': 'tools.traffic_tools.TrafficTools',
    'general': 'tools.general_tools.GeneralTools',
    'rag': 'tools.rag_tools.RAGTools'
}

# 工具描述
TOOL_DESCRIPTIONS = {
    'weather': '天气查询工具 - 实时天气、预报、台风警告',
    'finance': '金融信息工具 - 股票、汇率、加密货币',
    'traffic': '交通状况工具 - MTR、巴士、道路、停车',
    'general': '通用对话工具 - 问候、能力介绍',
    'rag': '知识库工具 - 文档搜索、内容检索'
}