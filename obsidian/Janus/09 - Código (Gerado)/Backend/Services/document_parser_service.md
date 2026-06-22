---
tipo: codigo
dominio: backend
camada: services
gerado: true
origem: "backend/app/services/document_parser_service.py"
ultima_geracao: "2026-05-22T20:43:32.754469+00:00"
status: ativo
---

# document_parser_service

## Objetivo
Document Parser Service with hierarchical fallbacks.
Extracts text from various document formats.

## Arquivos-fonte
- `backend/app/services/document_parser_service.py`

## Fluxos de uso (chamadores)
- `backend/app/services/document_service.py`

## Símbolos
- class: `DocumentParserService`
  - Parses documents with fallback strategies.
- method: `DocumentParserService.__init__(self)`
- method: `DocumentParserService.parse(self, data: bytes, content_type: str, filename: str)` -> `str`
  - Parse document with automatic format detection and fallbacks.
- method: `DocumentParserService._parse_plain(self, data: bytes)` -> `str`
  - Parse plain text file.
- method: `DocumentParserService._parse_json(self, data: bytes)` -> `str`
  - Parse JSON files into searchable text lines.
- method: `DocumentParserService._parse_html(self, data: bytes)` -> `str`
  - Parse HTML file.
- method: `DocumentParserService._parse_docx(self, data: bytes)` -> `str`
  - Parse DOCX file.
- method: `DocumentParserService._parse_pdf(self, data: bytes)` -> `str`
  - Parse PDF file with fallback strategies.
- method: `DocumentParserService._parse_pdf_pypdf2(self, data: bytes)` -> `str`
  - Primary PDF parser using PyPDF2.
- method: `DocumentParserService._parse_pdf_minimal(self, data: bytes)` -> `str`
  - Minimal PDF fallback (returns empty - logged).

## Observações
- Esta nota é gerada automaticamente a partir do código-fonte.
