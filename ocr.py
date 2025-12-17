# ocr.py - PaddleOCR version (TDD-compatible + OpenCV-safe)

from paddleocr import PaddleOCR
import cv2

_reader = None  # lazy-loaded OCR reader


def get_reader():
    """
    Lazy load PaddleOCR reader.
    Kept mockable for pytest.
    """
    global _reader
    if _reader is None:
        _reader = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            lang="ch",  # Traditional Chinese
        )
    return _reader


def preprocess_image(path: str):
    """
    Load and prep image.
    This is mockable in tests.
    """
    if not path:
        return None

    img = cv2.imread(path, cv2.IMREAD_COLOR)
    if img is None:
        print("[OCR Error] Cannot open:", path)
        return None

    # Upscale helps OCR accuracy
    img = cv2.resize(img, None, fx=2, fy=2)

    return img

def extract_lines(img: cv2.typing.MatLike) -> list[str]:
    reader = get_reader()
    results = reader.predict(img)
    texts = []
    for res in results:
        texts.extend(res.get("rec_texts", []))
    return texts

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
