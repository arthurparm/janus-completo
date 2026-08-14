from __future__ import annotations

import importlib
from typing import Any

import pytest


def test_matrix_does_not_label_in_process_openapi_as_live(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = importlib.import_module("tooling.generate_api_matrix")
    endpoint = {
        "method": "GET",
        "path": "/api/v1/example",
        "module": "Example",
        "summary": "Example",
        "operation_id": "example_get",
    }
    monkeypatch.setattr(
        generator,
        "load_endpoints",
        lambda _openapi_url=None: ([endpoint], "openapi_in_process"),
    )
    monkeypatch.setattr(generator, "load_smoke_results", dict)
    monkeypatch.setattr(generator, "discover_test_endpoint_refs", set)
    monkeypatch.setattr(generator, "now_iso", lambda: "2026-08-14T00:00:00+00:00")

    matrix = generator.build_matrix()
    markdown = generator.render_markdown(matrix)

    assert matrix["metadata"]["source"] == "openapi_in_process"
    assert matrix["metadata"]["openapi_runtime_validated"] is False
    assert "openapi_url" not in matrix["metadata"]
    assert markdown.startswith("# API Endpoint Matrix\n")
    assert "OpenAPI runtime validated: `no`" in markdown
    assert "(Live)" not in markdown


def test_explicit_runtime_openapi_is_labeled_and_fail_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    generator = importlib.import_module("tooling.generate_api_matrix")
    runtime_spec = {
        "paths": {
            "/api/v1/runtime": {
                "get": {
                    "tags": ["Runtime"],
                    "summary": "Runtime",
                    "operationId": "runtime_get",
                }
            }
        }
    }
    calls: list[str] = []

    def fetch(openapi_url: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
        calls.append(openapi_url)
        assert timeout_seconds == 10.0
        return runtime_spec

    monkeypatch.setattr(generator, "fetch_runtime_openapi", fetch)

    endpoints, source = generator.load_endpoints("http://runtime/openapi.json")

    assert calls == ["http://runtime/openapi.json"]
    assert source == "openapi_runtime"
    assert endpoints[0]["path"] == "/api/v1/runtime"
    monkeypatch.setattr(generator, "load_smoke_results", dict)
    monkeypatch.setattr(generator, "discover_test_endpoint_refs", set)
    runtime_matrix = generator.build_matrix("http://runtime/openapi.json")
    assert runtime_matrix["metadata"]["source"] == "openapi_runtime"
    assert runtime_matrix["metadata"]["openapi_runtime_validated"] is True
    assert runtime_matrix["metadata"]["openapi_url"] == "http://runtime/openapi.json"

    def fail(_openapi_url: str, _timeout_seconds: float = 10.0) -> dict[str, Any]:
        raise RuntimeError("runtime indisponível")

    monkeypatch.setattr(generator, "fetch_runtime_openapi", fail)
    with pytest.raises(RuntimeError, match="runtime indisponível"):
        generator.load_endpoints("http://runtime/openapi.json")
