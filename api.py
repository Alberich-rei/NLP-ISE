
import requests, os

class HKGAIClient:
    def __init__(self):
        self.base_url = os.getenv("HKGAI_BASE_URL", "https://oneapi.hkgai.net/v1")
        self.api_key = os.getenv("HKGAI_API_KEY", "sk-iqA1pjC48rpFXdkU7cCaE3BfBc9145B4BfCbEe0912126646")
        self.model_id = os.getenv("HKGAI_MODEL", "HKGAI-V1")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def chat(self, system_prompt, user_prompt, max_tokens=500, temperature=0.7):
        endpoint = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model_id,
            "messages": [
                {"role":"system","content":system_prompt},
                {"role":"user","content":user_prompt}
            ],
            "max_tokens": max_tokens,
            "temperature": temperature
        }

        try:
            r = requests.post(endpoint, headers=self.headers, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message") or {}
                return msg.get("content", "")
            return ""
        except Exception as e:
            return f"[API Error] {e}"
