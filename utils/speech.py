# utils/speech.py
"""
Speech helpers:
- speech_to_text(uploaded_file) -> transcribed text
- record_and_translate() -> record mic input, transcribe & translate
- text_to_speech_bytes(text, lang='en') -> mp3 bytes
"""

import os
import tempfile
from io import BytesIO

# Supported languages for TTS
SUPPORTED_SPEECH_LANGS = {
    "en": "English",
    "hi": "Hindi",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh-cn": "Chinese (Simplified)",
    "ja": "Japanese",
    "ko": "Korean",
    "ru": "Russian",
    "ar": "Arabic",
    "it": "Italian",
    "pt": "Portuguese",
    "tr": "Turkish",
    "bn": "Bengali",
    "pa": "Punjabi",
    "ur": "Urdu",
    "sv": "Swedish",
    "th": "Thai",
    "fa": "Persian",
    "ta": "Tamil",
    "te": "Telugu",
    "gu": "Gujarati",
    "pl": "Polish",
    "uk": "Ukrainian",
    "nl": "Dutch",
    "vi": "Vietnamese",
    "id": "Indonesian",
}

# Save uploaded file
def _save_uploaded_file(uploaded_file, suffix=None):
    name = getattr(uploaded_file, "name", "uploaded")
    ext = os.path.splitext(name)[1] or (suffix or ".tmp")
    fd, path = tempfile.mkstemp(suffix=ext)
    with os.fdopen(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

# Try whisper
try:
    import whisper
    _HAS_WHISPER = True
except Exception:
    _HAS_WHISPER = False

# Try speech_recognition + pydub
try:
    import speech_recognition as sr
    from pydub import AudioSegment
    _HAS_SR = True
except Exception:
    _HAS_SR = False

def speech_to_text(uploaded_file, lang: str = "en") -> str:
    """Transcribe audio file (uploaded_file is Streamlit UploadedFile)."""
    path = _save_uploaded_file(uploaded_file)

    if _HAS_WHISPER:
        try:
            model = whisper.load_model("small")
            result = model.transcribe(path)
            return result.get("text", "").strip()
        except Exception:
            pass

    if _HAS_SR:
        ext = os.path.splitext(path)[1].lower()
        wav_path = path
        if ext != ".wav":
            try:
                wav_path = path + ".wav"
                AudioSegment.from_file(path).export(wav_path, format="wav")
            except Exception:
                wav_path = path

        r = sr.Recognizer()
        try:
            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
            text = r.recognize_google(audio_data, language=lang)
            return text
        except Exception:
            return ""
    return ""

# TTS with gTTS
try:
    from gtts import gTTS
    _HAS_GTTS = True
except Exception:
    _HAS_GTTS = False

def text_to_speech_bytes(text: str, lang: str = "en") -> bytes:
    """Return MP3 bytes for given text using gTTS."""
    if not _HAS_GTTS:
        raise RuntimeError("gTTS not installed. Run: pip install gTTS")
    bio = BytesIO()
    tts = gTTS(text=text, lang=lang)
    tts.write_to_fp(bio)
    bio.seek(0)
    return bio.read()

