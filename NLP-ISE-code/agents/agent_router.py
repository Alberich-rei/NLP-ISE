"""Agent router wiring the specialised agents together."""
from __future__ import annotations

from typing import Any, Dict

from utils.source_selector import select_sources

from .finance_agent import FinanceAgent
from .general_agent import GeneralAgent
from .rag_agent import RAGAgent
from .traffic_agent import TrafficAgent
from .weather_agent import WeatherAgent
from .transport_agent import TransportAgent
from .web_agent import WebAgent


class AgentRouter:
    """Route incoming queries to the appropriate specialist agent."""

    def __init__(self, llm, retriever):
        self.weather_agent = WeatherAgent(llm)
        self.finance_agent = FinanceAgent(llm)
        self.traffic_agent = TrafficAgent(llm)
        self.transport_agent = TransportAgent(llm)
        self.rag_agent = RAGAgent(llm, retriever)
        self.general_agent = GeneralAgent(llm)
        self.web_agent = WebAgent(llm)

    def _classify_intent(self, query: str) -> str:
        """Use the source selector to classify query intent."""
        try:
            result = select_sources(query)
            return result.get("intent", "general")#没有对应分类返回general
        except Exception as exc:  # noqa: BLE001 - want to display a friendly fallback
            print(f"Intent classification error: {exc}")
            return "general"

    def invoke(self, input_data: Dict[str, Any]) -> Dict[str, str]:
        """Process the user input and route to the appropriate agent."""
        user_query = input_data.get("user_query", " ")
        processed_quert = input_data.get("input", "")
        context = input_data.get("context", "")
        has_history = input_data.get("has_history", False)

        if has_history and context:
            enhanced_query = f"Context from previous conversation:\n{context}\n\nCurrent question: {processed_quert}"
        else:
            enhanced_query = processed_quert

        intent = self._classify_intent(processed_quert)
        print(f"Intent detected: {intent}")

        if intent == "weather":
            result = self.weather_agent.run(user_query, enhanced_query)
        elif intent == "finance":
            result = self.finance_agent.run(user_query, enhanced_query)
        elif intent == "traffic":
            result = self.traffic_agent.run(user_query, enhanced_query)
        elif intent == "transport":
            result = self.transport_agent.run(user_query, enhanced_query)
        elif intent == "web":
            result = self.web_agent.run(enhanced_query)
        elif intent == "rag":
            result = self.rag_agent.run(enhanced_query)
        elif intent == "general":
             result = self.general_agent.run(enhanced_query)
        else:
            result = self.general_agent.run(enhanced_query)

        return {"output": result}


def create_tool_agent(llm, retriever) -> AgentRouter:
    """Public factory to assemble the multi-agent router."""
    return AgentRouter(llm, retriever)
