# utils/ocr.py
"""
OCR helpers:
- extract_text_from_image(uploaded_image) -> string

This tries pytesseract first (needs tesseract binary installed),
then falls back to easyocr (pure Python but needs torch).
"""

import os
import tempfile
from PIL import Image

def _save_image(uploaded_file):
    fd, path = tempfile.mkstemp(suffix=os.path.splitext(getattr(uploaded_file, "name", ""))[1] or ".png")
    with os.fdopen(fd, "wb") as f:
        f.write(uploaded_file.getbuffer())
    return path

# try pytesseract
try:
    import pytesseract
    _HAS_TESSERACT = True
except Exception:
    _HAS_TESSERACT = False

# try easyocr
try:
    import easyocr
    _HAS_EASYOCR = True
except Exception:
    _HAS_EASYOCR = False

def extract_text_from_image(uploaded_file) -> str:
    """
    Extract text from an uploaded image file (Streamlit UploadedFile).
    Returns extracted text (may be empty).
    """
    path = _save_image(uploaded_file)
    try:
        img = Image.open(path)
    except Exception:
        raise RuntimeError("Could not open uploaded image.")

    # Try pytesseract
    if _HAS_TESSERACT:
        try:
            text = pytesseract.image_to_string(img)
            if text and text.strip():
                return text.strip()
        except Exception:
            pass

    # Try easyocr
    if _HAS_EASYOCR:
        try:
            # detect languages automatically or use English as default
            reader = easyocr.Reader(["en"], gpu=False)
            results = reader.readtext(path, detail=0)
            return "\n".join(results).strip()
        except Exception:
            pass

    raise RuntimeError(
        "No OCR backend available. Install 'pytesseract' (and the tesseract binary) or 'easyocr'."
    )
