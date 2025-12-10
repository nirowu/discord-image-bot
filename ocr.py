# ocr.py
from typing import Optional

try:
    import pytesseract
    from PIL import Image
except ImportError:
    pytesseract = None
    Image = None


def extract_text(path: str) -> str:
    """
    Tiny wrapper around pytesseract.image_to_string.

    In real use, returns OCR text.
    In tests, this is monkeypatched, so we don't need a perfect impl.
    """
    if pytesseract is None or Image is None:
        # Library not available (e.g., CI without tesseract) – fail soft.
        return ""

    try:
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return text.strip()
    except Exception:
        # Any error: just treat as "no OCR"
        return ""

