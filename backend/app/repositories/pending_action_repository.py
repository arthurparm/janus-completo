import json
from datetime import datetime

from app.db import db
from app.models.pending_action_models import PendingAction
from sqlalchemy import desc
from sqlalchemy.orm import Session


class PendingActionRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def create(
        self,
        user_id: str | None,
        tool_name: str,
        args_json: str,
        run_id: int | None,
        cycle: int | None,
        simulation_summary_json: str | None = None,
        simulation_generated_at: datetime | None = None,
        simulation_version: str | None = None,
    ) -> PendingAction:
        normalized_user_id = str(user_id).strip() if user_id is not None else ""
        if not normalized_user_id:
            raise ValueError("pending_actions require persisted user_id")
        s = self._get_session()
        try:
            p = PendingAction(
                user_id=normalized_user_id,
                tool_name=tool_name,
                args_json=args_json,
                run_id=run_id,
                cycle=cycle,
                simulation_summary_json=simulation_summary_json,
                simulation_generated_at=simulation_generated_at,
                simulation_version=simulation_version,
            )
            s.add(p)
            s.commit()
            s.refresh(p)
            return p
        finally:
            if not self._session:
                s.close()

    def list_without_owner(self, limit: int = 500) -> list[PendingAction]:
        s = self._get_session()
        try:
            return (
                s.query(PendingAction)
                .filter(PendingAction.user_id.is_(None))
                .order_by(desc(PendingAction.created_at))
                .limit(limit)
                .all()
            )
        finally:
            if not self._session:
                s.close()

    @staticmethod
    def _extract_conversation_id(args_json: str | None) -> str | None:
        if not args_json:
            return None
        try:
            parsed = json.loads(args_json)
        except Exception:
            return None
        if not isinstance(parsed, dict):
            return None
        conversation_id = parsed.get("conversation_id")
        if conversation_id is None:
            return None
        text = str(conversation_id).strip()
        return text or None

    def count_without_owner(self, status: str | None = None) -> int:
        s = self._get_session()
        try:
            q = s.query(PendingAction).filter(PendingAction.user_id.is_(None))
            if status:
                q = q.filter(PendingAction.status == status)
            return int(q.count())
        finally:
            if not self._session:
                s.close()

    def get_legacy_residue_summary(self, limit: int = 20) -> dict[str, object]:
        sample_limit = max(1, int(limit))
        rows = self.list_without_owner(limit=sample_limit)
        pending_count = self.count_without_owner(status="pending")
        total_count = self.count_without_owner()
        items = [
            {
                "action_id": getattr(item, "id", None),
                "status": getattr(item, "status", None),
                "tool_name": getattr(item, "tool_name", None),
                "created_at": (
                    getattr(item, "created_at", None).isoformat()
                    if getattr(item, "created_at", None) is not None
                    else None
                ),
                "conversation_id": self._extract_conversation_id(getattr(item, "args_json", None)),
            }
            for item in rows
        ]
        return {
            "total_without_owner": total_count,
            "pending_without_owner": pending_count,
            "sample_limit": sample_limit,
            "legacy_runtime_fallback_enabled": False,
            "message": (
                "Operational legacy is extinct. Historical pending_actions without persisted "
                "owner remain blocked as administrative backlog until controlled sanitation; "
                "new ownerless records are rejected."
            ),
            "items": items,
        }

    def assign_user_id(self, action_id: int, user_id: str) -> PendingAction | None:
        normalized_user_id = str(user_id or "").strip()
        if not normalized_user_id:
            raise ValueError("pending_actions require persisted user_id")
        s = self._get_session()
        try:
            pending = s.query(PendingAction).filter(PendingAction.id == action_id).first()
            if pending is None:
                return None
            pending.user_id = normalized_user_id
            s.commit()
            s.refresh(pending)
            return pending
        finally:
            if not self._session:
                s.close()

    def list(
        self, status: str | None = "pending", limit: int = 50, user_id: str | None = None
    ) -> list[PendingAction]:
        s = self._get_session()
        try:
            q = s.query(PendingAction)
            if status:
                q = q.filter(PendingAction.status == status)
            if user_id is not None:
                q = q.filter(PendingAction.user_id == str(user_id))
            return q.order_by(desc(PendingAction.created_at)).limit(limit).all()
        finally:
            if not self._session:
                s.close()

    def get(self, action_id: int, user_id: str | None = None) -> PendingAction | None:
        s = self._get_session()
        try:
            q = s.query(PendingAction).filter(PendingAction.id == action_id)
            if user_id is not None:
                q = q.filter(PendingAction.user_id == str(user_id))
            return q.first()
        finally:
            if not self._session:
                s.close()

    def set_status(
        self, action_id: int, status: str, user_id: str | None = None
    ) -> PendingAction | None:
        s = self._get_session()
        try:
            q = s.query(PendingAction).filter(PendingAction.id == action_id)
            if user_id is not None:
                q = q.filter(PendingAction.user_id == str(user_id))
            p = q.first()
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
