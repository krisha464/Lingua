# utils/translator.py
"""
Simple translator helper.
Primary backend: deep-translator (GoogleTranslator).
If transformers are installed later, you can extend to use Marian/M2M models.
"""

from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0

from deep_translator import GoogleTranslator

def detect_language(text: str) -> str:
    """Return BCP-47-ish language code detected for the text (e.g. 'en', 'hi')."""
    try:
        return detect(text)
    except Exception:
        return "unknown"

def translate_with_deep_translator(text: str, target: str = "en") -> str:
    """Translate using deep-translator's Google Translator (simple & reliable)."""
    return GoogleTranslator(source="auto", target=target).translate(text)

def detect_and_translate(text: str, target: str = "en"):
    """
    Returns (translated_text, detected_lang)
    Uses deep-translator by default.
    """
    lang = detect_language(text)
    try:
        translated = translate_with_deep_translator(text, target=target)
    except Exception as e:
        # If translator fails, return original text as fallback
        translated = text
    return translated, lang
