import datetime
from typing import Optional

class ConversationContext:
    def __init__(self, max_history=10):
        self.history = []
        self.max_history = max_history
    
    def add_exchange(self, user_input: str, agent_output: str, user_en: str = None, assistant_en: str = None, duration_seconds: Optional[float] = None):
        """Add one QA exchange to history. Optionally include processing duration in seconds."""
        user_en = user_en if user_en is not None else user_input
        assistant_en = assistant_en if assistant_en is not None else agent_output
        entry = {
            "user": user_input,
            "assistant": agent_output,
            "user_en": user_en,
            "assistant_en": assistant_en,
            "timestamp": datetime.datetime.now().isoformat()
        }
        if duration_seconds is not None:
            entry["duration_seconds"] = float(duration_seconds)
        self.history.append(entry)
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_context_for_agent(self, use_english: bool = True) -> str:
        if not self.history:
            return ""
        recent_history = self.history[-3:]
        context_parts = []
        user_key = "user_en" if use_english else "user"
        assistant_key = "assistant_en" if use_english else "assistant"
        for i, exchange in enumerate(recent_history, 1):
            user_text = exchange.get(user_key) or exchange.get("user")
            assistant_text = exchange.get(assistant_key) or exchange.get("assistant")
            context_parts.append(f"Previous Q{i}: {user_text}")
            snippet = assistant_text if assistant_text is not None else ""
            context_parts.append(f"Previous A{i}: {snippet[:200]}...")
        return "\n".join(context_parts) if context_parts else ""
    
    def get_history_summary(self) -> str:
        if not self.history:
            return "No conversation history."
        avg = self.get_average_response_time()
        avg_part = f", avg response: {avg:.3f}s" if avg is not None else ""
        return f"Conversation history: {len(self.history)} exchanges, last update: {self.history[-1]['timestamp'][:19]}{avg_part}"

    def get_average_response_time(self) -> Optional[float]:
        """Compute average duration (seconds) for exchanges that recorded duration."""
        times = [e.get("duration_seconds") for e in self.history if e.get("duration_seconds") is not None]
        if not times:
            return None
        return sum(times) / len(times)
    
    def clear_history(self):
        self.history = []
        print("Conversation history cleared.")
