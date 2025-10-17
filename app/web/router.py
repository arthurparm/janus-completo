import structlog
from typing import Optional

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.services.llm_service import get_llm_service, LLMService
from app.services.system_status_service import system_status_service
from app.config import settings

logger = structlog.get_logger(__name__)
web_router = APIRouter(tags=["Web"])
templates = Jinja2Templates(directory="app/web/templates")
templates.env.globals["identity_name"] = getattr(settings, "AGENT_IDENTITY_NAME", None) or settings.APP_NAME
templates.env.globals["app_env"] = settings.ENVIRONMENT


@web_router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@web_router.get("/overview", response_class=HTMLResponse, include_in_schema=False)
async def web_overview(request: Request, service: LLMService = Depends(get_llm_service)):
    providers = service.get_providers()
    breakers = service.get_circuit_breaker_statuses()
    cache_entries = service.get_cache_status()
    system = system_status_service.get_system_status()
    return templates.TemplateResponse(
        "overview.html",
        {
            "request": request,
            "providers": providers,
            "breakers": breakers,
            "cache_entries": cache_entries,
            "system": system,
        },
    )


@web_router.get("/console", response_class=HTMLResponse, include_in_schema=False)
async def web_console(request: Request):
    return templates.TemplateResponse("console_llm.html", {"request": request})


@web_router.get("/health", response_class=HTMLResponse, include_in_schema=False)
async def web_health(request: Request, service: LLMService = Depends(get_llm_service)):
    status = await service.get_health_status()
    system = system_status_service.get_system_status()
    return templates.TemplateResponse("health.html", {"request": request, "status": status, "system": system})


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


@web_router.get("/chat", response_class=HTMLResponse, include_in_schema=False)
async def web_chat(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})
