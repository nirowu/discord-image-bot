import ocr

def test_extract_text_success(monkeypatch):
    # Fake image preprocessing (avoid loading real file)
    monkeypatch.setattr(ocr, "preprocess_image", lambda path: "FAKE_IMAGE")
    monkeypatch.setattr(ocr, "extract_lines", lambda _: ["你好世界", "測試文字"])

    text = ocr.extract_text("fake.png")
    assert text == "你好世界 測試文字"


def test_extract_text_empty(monkeypatch):
    monkeypatch.setattr(ocr, "preprocess_image", lambda path: "FAKE_IMAGE")
    monkeypatch.setattr(ocr, "extract_lines", lambda _: [])

    text = ocr.extract_text("fake.png")
    assert text == ""
    

def test_extract_text_invalid_image(monkeypatch):
    # Simulate image load failure
    monkeypatch.setattr(ocr, "preprocess_image", lambda path: None)

    text = ocr.extract_text("fake.png")
    assert text == ""
