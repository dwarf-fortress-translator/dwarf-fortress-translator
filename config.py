"""
Configuration management - minimal version
"""

import os
import sys
import json
import logging


def resource_path(rel_path: str) -> str:
    if getattr(sys, "frozen", False):
        base = getattr(sys, "_MEIPASS", os.path.abspath(os.path.dirname(sys.executable)))
    else:
        base = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base, rel_path)


def setup_logging():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)]
    )
    return logging.getLogger("ocr_translator")


SETTINGS_FILE = "settings.json"
DB_FILE = "translations_cache.db"
AUDIO_CACHE_DIR = "audio_cache"
HISTORY_LIMIT = 300

TARGET_LANGUAGES = {
    "ar": "Arabic (العربية)",
    "zh-cn": "Chinese (中文)",
    "cs": "Czech (čeština)",
    "da": "Danish (dansk)",
    "nl": "Dutch (Nederlands)",
    "en": "English",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "hi": "Hindi (हिन्दी)",
    "it": "Italian (Italiano)",
    "ja": "Japanese (日本語)",
    "ko": "Korean (한국어)",
    "no": "Norwegian (norsk)",
    "pl": "Polish (Polski)",
    "pt": "Portuguese (Português)",
    "ru": "Russian (Русский)",
    "es": "Spanish (Español)",
    "sv": "Swedish (svenska)",
    "tr": "Turkish (Türkçe)",
    "uk": "Ukrainian (Українська)",
}

DEFAULT_SETTINGS = {
    "target_lang": "ar",
    "overlay_display_time": 10,
    "ocr_engine": "tesseract",
    "gemini_api_keys": [],
    "gemini_prompt": "Extract text from this game screenshot. Return ONLY the extracted text, nothing else.",
    "show_original_text": True,
    "overlay_width": 500,
    "overlay_max_height": 400,
    "overlay_auto_height": True,
    "batch_file_path": "",
    "overlay_bg_color": "#1e1e1e",
    "overlay_original_color": "#4CAF50",
    "overlay_translated_color": "#2196F3",
    "overlay_border_color": "#444",
    "overlay_alpha": 92,
    "overlay_font_family": "Segoe UI",
    "overlay_font_size": 11,
    "window_width": 1050,
    "window_height": 750,
    "window_x": 50,
    "window_y": 50,
}


def load_settings():
    try:
        if os.path.exists(SETTINGS_FILE):
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = {}
    except Exception as e:
        log = logging.getLogger("ocr_translator")
        log.exception(f"Failed to load settings: {e}")
        data = {}

    settings = DEFAULT_SETTINGS.copy()
    settings.update(data)
    return settings


def save_settings(settings: dict):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
    except Exception:
        log = logging.getLogger("ocr_translator")
        log.exception("Failed to save settings")