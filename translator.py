import logging
from googletrans import Translator
from database import TranslationCache

log = logging.getLogger("ocr_translator")

DF_TERMS = {
    "urist": "urist",
    "dwarf": "dwarf",
    "dwarves": "dwarves",
    "burrow": "burrow",
    "hauling": "hauling",
    "moody": "in a mood",
    "tantrum": "tantrum",
    "melancholy": "melancholy",
    "legendary": "legendary",
    "overseer": "overseer",
    "fortress": "fortress",
    "cavern": "cavern",
    "caverns": "caverns",
    "aquifer": "aquifer",
    "magma": "magma",
    "adamantine": "adamantine",
    "goblin": "goblin",
    "kobold": "kobold",
    "forgotten beast": "forgotten beast",
    "titan": "titan",
    "werebeast": "werebeast",
    "necromancer": "necromancer",
    "stockpile": "stockpile",
    "workshop": "workshop",
}


class WordTranslator:
    """
    Handles translation with two strategies:
      1. Full-phrase via Google Translate (primary)
      2. Word-by-word with SQLite cache (fallback)
    """

    def __init__(self, translator=None, target_lang="uk"):
        self.translator = translator or Translator()
        self.cache = TranslationCache()
        self.punctuation = set('.,!?;:()"\'')
        self.target_lang = target_lang
        log.debug("WordTranslator initialised with target_lang=%s", target_lang)

    def set_target_language(self, lang: str):
        self.target_lang = lang
        log.debug("Target language changed to: %s", lang)

    def get_target_language(self) -> str:
        return self.target_lang

    def _preprocess_df_text(self, text: str) -> str:
        text = text.replace("#", " ")
        text = " ".join(text.split())
        return text

    def translate_text(self, text: str, src: str = "en", dest: str = None) -> str:
        if dest is None:
            dest = self.target_lang

        if src == dest:
            log.debug("Source and target languages are the same, skipping translation")
            return text

        text = self._preprocess_df_text(text)
        if not text.strip():
            return text

        try:
            result = self.translator.translate(text, src=src, dest=dest)
            translated = result.text
            log.debug("Full-phrase translation: %d chars → %d chars", len(text), len(translated))
            return translated
        except Exception:
            log.exception("Full-phrase translation failed, returning original")
            return text

    def translate_phrase(self, text: str, on_word_translated=None):
        preprocessed = self._preprocess_df_text(text)

        try:
            full_translation = self.translate_text(preprocessed, src="auto", dest=self.target_lang)
            if full_translation and full_translation.strip() and full_translation != preprocessed:
                words = self.extract_words(preprocessed)
                self.cache.save_translation(text, full_translation, word_hashes=None)
                log.debug("Used full-phrase translation path")
                return full_translation, words, [full_translation]
        except Exception:
            log.exception("Full-phrase path failed, falling back to word-by-word")

        log.debug("Using word-by-word translation fallback")
        words = self.extract_words(preprocessed)
        translated_words, word_hashes = self.translate_words(words, on_word_translated)

        translated = []
        for i, tw in enumerate(translated_words):
            if tw == " ":
                if 0 < i < len(translated_words) - 1:
                    translated.append(" ")
            elif tw in self.punctuation:
                translated.append(tw)
            else:
                translated.append(tw)

        final_text = "".join(translated)
        self.cache.save_translation(text, final_text, word_hashes)
        return final_text, words, translated_words

    def extract_words(self, text: str):
        words = []
        current_word = []

        for char in text:
            if char.isalnum() or char in ("'", "-"):
                current_word.append(char)
            else:
                if current_word:
                    words.append("".join(current_word))
                    current_word = []
                if char.strip():
                    words.append(char)
                elif char == " " and words and words[-1] != " ":
                    words.append(" ")

        if current_word:
            words.append("".join(current_word))

        return words

    def translate_word(self, word: str):
        if word.strip().lower() == "a":
            return "", None

        if word.strip() and not word.isspace() and word not in self.punctuation:
            cached = self.cache.get_cached_word(word)
            if cached:
                return cached, None
            try:
                translated = self.translator.translate(
                    word, src="en", dest=self.target_lang
                ).text
                self.cache.save_word_translation(word, translated)
                return translated, word
            except Exception:
                log.exception("Failed to translate word '%s'", word)
                return word, None

        return word, None

    def translate_words(self, words, on_word_translated=None):
        from utils import normalize_text, text_hash

        translated_words = []
        word_hashes = []

        for word in words:
            if word.strip().lower() == "a":
                translated_words.append("")
                word_hashes.append(None)
                continue

            if word.strip() and not word.isspace() and word not in self.punctuation:
                cached = self.cache.get_cached_word(word)
                if cached:
                    translated = cached
                else:
                    try:
                        translated = self.translator.translate(
                            word, src="en", dest=self.target_lang
                        ).text
                        self.cache.save_word_translation(word, translated)
                    except Exception:
                        log.exception("Failed to translate word '%s'", word)
                        translated = word

                translated_words.append(translated)
                word_hashes.append(text_hash(normalize_text(word)))

                if on_word_translated:
                    on_word_translated(word, translated)
            else:
                translated_words.append(word)
                word_hashes.append(None)

        return translated_words, word_hashes