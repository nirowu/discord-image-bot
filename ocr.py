# ocr.py - EasyOCR version (macOS & Python 3.10 friendly)

import easyocr
import cv2

_reader = None  # lazy-loaded OCR reader


def get_reader():
    """
    Lazy load EasyOCR reader. 
    This prevents slow import time and makes pytest run fast.
    """
    global _reader
    if _reader is None:
        # Chinese + English support
        _reader = easyocr.Reader(["ch_tra", "en"])
    return _reader


def preprocess_image(path: str):
    """
    Load and prep image.
    This is mockable in tests.
    """
    img = cv2.imread(path)
    if img is None:
        print("[OCR Error] Cannot open:", path)
        return None

    # Upscale helps OCR accuracy
    img = cv2.resize(img, None, fx=2, fy=2)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

def extract_lines(img: cv2.typing.MatLike) -> list[str]:
    reader = get_reader()
    # EasyOCR returns a list of text strings (detail=0)
    results = reader.readtext(img, detail=0)
    return results

def extract_text(path: str) -> str:
    """
    Run OCR and return text.
    Real model loads only on first call.
    Fully mockable during pytest.
    """
    try:
        processed = preprocess_image(path)
        if processed is None:
            return ""

        results = extract_lines(processed)

        if not results:
            return ""

        return " ".join(results).strip()

    except Exception as e:
        print("[OCR Error]", e)
        return ""
