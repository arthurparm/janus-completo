from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Janus Web Preview")

BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/web/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/web/console")
def web_console(request: Request):
    # Console não depende de dados do backend para renderizar inicialmente
    return templates.TemplateResponse("console_llm.html", {"request": request})


@app.get("/web/models/arthurparm")
def web_model_arthurparm(request: Request):
    # Mock simplificado apenas para visualização do template model.html
    providers = {
        "openai": {
            "budget_remaining": 123.45,
            "pricing": {
                "input_per_ktokens_usd": 0.5,
                "output_per_ktokens_usd": 1.5,
                "training_per_ktokens_usd": 0.0,
            },
            "penalties": {
                "role_priority_factor": 1.0,
                "model_penalty_factor": 1.0,
            },
            "stats": {
                "total_requests": 42,
                "total_tokens_in": 120_000,
                "total_tokens_out": 210_000,
                "avg_latency_ms": 1200,
            },
            "limits": {
                "system": {"max_ktokens": 16},
                "user": {"max_ktokens": 24},
                "assistant": {"max_ktokens": 32},
            },
        }
    }
    global_cfg = {
        "expected_ktokens_by_role": {"system": 4, "user": 8, "assistant": 12},
        "cost_increment_per_request_usd": 0.002,
        "penalty_increment_per_request": 0.001,
        "role_priority_factor": {"low": 0.8, "normal": 1.0, "high": 1.2},
    }
    return templates.TemplateResponse(
        "model.html",
        {
            "request": request,
            "model_name": "arthurparm",
            "providers": providers,
            "global": global_cfg,
            "raw_details": {"note": "Pré-visualização simplificada"},
        },
    )


@app.get("/web/operations")
def web_operations(request: Request):
    # Mock simplificado para visualizar o template operations.html
    breakers = [
        {"provider": "openai", "state": "closed"},
        {"provider": "ollama", "state": "open"},
        {"provider": "qdrant", "state": "half-open"},
    ]
    cache_entries = [
        {"key": "models", "val": {"size": 3, "hits": 120, "misses": 5}},
        {"key": "responses", "val": {"size": 12, "ttl_seconds": 600}},
    ]
    return templates.TemplateResponse(
        "operations.html",
        {
            "request": request,
            "breakers": breakers,
            "cache_entries": cache_entries,
        },
    )