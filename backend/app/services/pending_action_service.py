"""Domain service for creating and managing durable pending actions."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Protocol, cast

from app.models.pending_action_models import PendingAction
from app.services.chat.risk_policy import evaluate_confirmation_risk

_PENDING_ACTION_ID_RE = re.compile(
    r"(?:pending\s*action\s*id|pending[_\s-]*action[_\s-]*id)\s*[:=#-]?\s*(\d+)",
    re.IGNORECASE,
)


def extract_pending_action_id_from_text(text: str | None) -> int | None:
    """Extract only durable numeric pending-action identifiers from model text."""

    if not text:
        return None
    match = _PENDING_ACTION_ID_RE.search(text)
    if not match:
        return None
    return int(match.group(1))


class PendingActionRepositoryPort(Protocol):
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
    ) -> PendingAction: ...

    def get(self, action_id: int, user_id: str | None = None) -> PendingAction | None: ...

    def list(
        self,
        status: str | None = "pending",
        limit: int = 50,
        user_id: str | None = None,
    ) -> list[PendingAction]: ...

    def set_status(
        self,
        action_id: int,
        status: str,
        user_id: str | None = None,
    ) -> PendingAction | None: ...


def _default_repository_factory() -> PendingActionRepositoryPort:
    from app.repositories.pending_action_repository import PendingActionRepository

    return cast(PendingActionRepositoryPort, PendingActionRepository())


class PendingActionService:
    """Single boundary for pending-action validation and persistence rules."""

    VALID_STATUSES = frozenset({"pending", "approved", "rejected", "expired", "executed"})

    def __init__(
        self,
        repository_factory: Callable[[], PendingActionRepositoryPort] | None = None,
    ) -> None:
        self._repository_factory = repository_factory or _default_repository_factory

    @staticmethod
    def _normalize_user_id(user_id: str | None) -> str:
        normalized = str(user_id or "").strip()
        if not normalized:
            raise ValueError("pending_actions require persisted user_id")
        return normalized

    @staticmethod
    def _normalize_action_id(action_id: int) -> int:
        if isinstance(action_id, bool):
            raise ValueError("pending action id must be a positive integer")
        normalized = int(action_id)
        if normalized <= 0:
            raise ValueError("pending action id must be a positive integer")
        return normalized

    def create(
        self,
        *,
        user_id: str | None,
        tool_name: str,
        args: Mapping[str, object],
        run_id: int | None = None,
        cycle: int | None = None,
        simulation_summary_json: str | None = None,
        simulation_generated_at: datetime | None = None,
        simulation_version: str | None = None,
    ) -> int:
        normalized_user_id = self._normalize_user_id(user_id)
        normalized_tool_name = str(tool_name or "").strip()
        if not normalized_tool_name:
            raise ValueError("pending action tool_name is required")
        pending = self._repository_factory().create(
            user_id=normalized_user_id,
            tool_name=normalized_tool_name,
            args_json=json.dumps(args, ensure_ascii=False),
            run_id=run_id,
            cycle=cycle,
            simulation_summary_json=simulation_summary_json,
            simulation_generated_at=simulation_generated_at,
            simulation_version=simulation_version,
        )
        pending_id = getattr(pending, "id", None)
        if isinstance(pending_id, bool) or pending_id is None or int(pending_id) <= 0:
            raise RuntimeError("pending action repository returned no durable id")
        return int(pending_id)

    def resolve_chat_confirmation(
        self,
        *,
        message: str,
        assistant_response: str | None = None,
        conversation_id: str | None = None,
        user_id: str | None = None,
        existing_pending_action_id: int | None = None,
        understanding: Mapping[str, object] | None = None,
    ) -> tuple[int | None, str | None]:
        assessment = evaluate_confirmation_risk(
            message=message,
            assistant_response=assistant_response,
            understanding=understanding,
            existing_pending_action_id=existing_pending_action_id,
        )
        if existing_pending_action_id is not None:
            normalized_action_id = self._normalize_action_id(existing_pending_action_id)
            normalized_user_id = self._normalize_user_id(user_id)
            owned_action = self._repository_factory().get(
                normalized_action_id,
                user_id=normalized_user_id,
            )
            if owned_action is not None:
                return normalized_action_id, assessment.reason
            assessment = evaluate_confirmation_risk(
                message=message,
                assistant_response=assistant_response,
                understanding=understanding,
                existing_pending_action_id=None,
            )
        if not assessment.requires_pending_action:
            return None, assessment.reason
        pending_id = self.create(
            user_id=user_id,
            tool_name="chat_high_risk_request",
            args={
                "source": "chat_confirmation_fallback",
                "conversation_id": conversation_id,
                "message": message,
                "risk_reason": assessment.reason,
                "user_id": user_id,
            },
        )
        return pending_id, assessment.reason

    def get(self, *, action_id: int, user_id: str | None) -> PendingAction | None:
        return self._repository_factory().get(
            self._normalize_action_id(action_id),
            user_id=self._normalize_user_id(user_id),
        )

    def get_for_access_review(self, *, action_id: int) -> PendingAction | None:
        """Load an action before the API applies its explicit ownership contract."""

        return self._repository_factory().get(self._normalize_action_id(action_id))

    def list(
        self,
        *,
        user_id: str | None,
        status: str | None = "pending",
        limit: int = 50,
    ) -> list[PendingAction]:
        normalized_limit = max(1, min(500, int(limit)))
        return self._repository_factory().list(
            status=status,
            limit=normalized_limit,
            user_id=self._normalize_user_id(user_id),
        )

    def update_status(
        self,
        *,
        action_id: int,
        status: str,
        user_id: str | None,
    ) -> PendingAction | None:
        normalized_status = str(status or "").strip().lower()
        if normalized_status not in self.VALID_STATUSES:
            raise ValueError(f"invalid pending action status: {normalized_status or '<empty>'}")
        return self._repository_factory().set_status(
            self._normalize_action_id(action_id),
            normalized_status,
            user_id=self._normalize_user_id(user_id),
        )


def get_pending_action_service() -> PendingActionService:
    """FastAPI dependency factory for the pending-action domain boundary."""

    return PendingActionService()
