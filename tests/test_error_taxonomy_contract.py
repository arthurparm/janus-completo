import os
import sys

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

sys.path.append(os.path.join(os.getcwd(), "janus"))

from app.api.exception_handlers import add_exception_handlers


def _client() -> TestClient:
    app = FastAPI()

    @app.middleware("http")
    async def _inject_trace(request: Request, call_next):
        request.state.correlation_id = "trace-xyz"
        return await call_next(request)

    @app.get("/bad")
    async def bad():
        raise ValueError("invalid payload")

    @app.get("/denied")
    async def denied():
        raise ValueError("Access denied to this resource")

    @app.get("/boom")
    async def boom():
        raise RuntimeError("unexpected failure")

    add_exception_handlers(app)
    return TestClient(app, raise_server_exceptions=False)


def test_error_taxonomy_invalid_input_contract():
    client = _client()
    resp = client.get("/bad")
    assert resp.status_code == 400
    body = resp.json()
    assert body["error_code"] == "INVALID_INPUT"
    assert body["error_category"] == "validation"
    assert body["trace_id"] == "trace-xyz"


def test_error_taxonomy_access_denied_contract():
    client = _client()
    resp = client.get("/denied")
    assert resp.status_code == 403
    body = resp.json()
    assert body["error_code"] == "ACCESS_DENIED"
    assert body["error_category"] == "authz"
    assert body["trace_id"] == "trace-xyz"


def test_error_taxonomy_internal_error_contract():
    client = _client()
    resp = client.get("/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error_code"] == "INTERNAL_SERVICE_ERROR"
    assert body["error_category"] == "internal"
    assert body["trace_id"] == "trace-xyz"
