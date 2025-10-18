import structlog
from typing import Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from app.services.llm_service import get_llm_service, LLMService
from app.services.system_status_service import system_status_service
from app.config import settings

# Imports internos para dados do modelo/provedor
from app.core.llm.llm_manager import _get_model_pricing, _model_penalty_factors, _model_stats, _budget_remaining

logger = structlog.get_logger(__name__)
web_router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["identity_name"] = getattr(settings, "AGENT_IDENTITY_NAME", None) or settings.APP_NAME
templates.env.globals["app_env"] = settings.ENVIRONMENT


@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@web_router.get("/overview", response_class=HTMLResponse, include_in_schema=False)
async def web_overview(request: Request):
    return templates.TemplateResponse("overview.html", {"request": request})

@web_router.get("/observability", response_class=HTMLResponse, include_in_schema=False)
async def web_observability(request: Request):
    return templates.TemplateResponse("observability.html", {"request": request})

@web_router.get("/agents", response_class=HTMLResponse, include_in_schema=False)
async def web_agents(request: Request):
    return templates.TemplateResponse("agents.html", {"request": request})

@web_router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def web_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@web_router.get("/knowledge", response_class=HTMLResponse, include_in_schema=False)
async def web_knowledge(request: Request):
    return templates.TemplateResponse("knowledge.html", {"request": request})

@web_router.get("/system", response_class=HTMLResponse, include_in_schema=False)
async def web_system(request: Request):
    return templates.TemplateResponse("system.html", {"request": request})








@web_router.get("/operations", response_class=HTMLResponse, include_in_schema=False)
async def web_operations(request: Request, service: LLMService = Depends(get_llm_service)):
    providers = service.get_providers()
    breakers = service.get_circuit_breaker_statuses()
    cache_entries = service.get_cache_status()
    return templates.TemplateResponse(
        "operations.html",
        {
            "request": request,
            "providers": providers,
            "breakers": breakers,
            "cache_entries": cache_entries,
        },
    )

@web_router.get("/stream", include_in_schema=False)
async def web_stream(request: Request):
    """SSE stream para animações do herói e estados da IA."""
    import asyncio, json, random, time

    async def event_gen():
        # State cycling demo; substitua por observability/knowledge para dados reais
        modes = ["idle", "processing", "creative"]
        i = 0
        while True:
            # Ping básico de saúde
            status = system_status_service.get_system_status()
            payload = {
                "ts": time.time(),
                "mode": modes[i % len(modes)],
                "metrics": status,
                "entropy": random.random(),
            }
            yield f"data: {json.dumps(payload)}\n\n"
            i += 1
            await asyncio.sleep(2)

    return StreamingResponse(event_gen(), media_type="text/event-stream")
