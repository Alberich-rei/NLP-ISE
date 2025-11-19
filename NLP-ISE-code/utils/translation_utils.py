"""Utility helpers for translating text via the configured LLM."""
from __future__ import annotations

from typing import Callable

LLMCallable = Callable[[str], str]


def _safe_call(llm: LLMCallable, prompt: str) -> str:
    try:
        return llm(prompt).strip()
    except Exception as exc:  # noqa: BLE001 - we want to surface clean fallback
        return f"Translation error: {exc}"


def translate_to_english(llm: LLMCallable, text: str, source_language: str) -> str:
    """Translate an arbitrary language into English using the LLM."""
    if not text.strip():
        return text

    language = source_language.lower()
    if language == "english":
        return text

    language_label = {
        "cantonese": "Cantonese Chinese",
        "chinese": "Chinese",
    }.get(language, source_language)

    prompt = (
        "You are a precise translator. Translate the following {src} text into natural English. "
        "Return only the translated text without extra commentary.\n\n{text}"
    ).format(src=language_label, text=text)
    result = _safe_call(llm, prompt)
    return result if result else text


def translate_from_english(llm: LLMCallable, text: str, target_language: str) -> str:
    """Translate English text into the configured target language."""
    if not text.strip():
        return text

    language = target_language.lower()
    if language == "english":
        return text

    if language == "cantonese":
        prompt = (
            "Translate the following English text into written Cantonese using Traditional Chinese characters. "
            "Use colloquial Cantonese expressions where appropriate. Return only the translated text."\
        )
    elif language == "chinese":
        prompt = (
            "Translate the following English text into Simplified Chinese suitable for Mainland readers. "
            "Return only the translated text."
        )
    else:
        prompt = (
            "Translate the following English text into {lang}. Return only the translated text.".format(lang=target_language)
        )

    prompt = f"{prompt}\n\n{text}"
    result = _safe_call(llm, prompt)
    return result if result else text
