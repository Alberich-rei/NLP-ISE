"""Language preference storage for the ISE system."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict

SUPPORTED_LANGUAGES: Dict[str, str] = {
    "english": "English",
    "cantonese": "粵語",
    "chinese": "中文",
}

_DEFAULT_LANGUAGE = "english"
_CONFIG_FILENAME = "language_pref.json"
_CONFIG_PATH = Path(__file__).resolve().parent / _CONFIG_FILENAME


def _ensure_config_dir() -> None:
    _CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_language_preference() -> str:
    """Return the persisted language preference (default: English)."""
    try:
        if _CONFIG_PATH.is_file():
            with _CONFIG_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
                lang = str(data.get("language", _DEFAULT_LANGUAGE)).lower()
                if lang in SUPPORTED_LANGUAGES:
                    return lang
    except (OSError, json.JSONDecodeError):
        pass
    return _DEFAULT_LANGUAGE


def set_language_preference(language: str) -> None:
    """Persist the chosen language preference."""
    language_key = language.lower()
    if language_key not in SUPPORTED_LANGUAGES:
        raise ValueError(f"Unsupported language '{language}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}")

    _ensure_config_dir()
    try:
        with _CONFIG_PATH.open("w", encoding="utf-8") as fh:
            json.dump({"language": language_key}, fh, ensure_ascii=False, indent=2)
    except OSError as exc:
        raise RuntimeError(f"无法写入语言配置文件: {exc}") from exc


def describe_supported_languages() -> str:
    """Human readable listing of available language modes."""
    items = [f"- {key}: {label}" for key, label in SUPPORTED_LANGUAGES.items()]
    return "\n".join(items)
