from typing import Any, Dict, Optional

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from starlette.exceptions import HTTPException as StarletteHTTPException


class ProblemDetails(BaseModel):
    """
    RFC 7807 Problem Details for HTTP APIs
    https://tools.ietf.org/html/rfc7807
    """
    type: str = Field(default="about:blank", description="URI reference that identifies the problem type")
    title: str = Field(..., description="Short, human-readable summary of the problem")
    status: int = Field(..., description="HTTP status code")
    detail: str = Field(..., description="Human-readable explanation specific to this occurrence")
    instance: str = Field(..., description="URI reference that identifies the specific occurrence")
    trace_id: Optional[str] = Field(default=None, description="Correlation ID for tracing")


def _problem_response(status: int, title: str, detail: str, instance: str, trace_id: str) -> JSONResponse:
    """Constructs a standardized problem+json response."""
    body: Dict[str, Any] = {
        "type": "about:blank",
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
        "trace_id": trace_id,
    }
    return JSONResponse(content=body, status_code=status, media_type="application/problem+json")


def add_problem_handlers(app: FastAPI) -> None:
    """Adds custom exception handlers to the FastAPI app to produce problem+json responses."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exc_handler(request: Request, exc: StarletteHTTPException):
        trace_id = getattr(request.state, "correlation_id", "not-available")
        return _problem_response(exc.status_code, exc.detail or "HTTP Error", str(exc.detail), str(request.url.path),
                                 trace_id)

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError):
        trace_id = getattr(request.state, "correlation_id", "not-available")
        return _problem_response(422, "Unprocessable Entity", exc.errors().__repr__(), str(request.url.path), trace_id)

    @app.exception_handler(Exception)
    async def generic_handler(request: Request, exc: Exception):
        trace_id = getattr(request.state, "correlation_id", "not-available")
        return _problem_response(500, "Internal Server Error", str(exc), str(request.url.path), trace_id)
