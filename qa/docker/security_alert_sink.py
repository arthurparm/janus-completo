from __future__ import annotations

from fastapi import FastAPI, Response, status

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/alerts", status_code=status.HTTP_202_ACCEPTED)
async def accept_security_alert() -> Response:
    """Accept local alerts without logging their potentially sensitive body."""
    return Response(status_code=status.HTTP_202_ACCEPTED)
