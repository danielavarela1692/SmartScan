from facturas.classification import classifier


class FakePage:
    def __init__(self, text: str):
        self._text = text

    def extract_text(self) -> str:
        return self._text


class FakeReader:
    def __init__(self, pages_text: list[str]):
        self.pages = [FakePage(text) for text in pages_text]


def test_classifies_as_structured_when_enough_text(monkeypatch):
    monkeypatch.setattr(classifier, "PdfReader", lambda _: FakeReader(["x" * 500]))
    assert classifier.classify(b"irrelevant") is classifier.DocumentKind.STRUCTURED_PDF


def test_classifies_as_scanned_when_little_or_no_text(monkeypatch):
    monkeypatch.setattr(classifier, "PdfReader", lambda _: FakeReader([""]))
    assert classifier.classify(b"irrelevant") is classifier.DocumentKind.SCANNED
