from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db import db
from app.models.tool_usage_models import ToolDailyUsage


class ToolUsageRepository:
    def __init__(self, session: Session | None = None):
        self._session = session

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def increment_if_within_limit(
        self, user_id: str, tool_name: str, daily_limit: int
    ) -> tuple[bool, int, int]:
        """
        Incrementa o uso diário se ainda estiver dentro do limite.
        Retorna (allowed, current_count, limit).
        """
        if daily_limit is None or daily_limit <= 0:
            return True, 0, daily_limit

        session = self._get_session()
        try:
            today = datetime.now(timezone.utc).date()
            row = (
                session.query(ToolDailyUsage)
                .filter(
                    ToolDailyUsage.user_id == user_id,
                    ToolDailyUsage.tool_name == tool_name,
                    ToolDailyUsage.usage_date == today,
                )
                .with_for_update()
                .first()
            )

            if not row:
                row = ToolDailyUsage(
                    user_id=user_id, tool_name=tool_name, usage_date=today, count=0
                )
                session.add(row)
                session.flush()

            if row.count >= daily_limit:
                session.rollback()
                return False, row.count, daily_limit

            row.count += 1
            session.commit()
            session.refresh(row)
            return True, row.count, daily_limit
        finally:
            if not self._session:
                session.close()
