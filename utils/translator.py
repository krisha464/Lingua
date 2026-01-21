# utils/translator.py
# Simple wrapper to detect language and translate text.
# If you have a cloud provider, replace detect_and_translate implementation.

SUPPORTED_LANGS = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "auto": "Auto-detect"
}

# try googletrans as optional fallback
try:
    from googletrans import Translator as GoogleTranslator
    _HAS_GOOGLETRANS = True
    _gt = GoogleTranslator()
except Exception:
    _HAS_GOOGLETRANS = False

def detect_and_translate(text, target_lang="en"):
    """
    Returns (translated_text, detected_lang)
    - If googletrans is installed, uses it.
    - Otherwise returns input text and 'unknown' as detected language.
    """
    if not text:
        return "", "unknown"
    if _HAS_GOOGLETRANS:
        try:
            # googletrans uses 'dest' param
            if target_lang == "auto":
                # just detect and return original
                det = _gt.detect(text).lang
                return text, det
            res = _gt.translate(text, dest=target_lang)
            detected = res.src
            return res.text, detected
        except Exception:
            pass
    # fallback: no translation, return original
    return text, "unknown"
    