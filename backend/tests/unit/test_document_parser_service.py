from app.services.document_parser_service import DocumentParserService


def test_parse_json_file_extracts_searchable_leaf_paths():
    service = DocumentParserService()

    payload = (
        b'{"version":1,"data":{"atlas":[{"name":"Docas","rumor":"Porto da tregua"}],'
        b'"timeline":[{"event":"Banquete da Ruptura"}]}}'
    )

    text = service.parse(payload, "application/json", "genesis-backup.json")

    assert "version: 1" in text
    assert "data.atlas[0].name: Docas" in text
    assert "data.atlas[0].rumor: Porto da tregua" in text
    assert "data.timeline[0].event: Banquete da Ruptura" in text
