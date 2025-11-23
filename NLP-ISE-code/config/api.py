
import requests
import os
import config.config as config

class HKGAIClient:
    def __init__(self):
        self.base_url = config.DEEPSEEK_V3_BASE_URL
        self.api_key = config.DEEPSEEK_V3_API_KEY
        self.model_id = config.DEEPSEEK_V3_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, system_prompt, user_prompt, max_tokens=1000, temperature=0.7):
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": [
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        try:
            r = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message") or {}
                return msg.get("content", "")
            return ""
        except Exception as e:
            return f"[API Error] {e}"
