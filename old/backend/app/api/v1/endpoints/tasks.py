import msgpack
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, Field

from app.models.schemas import QueueName
from app.services.task_service import TaskService, get_task_service

router = APIRouter(tags=["Tasks"])
logger = structlog.get_logger(__name__)

# --- Pydantic Models (DTOs) ---


class ConsolidationTaskRequest(BaseModel):
    mode: str = Field("batch")
    limit: int | None = Field(10)
    experience_id: str | None = None
    experience_content: str | None = None
    metadata: dict | None = None


class TaskResponse(BaseModel):
    task_id: str
    message: str
    queue: str


class QueueInfoResponse(BaseModel):
    name: str
    messages: int
    consumers: int


class QueuePolicyResponse(BaseModel):
    name: str
    durable: bool
    messages: int
    consumers: int
    arguments: dict


class QueuePolicyValidationResponse(BaseModel):
    status: str
    message: str
    details: dict


class ReconcilePolicyRequest(BaseModel):
    force_delete: bool = True


class ReconcilePolicyResponse(BaseModel):
    status: str
    message: str
    details: dict


class OutboxStatsResponse(BaseModel):
    pending: int = 0
    retry: int = 0
    processing: int = 0
    sent: int = 0
    dead: int = 0


class OutboxReconcileRequest(BaseModel):
    limit: int = 100
    requeue_dead: bool = True


class OutboxReconcileResponse(BaseModel):
    requeued_dead: int
    dispatch: dict
    stats: dict


# --- Endpoints ---


@router.post(
    "/consolidation", response_model=TaskResponse, summary="Publica tarefa de consolidação"
)
async def create_consolidation_task(
    request: ConsolidationTaskRequest,
    service: TaskService = Depends(get_task_service),
    http_request: Request = None,
):
    """Delega a publicação de uma tarefa de consolidação para o TaskService."""
    # TaskServiceError é tratado pelo exception handler central -> 500
    task_id = await service.create_consolidation_task(
        mode=request.mode,
        limit=request.limit,
        experience_id=request.experience_id,
        experience_content=request.experience_content,
        metadata=request.metadata,
    )
    data = {
        "task_id": task_id,
        "message": f"Tarefa de consolidação criada com sucesso (modo: {request.mode})",
        "queue": QueueName.KNOWLEDGE_CONSOLIDATION,
    }
    return _negotiate_response(http_request, data)


@router.get(
    "/queue/{queue_name}",
    response_model=QueueInfoResponse,
    summary="Obtém informações sobre uma fila",
)
async def get_queue_info(queue_name: str, service: TaskService = Depends(get_task_service)):
    """Delega a busca de informações da fila para o TaskService."""
    # TaskServiceError (se a fila não for encontrada) é tratado pelo handler -> 404
    info = await service.get_queue_details(queue_name)
    return QueueInfoResponse(**info)


@router.get("/health/rabbitmq", summary="Verifica saúde do RabbitMQ")
async def check_rabbitmq_health(
    service: TaskService = Depends(get_task_service), request: Request = None
):
    """Delega a verificação de saúde do broker para o TaskService."""
    if await service.check_broker_health():
        return _negotiate_response(
            request, {"status": "healthy", "message": "Conexão com RabbitMQ está operacional"}
        )

    raise HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="RabbitMQ não está acessível"
    )


@router.get(
    "/queue/{queue_name}/policy",
    response_model=QueuePolicyResponse,
    summary="Obtém política/argumentos da fila",
)
async def get_queue_policy(queue_name: str, service: TaskService = Depends(get_task_service)):
    """Retorna a política e argumentos atuais da fila via Management API."""
    policy = await service.get_queue_policy(queue_name)
    return QueuePolicyResponse(**policy)


@router.get(
    "/queue/{queue_name}/policy/validate",
    response_model=QueuePolicyValidationResponse,
    summary="Valida argumentos da fila contra configuração esperada",
)
async def validate_queue_policy(queue_name: str, service: TaskService = Depends(get_task_service)):
    """Valida a política da fila e indica divergências (TTL, max-length, etc.)."""
    result = await service.validate_queue_policy(queue_name)
    return QueuePolicyValidationResponse(**result)


@router.post(
    "/queue/{queue_name}/policy/reconcile",
    response_model=ReconcilePolicyResponse,
    summary="Reconcilia política da fila (deleta e recria se divergente)",
)
async def reconcile_queue_policy(
    queue_name: str,
    request: ReconcilePolicyRequest,
    service: TaskService = Depends(get_task_service),
):
    """
    Executa reconciliação da política da fila. Se houver divergências e `force_delete` estiver habilitado,
    a fila será deletada via Management API e recriada com os argumentos esperados.
    Atenção: Deletar a fila remove mensagens pendentes.
    """
    result = await service.reconcile_queue_policy(queue_name, force_delete=request.force_delete)
    return ReconcilePolicyResponse(**result)


@router.get(
    "/outbox/stats",
    response_model=OutboxStatsResponse,
    summary="Retorna estatísticas do outbox transacional",
)
async def get_outbox_stats(request: Request):
    outbox_service = getattr(request.app.state, "outbox_service", None)
    if outbox_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outbox service não está disponível.",
        )
    return OutboxStatsResponse(**outbox_service.get_stats())


@router.post(
    "/outbox/reconcile",
    response_model=OutboxReconcileResponse,
    summary="Reencaminha eventos do outbox para reconciliação",
)
async def reconcile_outbox(payload: OutboxReconcileRequest, request: Request):
    outbox_service = getattr(request.app.state, "outbox_service", None)
    if outbox_service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Outbox service não está disponível.",
        )
    result = await outbox_service.reconcile(
        limit=max(1, int(payload.limit)),
        requeue_dead=bool(payload.requeue_dead),
    )
    return OutboxReconcileResponse(**result)


def _negotiate_response(request: Request, data: dict) -> Response:
    accept = (request.headers.get("accept") or "").lower()
    if "application/msgpack" in accept:
        return Response(
            content=msgpack.packb(data, use_bin_type=True), media_type="application/msgpack"
        )
    return JSONResponse(content=data)
