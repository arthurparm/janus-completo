from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.services.chat_service import ChatService, get_chat_service

from .deps import is_chat_auth_enforced, resolve_authenticated_user_context

router = APIRouter()


@router.get(
    "/study-jobs/{job_id}",
    summary="Consulta o status de um job de estudo assíncrono do chat",
)
async def get_study_job(
    job_id: str,
    service: ChatService = Depends(get_chat_service),
    http: Request = None,
):
    identity_ctx = resolve_authenticated_user_context(
        http,
        None,
        allow_anonymous_fallback=False,
        endpoint_label="/api/v1/chat/study-jobs",
    )
    user_id = identity_ctx.user_id
    if user_id is None and is_chat_auth_enforced():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"message": "Authentication required", "code": "CHAT_AUTH_REQUIRED"},
        )

    jobs = getattr(http.app.state, "chat_study_job_service", None)
    if jobs is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study job not found")
    job = jobs.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study job not found")
    if user_id is not None and str(job.user_id or "") not in {"", str(user_id)}:
        history = service.get_history(job.conversation_id, user_id=user_id)
        if not history:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "conversation_id": job.conversation_id,
        "message_id": job.message_id,
        "placeholder_message": job.placeholder_message,
        "failure_classification": job.failure_classification,
        "final_response": job.final_response,
        "error": job.error,
        "updated_at": job.updated_at,
    }
