from fastapi import APIRouter
from pydantic import BaseModel

from app.config import settings

router = APIRouter(tags=["Authentication"], prefix="/auth")


class OIDCConfigResponse(BaseModel):
    issuer: str
    client_id: str
    audience: str
    scopes: list[str]
    authorization_endpoint: str
    response_type: str = "code"
    code_challenge_method: str = "S256"


@router.get("/oidc-config", response_model=OIDCConfigResponse, operation_id="get_oidc_config")
async def get_oidc_config() -> OIDCConfigResponse:
    """Public metadata required by the SPA's Authorization Code + PKCE flow."""
    return OIDCConfigResponse(
        issuer=settings.OIDC_ISSUER,
        client_id=settings.OIDC_PUBLIC_CLIENT_ID,
        audience=settings.OIDC_USER_AUDIENCE,
        scopes=list(settings.OIDC_PUBLIC_SCOPES),
        authorization_endpoint=settings.OIDC_AUTHORIZATION_ENDPOINT,
    )
