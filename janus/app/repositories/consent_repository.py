from sqlalchemy.orm import Session

from app.db.mysql_config import mysql_db
from app.models.consent_models import Consent


class ConsentRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def is_granted(self, user_id: str, scope: str) -> bool:
        s = self._get_session()
        try:
            c = (
                s.query(Consent)
                .filter(Consent.user_id == user_id, Consent.scope == scope)
                .order_by(Consent.created_at.desc())
                .first()
            )
            if not c:
                return False
            return (c.granted or "True") == "True" and c.revoked_at is None
        finally:
            if not self._session:
                s.close()
