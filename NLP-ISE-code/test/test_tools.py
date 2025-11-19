"""
工具包测试脚本
"""
import sys
import os

# 添加父目录到路径，以便导入工具
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from tools import WeatherTools, FinanceTools, TrafficTools, GeneralTools, RAGTools
    print("所有工具类导入成功！")
    
    # 测试各个工具类
    print("\n测试工具功能：")
    
    # 测试天气工具
    print("\n天气工具测试：")
    weather = WeatherTools()
    print(f"- 空气质量: {weather.get_air_quality('Hong Kong')}")
    print(f"- UV指数: {weather.get_uv_index('Hong Kong')}")
    
    # 测试金融工具
    print("\n金融工具测试：")
    finance = FinanceTools()
    print(f"- 汇率: {finance.get_forex_rate()}")
    print(f"- 市场指数: {finance.get_market_index()}")
    
    # 测试交通工具
    print("\n交通工具测试：")
    traffic = TrafficTools()
    print(f"- MTR状态: {traffic.get_mtr_status()}")
    print(f"- 交通状况: {traffic.get_traffic_conditions()}")
    
    # 测试通用工具
    print("\n通用工具测试：")
    general = GeneralTools()
    print(f"- 问候回复: {general.get_greeting_response('你好')}")
    
    # 测试RAG工具
    print("\nRAG工具测试：")
    rag = RAGTools()
    print(f"- 知识库状态: {rag.check_knowledge_base_status(None)}")
    
    print("\n所有工具测试完成！工具包结构正常。")
    
except ImportError as e:
    print(f"导入错误: {e}")
    print("请检查工具包文件是否正确创建。")
except Exception as e:
    print(f"测试错误: {e}")