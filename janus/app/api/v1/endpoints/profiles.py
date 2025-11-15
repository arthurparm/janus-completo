from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from pydantic import BaseModel, Field
from app.repositories.user_repository import ProfileRepository

router = APIRouter(tags=["Profiles"], prefix="/profiles")

class UpsertProfileRequest(BaseModel):
    user_id: int
    timezone: Optional[str] = Field(None)
    language: Optional[str] = Field(None)
    style_prefs: Optional[str] = Field(None)

class ProfileResponse(BaseModel):
    id: int
    user_id: int
    timezone: Optional[str]
    language: Optional[str]
    style_prefs: Optional[str]

def get_profile_repo(request: Request) -> ProfileRepository:
    return ProfileRepository()

@router.get("/{user_id}", response_model=ProfileResponse)
async def get_profile(user_id: int, repo: ProfileRepository = Depends(get_profile_repo)):
    p = repo.get_by_user(user_id)
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile not found")
    return ProfileResponse(id=p.id, user_id=p.user_id, timezone=p.timezone, language=p.language, style_prefs=p.style_prefs)

@router.post("/", response_model=ProfileResponse)
async def upsert_profile(payload: UpsertProfileRequest, repo: ProfileRepository = Depends(get_profile_repo)):
    p = repo.upsert(user_id=payload.user_id, timezone=payload.timezone, language=payload.language, style_prefs=payload.style_prefs)
    return ProfileResponse(id=p.id, user_id=p.user_id, timezone=p.timezone, language=p.language, style_prefs=p.style_prefs)