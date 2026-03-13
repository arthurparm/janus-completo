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
