from typing import Any, cast

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import db
from app.models.user_models import (
    Consent,
    ExternalIdentity,
    ExternalIdentityEvent,
    OAuthToken,
    Profile,
    ServicePrincipal,
    User,
)
from app.services.oauth_token_security_service import (
    is_protected_oauth_token,
    protect_oauth_token,
    reveal_oauth_token,
)


class IdentityLinkRequiredError(RuntimeError):
    """An existing account needs an explicit, separately authorized link flow."""


class InactivePrincipalError(RuntimeError):
    """The resolved local account or service principal is inactive."""


class UserRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def get_user(self, user_id: int) -> User | None:
        s = self._get_session()
        try:
            return s.query(User).filter(User.id == user_id).first()
        finally:
            if not self._session:
                s.close()

    def get_by_email(self, email: str) -> User | None:
        s = self._get_session()
        try:
            return s.query(User).filter(User.email == email).first()
        finally:
            if not self._session:
                s.close()

    def update_display_name(self, user_id: int, display_name: str | None) -> User | None:
        s = self._get_session()
        try:
            user = s.query(User).filter(User.id == user_id).first()
            if user is None:
                return None
            user.display_name = display_name
            s.commit()
            s.refresh(user)
            return user
        finally:
            if not self._session:
                s.close()

    def resolve_or_provision_external_identity(
        self,
        *,
        issuer: str,
        subject: str,
        email: str | None,
        email_verified: bool,
        display_name: str | None,
        admin_group_authorized: bool = False,
    ) -> tuple[User, bool]:
        """Atomically resolve or JIT-provision by the only trusted key: (issuer, subject)."""
        normalized_issuer = issuer.strip().rstrip("/")
        normalized_subject = subject.strip()
        if not normalized_issuer or not normalized_subject:
            raise ValueError("issuer and subject are required")
        s = self._get_session()
        try:
            identity = (
                s.query(ExternalIdentity)
                .filter(
                    ExternalIdentity.issuer == normalized_issuer,
                    ExternalIdentity.subject == normalized_subject,
                )
                .first()
            )
            if identity is not None:
                user = s.query(User).filter(User.id == identity.user_id).first()
                if user is None or str(user.status).lower() != "active":
                    raise InactivePrincipalError("inactive user")
                identity.last_seen_at = __import__("datetime").datetime.utcnow()
                s.commit()
                return user, False

            # Email is informative only. It must never silently link an existing account.
            if email and s.query(User).filter(User.email == email).first() is not None:
                raise IdentityLinkRequiredError("explicit account linking is required")

            user = User(
                email=email if email_verified else None,
                display_name=display_name,
                status="active",
            )
            s.add(user)
            s.flush()
            identity = ExternalIdentity(
                issuer=normalized_issuer,
                subject=normalized_subject,
                user_id=user.id,
                email_at_link=email,
                email_verified=email_verified,
            )
            s.add(identity)
            s.flush()
            s.add(
                ExternalIdentityEvent(
                    identity_id=identity.id,
                    user_id=user.id,
                    event_type="jit_provisioned",
                    admin_group_authorized=admin_group_authorized,
                )
            )
            s.commit()
            s.refresh(user)
            return user, True
        except IntegrityError:
            # Concurrent first logins converge on the database uniqueness constraint.
            s.rollback()
            identity = (
                s.query(ExternalIdentity)
                .filter(
                    ExternalIdentity.issuer == normalized_issuer,
                    ExternalIdentity.subject == normalized_subject,
                )
                .first()
            )
            if identity is None:
                raise
            user = s.query(User).filter(User.id == identity.user_id).first()
            if user is None or str(user.status).lower() != "active":
                raise InactivePrincipalError("inactive user")
            return user, False
        finally:
            if not self._session:
                s.close()

    def get_active_service_principal(
        self, *, issuer: str, subject: str, client_id: str
    ) -> tuple[ServicePrincipal, set[str]] | None:
        s = self._get_session()
        try:
            principal = (
                s.query(ServicePrincipal)
                .filter(
                    ServicePrincipal.issuer == issuer.strip().rstrip("/"),
                    ServicePrincipal.subject == subject,
                    ServicePrincipal.client_id == client_id,
                )
                .first()
            )
            if principal is None:
                return None
            if str(principal.status).lower() != "active":
                raise InactivePrincipalError("inactive service principal")
            return principal, {str(item.scope) for item in principal.scopes}
        finally:
            if not self._session:
                s.close()

    def has_active_admin_delegation(
        self,
        *,
        delegation_id: str,
        human_subject: str,
        service_client_id: str,
        operation_id: str,
        trace_id: str,
    ) -> bool:
        s = self._get_session()
        try:
            row = s.execute(
                text(
                    """
                    SELECT 1 FROM admin_delegations
                    WHERE id = :delegation_id
                      AND human_subject = :human_subject
                      AND service_client_id = :service_client_id
                      AND operation_id = :operation_id
                      AND trace_id = :trace_id
                      AND result_status IS NULL
                    """
                ),
                {
                    "delegation_id": delegation_id,
                    "human_subject": human_subject,
                    "service_client_id": service_client_id,
                    "operation_id": operation_id,
                    "trace_id": trace_id,
                },
            ).first()
            return row is not None
        finally:
            if not self._session:
                s.close()

    def create_user(
        self,
        email: str | None,
        display_name: str | None,
    ) -> User:
        s = self._get_session()
        try:
            u = User(
                email=email,
                display_name=display_name,
            )
            s.add(u)
            s.commit()
            s.refresh(u)
            return u
        finally:
            if not self._session:
                s.close()

class ProfileRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def get_by_user(self, user_id: int) -> Profile | None:
        s = self._get_session()
        try:
            return s.query(Profile).filter(Profile.user_id == user_id).first()
        finally:
            if not self._session:
                s.close()

    def upsert(
        self, user_id: int, timezone: str | None, language: str | None, style_prefs: str | None
    ) -> Profile:
        s = self._get_session()
        try:
            p = s.query(Profile).filter(Profile.user_id == user_id).first()
            if p is None:
                p = Profile(
                    user_id=user_id,
                    timezone=timezone,
                    language=language or "pt-BR",
                    style_prefs=style_prefs,
                )
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
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def add_consent(
        self,
        user_id: int,
        scope: str,
        granted: bool = True,
        expires_at: Any | None = None,
        *,
        commit: bool = True,
    ) -> Consent:
        s = self._get_session()
        try:
            c = s.query(Consent).filter(Consent.user_id == user_id, Consent.scope == scope).first()
            if c is None:
                c = Consent(user_id=user_id, scope=scope, granted=granted, expires_at=expires_at)
                s.add(c)
            else:
                c.granted = granted
                c.expires_at = expires_at
            if commit:
                s.commit()
            else:
                s.flush()
            s.refresh(c)
            return c
        finally:
            if not self._session:
                s.close()

    def list_consents(self, user_id: int) -> list[Consent]:
        s = self._get_session()
        try:
            return cast(list[Consent], s.query(Consent).filter(Consent.user_id == user_id).all())
        finally:
            if not self._session:
                s.close()

    def list_user_ids_by_scope(self, scope: str) -> list[int]:
        s = self._get_session()
        try:
            rows = (
                s.query(Consent.user_id)
                .filter(Consent.scope == scope, Consent.granted.is_(True))
                .all()
            )
            return [int(row[0]) for row in rows if row and row[0] is not None]
        finally:
            if not self._session:
                s.close()

    def revoke_consent(
        self, user_id: int, scope: str, *, commit: bool = True
    ) -> bool:
        s = self._get_session()
        try:
            c = s.query(Consent).filter(Consent.user_id == user_id, Consent.scope == scope).first()
            if c is None:
                return False
            s.delete(c)
            if commit:
                s.commit()
            else:
                s.flush()
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

                    return bool(c.expires_at > datetime.utcnow())
                except Exception:
                    return False
            return True
        finally:
            if not self._session:
                s.close()


class OAuthTokenRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def upsert(
        self,
        user_id: int,
        provider: str,
        access_token: str,
        refresh_token: str | None,
        expires_at: Any | None,
        *,
        commit: bool = True,
    ) -> OAuthToken:
        s = self._get_session()
        try:
            protected_access = protect_oauth_token(access_token)
            protected_refresh = (
                protect_oauth_token(refresh_token) if refresh_token is not None else None
            )
            tok = (
                s.query(OAuthToken)
                .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
                .first()
            )
            if tok is None:
                tok = OAuthToken(
                    user_id=user_id,
                    provider=provider,
                    access_token=protected_access,
                    refresh_token=protected_refresh,
                    expires_at=expires_at,
                )
                s.add(tok)
            else:
                tok.access_token = protected_access
                tok.refresh_token = (
                    protected_refresh if protected_refresh is not None else tok.refresh_token
                )
                tok.expires_at = expires_at
            if commit:
                s.commit()
            else:
                s.flush()
            s.refresh(tok)
            s.expunge(tok)
            tok.access_token = access_token
            tok.refresh_token = (
                refresh_token
                if refresh_token is not None
                else reveal_oauth_token(tok.refresh_token)
            )
            return tok
        finally:
            if not self._session:
                s.close()

    def get(self, user_id: int, provider: str) -> OAuthToken | None:
        s = self._get_session()
        try:
            tok = (
                s.query(OAuthToken)
                .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
                .first()
            )
            if tok is None:
                return None
            legacy_access = not is_protected_oauth_token(tok.access_token)
            legacy_refresh = bool(
                tok.refresh_token and not is_protected_oauth_token(tok.refresh_token)
            )
            access_token = reveal_oauth_token(tok.access_token)
            refresh_token = reveal_oauth_token(tok.refresh_token)
            if legacy_access or legacy_refresh:
                tok.access_token = protect_oauth_token(access_token or "")
                tok.refresh_token = (
                    protect_oauth_token(refresh_token) if refresh_token else None
                )
                s.commit()
                s.refresh(tok)
            s.expunge(tok)
            tok.access_token = access_token or ""
            tok.refresh_token = refresh_token
            return tok
        finally:
            if not self._session:
                s.close()

    def delete(
        self, user_id: int, provider: str, *, commit: bool = True
    ) -> bool:
        s = self._get_session()
        try:
            tok = (
                s.query(OAuthToken)
                .filter(OAuthToken.user_id == user_id, OAuthToken.provider == provider)
                .first()
            )
            if tok is None:
                return False
            s.delete(tok)
            if commit:
                s.commit()
            else:
                s.flush()
            return True
        finally:
            if not self._session:
                s.close()
