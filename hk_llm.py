from langchain_core.language_models.llms import LLM
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from typing import Optional, List, Any
from api import HKGAIClient


class HKGAIModel(LLM):
    # 在类级别定义所有字段
    client: Any = None
    system_prompt: str = "You are a helpful assistant."

    def __init__(self, system_prompt: str = "You are a helpful assistant.", **kwargs):
        # 在调用父类初始化之前设置字段
        super().__init__(**kwargs)
        self.client = HKGAIClient()
        self.system_prompt = system_prompt

    @property
    def _llm_type(self) -> str:
        return "hkgaiv1"

    def _call(
            self,
            prompt: str,
            stop: Optional[List[str]] = None,
            run_manager: Optional[CallbackManagerForLLMRun] = None,
            **kwargs: Any,
    ) -> str:
        result = self.client.chat(self.system_prompt, prompt)
        return result