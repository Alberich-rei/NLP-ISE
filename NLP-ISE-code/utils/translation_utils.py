"""Utility helpers for translating text via the configured LLM."""

from __future__ import annotations
import config.config as config
import requests

class TranslateModel:
    def __init__(self):
        self.base_url = config.DEEPSEEK_V3_BASE_URL
        self.api_key = config.DEEPSEEK_V3_API_KEY
        self.model_id = config.DEEPSEEK_V3_MODEL
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def translate_text(self, text: str, source_language: str, target_language: str) -> str:
        """
        Use LLM to translate text from source_language to target_language.
        If source and target are相同, return原文.
        """
        prompt = (
            f"You are a professional translator. Translate the following text from {source_language} to {target_language}. "
            f"Return only the translated text without any explanation or extra commentary.\n\n{text}"
        )
        endpoint = f"{self.base_url}/chat/completions"
        
        if not text.strip():
            return text

        src = source_language.strip().lower()
        tgt = target_language.strip().lower()
        if src == tgt:
            return text

        payload = {
            "model": self.model_id,
            "messages": [
                {"role":"system","content":prompt},
                {"role":"user","content":text}
            ],
            "max_tokens": 1000,
            "temperature": 0.7,
        }
        
        try:
            r = requests.post(endpoint, headers=self.headers, json=payload, timeout=20)
            r.raise_for_status()
            data = r.json()
            choices = data.get("choices", [])
            if choices:
                msg = choices[0].get("message") or {}
                return msg.get("content", "")
        except Exception as exc:
            return f"Translation error: {exc}"
