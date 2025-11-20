from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.db.mysql_config import mysql_db
from app.models.user_models import User, Role, UserRole, Profile, Consent, OAuthToken

class UserRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def get_user(self, user_id: int) -> Optional[User]:
        s = self._get_session()
        try:
            return s.query(User).filter(User.id == user_id).first()
        finally:
            if not self._session:
                s.close()

    def get_by_email(self, email: str) -> Optional[User]:
        s = self._get_session()
        try:
            return s.query(User).filter(User.email == email).first()
        finally:
            if not self._session:
                s.close()

    def create_user(self, email: Optional[str], display_name: Optional[str]) -> User:
        s = self._get_session()
        try:
            u = User(email=email, display_name=display_name)
            s.add(u)
            s.commit()
            s.refresh(u)
            return u
        finally:
            if not self._session:
                s.close()

    def assign_role(self, user_id: int, role_name: str) -> bool:
        s = self._get_session()
        try:
            r = s.query(Role).filter(Role.name == role_name).first()
            if r is None:
                r = Role(name=role_name)
                s.add(r)
                s.commit()
                s.refresh(r)
            ur = UserRole(user_id=user_id, role_id=r.id)
            s.add(ur)
            s.commit()
            return True
        finally:
            if not self._session:
                s.close()

    def is_admin(self, user_id: int) -> bool:
        s = self._get_session()
        try:
            q = s.query(UserRole).join(Role, UserRole.role_id == Role.id).filter(
                and_(UserRole.user_id == user_id, Role.name == "ADMIN")
            )
            return q.first() is not None
        finally:
            if not self._session:
                s.close()

    def has_role(self, user_id: int, role_name: str) -> bool:
        s = self._get_session()
        try:
            q = s.query(UserRole).join(Role, UserRole.role_id == Role.id).filter(
                and_(UserRole.user_id == user_id, Role.name == role_name)
            )
            return q.first() is not None
        finally:
            if not self._session:
                s.close()

class ProfileRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def get_by_user(self, user_id: int) -> Optional[Profile]:
        s = self._get_session()
        try:
            return s.query(Profile).filter(Profile.user_id == user_id).first()
        finally:
            if not self._session:
                s.close()

    def upsert(self, user_id: int, timezone: Optional[str], language: Optional[str], style_prefs: Optional[str]) -> Profile:
        s = self._get_session()
        try:
            p = s.query(Profile).filter(Profile.user_id == user_id).first()
            if p is None:
                p = Profile(user_id=user_id, timezone=timezone, language=language or "pt-BR", style_prefs=style_prefs)
                s.add(p)
            else:
                if timezone is not None:
                    p.timezone = timezone
                if language is not None:
                    p.language = language
                if style_prefs is not None:
                    p.style_prefs = style_prefs
            s.commit()
            s.refresh(p)
            return p
        finally:
            if not self._session:
                s.close()


class ConsentRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def add_consent(self, user_id: int, scope: str, granted: bool = True, expires_at: Optional[Any] = None) -> Consent:
        s = self._get_session()
        try:
            c = s.query(Consent).filter(Consent.user_id == user_id, Consent.scope == scope).first()
            if c is None:
                c = Consent(user_id=user_id, scope=scope, granted=granted, expires_at=expires_at)
                s.add(c)
            else:
                c.granted = granted
                c.expires_at = expires_at
            s.commit()
            s.refresh(c)
            return c
        finally:
            if not self._session:
                s.close()

    def list_consents(self, user_id: int) -> list[Consent]:
        s = self._get_session()
        try:
            return s.query(Consent).filter(Consent.user_id == user_id).all()
        finally:
            if not self._session:
                s.close()

    def revoke_consent(self, user_id: int, scope: str) -> bool:
        s = self._get_session()
        try:
            c = s.query(Consent).filter(Consent.user_id == user_id, Consent.scope == scope).first()
            if c is None:
                return False
            s.delete(c)
            s.commit()
            return True
        finally:
            if not self._session:
                s.close()

    def has_consent(self, user_id: int, scope: str) -> bool:
        s = self._get_session()
        try:
            c = s.query(Consent).filter(Consent.user_id == user_id, Consent.scope == scope).first()
            if c is None or not c.granted:
                return False
            if c.expires_at is not None:
                try:
                    from datetime import datetime
                    return c.expires_at > datetime.utcnow()
                except Exception:
                    return False
            return True
        finally:
            if not self._session:
                s.close()


class OAuthTokenRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def upsert(self, user_id: int, provider: str, access_token: str, refresh_token: Optional[str], expires_at: Optional[Any]) -> OAuthToken:
        s = self._get_session()
        try:
            tok = s.query(OAuthToken).filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider).first()
            if tok is None:
                tok = OAuthToken(user_id=user_id, provider=provider, access_token=access_token, refresh_token=refresh_token, expires_at=expires_at)
                s.add(tok)
            else:
                tok.access_token = access_token
                tok.refresh_token = refresh_token if refresh_token is not None else tok.refresh_token
                tok.expires_at = expires_at
            s.commit()
            s.refresh(tok)
            return tok
        finally:
            if not self._session:
                s.close()

    def get(self, user_id: int, provider: str) -> Optional[OAuthToken]:
        s = self._get_session()
        try:
            return s.query(OAuthToken).filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider).first()
        finally:
            if not self._session:
                s.close()
