from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.db.mysql_config import mysql_db
from app.models.pending_action_models import PendingAction

class PendingActionRepository:
    def __init__(self, session: Optional[Session] = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def create(self, user_id: str, tool_name: str, args_json: str, run_id: Optional[int], cycle: Optional[int]) -> PendingAction:
        s = self._get_session()
        try:
            p = PendingAction(user_id=user_id, tool_name=tool_name, args_json=args_json, run_id=run_id, cycle=cycle)
            s.add(p)
            s.commit()
            s.refresh(p)
            return p
        finally:
            if not self._session:
                s.close()

    def list(self, user_id: Optional[str] = None, status: Optional[str] = "pending", limit: int = 50) -> List[PendingAction]:
        s = self._get_session()
        try:
            q = s.query(PendingAction)
            if user_id:
                q = q.filter(PendingAction.user_id == user_id)
            if status:
                q = q.filter(PendingAction.status == status)
            return q.order_by(desc(PendingAction.created_at)).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def get(self, action_id: int) -> Optional[PendingAction]:
        s = self._get_session()
        try:
            return s.query(PendingAction).filter(PendingAction.id == action_id).first()
        finally:
            if not self._session:
                s.close()

    def set_status(self, action_id: int, status: str) -> Optional[PendingAction]:
        s = self._get_session()
        try:
            p = s.query(PendingAction).filter(PendingAction.id == action_id).first()
            if not p:
                return None
            from datetime import datetime
            p.status = status
            p.decided_at = datetime.utcnow()
            s.commit()
            s.refresh(p)
            return p
        finally:
            if not self._session:
                s.close()