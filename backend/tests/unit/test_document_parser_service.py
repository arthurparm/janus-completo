from app.services.document_parser_service import DocumentParserService


def test_parse_pdf_returns_text_without_async_fallback(monkeypatch):
    service = DocumentParserService()
    monkeypatch.setattr(
        service,
        "_parse_pdf_pypdf2",
        lambda _data: "Capítulo 1\nIntrodução ao sistema",
    )
    monkeypatch.setattr(
        service,
        "_parse_pdf_minimal",
        lambda _data: "",
    )

    result = service._parse_pdf(b"%PDF-1.4")

    assert result == "Capítulo 1\nIntrodução ao sistema"


def test_parse_pdf_reader_falls_back_to_pypdf(monkeypatch):
    service = DocumentParserService()

    class _FakePage:
        @staticmethod
        def extract_text():
            return "Resumo do capítulo"

    class _FakeReader:
        def __init__(self, _stream):
            self.pages = [_FakePage()]

    import builtins
    import sys
    import types

    monkeypatch.delitem(sys.modules, "PyPDF2", raising=False)
    monkeypatch.setitem(sys.modules, "pypdf", types.SimpleNamespace(PdfReader=_FakeReader))

    original_import = builtins.__import__

    def _fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "PyPDF2":
            raise ModuleNotFoundError("No module named 'PyPDF2'")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", _fake_import)

    result = service._parse_pdf_pypdf2(b"%PDF-1.4")

    assert result == "Resumo do capítulo"
