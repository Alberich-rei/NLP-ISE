"""RAG agent leveraging the local knowledge base."""
from __future__ import annotations

from utils.reranker import rerank
from tools import RAGTools


class RAGAgent:
    """Agent responsible for knowledge base retrieval and synthesis."""

    def __init__(self, llm, retriever, system_prompt: str | None = None):
        self.llm = llm
        self.retriever = retriever
        self.name = "RAGAgent"
        self.tools = RAGTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)

    def run(self, query: str, fallback_to_llm: bool = False) -> str:
        status = self.tools.check_knowledge_base_status(self.retriever)
        if "未初始化" in status:
            if fallback_to_llm:
                return self._call_llm(f"请回答以下问题：{query}")
            return "知识库系统不可用，请先初始化RAG系统。"

        docs_content = self.tools.search_documents(self.retriever, query, top_k=5)

        if not docs_content or docs_content[0] == "知识库不可用":
            if fallback_to_llm:
                return self._call_llm(f"请回答以下问题：{query}")
            return self._call_llm(f"我没有找到关于'{query}'的相关信息。请尝试其他问题或检查知识库内容。")

        try:
            docs = self.retriever.get_relevant_documents(query)
            if docs:
                reranked = rerank(query, docs)[:5]
                context = "\n---\n".join([doc.page_content for doc in reranked])
            else:
                context = "\n---\n".join(docs_content)
        except Exception:
            context = "\n---\n".join(docs_content)

        summary = self.tools.get_document_summary(self.retriever, query)

        prompt = f"""基于以下知识库内容回答问题。如果基于提供的内容无法回答问题，请明确说明。

知识库状态：{summary}

相关内容：
{context}

Question: {query}

Answer:"""
        return self._call_llm(prompt)
