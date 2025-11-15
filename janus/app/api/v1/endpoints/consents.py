from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.mysql_config import mysql_db
from app.models.consent_models import Consent

router = APIRouter(tags=["Consents"], prefix="/consents")

def _get_session() -> Session:
    return mysql_db.get_session_direct()

class ConsentRequest(BaseModel):
    user_id: str
    scope: str
    resource: Optional[str] = None
    notes: Optional[str] = None

class ConsentResponse(BaseModel):
    id: int
    user_id: str
    scope: str
    resource: Optional[str]
    granted: str
    created_at: str
    revoked_at: Optional[str]

@router.post("/", response_model=ConsentResponse)
async def grant_consent(payload: ConsentRequest):
    s = _get_session()
    try:
        c = Consent(user_id=payload.user_id, scope=payload.scope, resource=payload.resource, granted="True", notes=payload.notes)
        s.add(c)
        s.commit()
        s.refresh(c)
        return ConsentResponse(id=c.id, user_id=c.user_id, scope=c.scope, resource=c.resource, granted=c.granted, created_at=str(c.created_at), revoked_at=str(c.revoked_at) if c.revoked_at else None)
    finally:
        s.close()

@router.get("/", response_model=List[ConsentResponse])
async def list_consents(user_id: Optional[str] = None, scope: Optional[str] = None):
    s = _get_session()
    try:
        q = s.query(Consent)
        if user_id:
            q = q.filter(Consent.user_id == user_id)
        if scope:
            q = q.filter(Consent.scope == scope)
        items = q.order_by(Consent.created_at.desc()).all()
        return [ConsentResponse(id=c.id, user_id=c.user_id, scope=c.scope, resource=c.resource, granted=c.granted, created_at=str(c.created_at), revoked_at=str(c.revoked_at) if c.revoked_at else None) for c in items]
    finally:
        s.close()

@router.post("/{consent_id}/revoke", response_model=ConsentResponse)
async def revoke_consent(consent_id: int):
    s = _get_session()
    try:
        c = s.query(Consent).filter(Consent.id == consent_id).first()
        if not c:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Consentimento não encontrado")
        from datetime import datetime
        c.granted = "False"
        c.revoked_at = datetime.utcnow()
        s.commit()
        s.refresh(c)
        return ConsentResponse(id=c.id, user_id=c.user_id, scope=c.scope, resource=c.resource, granted=c.granted, created_at=str(c.created_at), revoked_at=str(c.revoked_at) if c.revoked_at else None)
    finally:
        s.close()