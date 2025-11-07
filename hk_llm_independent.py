from api import HKGAIClient


class HKGAIModel:
    """针对测试集优化的 LLM 包装器"""

    def __init__(self, system_prompt=None):
        self.client = HKGAIClient()

        # 针对测试集的优化系统提示
        self.system_prompt = system_prompt or """
        你是一个专门为香港和通用知识问答设计的智能助手。

        请遵循以下原则：
        1. 提供准确、简洁的答案
        2. 对于数学计算，直接给出计算结果
        3. 对于事实性问题，提供明确的答案
        4. 对于流程性问题，给出清晰的步骤说明
        5. 如果涉及香港本地信息，确保答案符合香港实际情况

        使用语言：根据用户问题的语言选择回复语言。
        """

    def __call__(self, prompt):
        return self.client.chat(self.system_prompt, prompt)

    def _call(self, prompt, **kwargs):
        return self.client.chat(self.system_prompt, prompt)