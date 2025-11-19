"""General conversation agent."""
from __future__ import annotations

from tools import GeneralTools


class GeneralAgent:
    """Agent responsible for general conversation and FAQs."""

    def __init__(self, llm, system_prompt: str | None = None):
        self.llm = llm
        self.name = "GeneralAgent"
        self.tools = GeneralTools()
        self.system_prompt = system_prompt

    def _call_llm(self, prompt: str) -> str:
        if self.system_prompt:
            combined = f"{self.system_prompt}\n\n{prompt}"
        else:
            combined = prompt
        return self.llm(combined)

    def run(self, query: str) -> str:
        """处理一般性对话和问题"""
        query_lower = query.lower()

        # 检查是否是问候语
        if any(greeting in query_lower or greeting in query for greeting in ["你好", "hello", "谢谢", "thank", "再见", "goodbye"]):
            return self.tools.get_greeting_response(query)

        # 检查是否询问系统能力
        if any(
            word in query_lower or word in query
            for word in ["能做什么", "功能", "能力", "what can you do", "capabilities", "help"]
        ):
            return self.tools.get_capability_info()

        return self._call_llm(f"请回答以下问题：{query}")
