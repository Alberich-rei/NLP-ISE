"""
知识库相关工具集
"""
from typing import List


class RAGTools:
    """知识库相关工具集"""
    
    @staticmethod
    def search_documents(retriever, query: str, top_k: int = 5) -> List[str]:
        """搜索文档"""
        if retriever is None:
            return ["知识库不可用"]
        
        try:
            docs = retriever.get_relevant_documents(query)
            return [doc.page_content for doc in docs[:top_k]]
        except Exception as e:
            return [f"搜索失败: {e}"]
    
    @staticmethod
    def get_document_summary(retriever, query: str) -> str:
        """获取文档摘要"""
        docs = RAGTools.search_documents(retriever, query, top_k=3)
        if docs and docs[0] != "知识库不可用":
            return f"找到 {len(docs)} 个相关文档片段"
        return "未找到相关文档"
    
    @staticmethod
    def check_knowledge_base_status(retriever) -> str:
        """检查知识库状态"""
        if retriever is None:
            return "知识库未初始化"
        try:
            # 尝试一个简单的查询来检查状态
            test_docs = retriever.get_relevant_documents("测试")
            return f"知识库运行正常，包含 {len(test_docs)} 个相关文档片段"
        except Exception as e:
            return f"知识库状态异常：{e}"
            
    @staticmethod
    def get_search_suggestions(query: str) -> List[str]:
        """获取搜索建议（模拟）"""
        suggestions = [
            f"{query} 相关概念",
            f"{query} 实现方法",
            f"{query} 最佳实践",
            f"{query} 常见问题",
            f"{query} 案例研究"
        ]
        return suggestions[:3]  # 返回前3个建议
            
    @staticmethod
    def analyze_query_intent(query: str) -> str:
        """分析查询意图（模拟）"""
        query_lower = query.lower()
        if any(word in query_lower for word in ['是什么', 'what is', '定义', 'define']):
            return '概念解释'
        elif any(word in query_lower for word in ['怎么', 'how', '方法', '步骤']):
            return '操作指导'
        elif any(word in query_lower for word in ['为什么', 'why', '原因', '原理']):
            return '原理阐释'
        else:
            return '一般查询'