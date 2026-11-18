from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from app.db import db
from app.models.feedback_models import FeedbackEntry
from app.repositories.chat_repository_sql import ChatRepositoryError, ChatRepositorySQL
from sqlalchemy.orm import Session


class OwnedConversationNotFoundError(LookupError):
    pass


class FeedbackRepository:
    def __init__(self, session: Session | None = None) -> None:
        self._session = session

    def _get_session(self) -> Session:
        return self._session or db.get_session_direct()

    def assert_owned_conversation(
        self, *, owner_user_id: int, conversation_id: str, message_id: str | None = None
    ) -> None:
        repo = ChatRepositorySQL(session=self._session) if self._session else ChatRepositorySQL()
        try:
            conversation = repo.get_conversation(conversation_id)
        except (ChatRepositoryError, TypeError, ValueError) as exc:
            raise OwnedConversationNotFoundError from exc
        if str(conversation.get("user_id")) != str(owner_user_id):
            raise OwnedConversationNotFoundError
        if message_id is not None and not any(
            str(message.get("id")) == str(message_id)
            for message in conversation.get("messages", [])
        ):
            raise OwnedConversationNotFoundError

    def create(
        self,
        *,
        feedback_id: str,
        owner_user_id: int,
        conversation_id: str,
        message_id: str | None,
        rating: str,
        feedback_type: str,
        comment: str | None,
        context: dict[str, Any],
    ) -> FeedbackEntry:
        self.assert_owned_conversation(
            owner_user_id=owner_user_id,
            conversation_id=conversation_id,
            message_id=message_id,
        )
        session = self._get_session()
        try:
            entry = FeedbackEntry(
                id=feedback_id,
                owner_user_id=owner_user_id,
                conversation_id=conversation_id,
                message_id=message_id,
                rating=rating,
                feedback_type=feedback_type,
                comment=comment,
                context_json=context,
            )
            session.add(entry)
            session.commit()
            session.refresh(entry)
            return entry
        finally:
            if not self._session:
                session.close()

    def list_for_owner(
        self,
        *,
        owner_user_id: int,
        since: datetime | None = None,
        conversation_id: str | None = None,
    ) -> list[FeedbackEntry]:
        session = self._get_session()
        try:
            query = session.query(FeedbackEntry).filter(
                FeedbackEntry.owner_user_id == owner_user_id
            )
            if since is not None:
                query = query.filter(FeedbackEntry.created_at >= since)
            if conversation_id is not None:
                self.assert_owned_conversation(
                    owner_user_id=owner_user_id, conversation_id=conversation_id
                )
                query = query.filter(FeedbackEntry.conversation_id == conversation_id)
            return cast(
                list[FeedbackEntry], query.order_by(FeedbackEntry.created_at.desc()).all()
            )
        finally:
            if not self._session:
                session.close()

    def list_global(self, *, rating: str | None = None, limit: int = 1000) -> list[FeedbackEntry]:
        session = self._get_session()
        try:
            query = session.query(FeedbackEntry)
            if rating:
                query = query.filter(FeedbackEntry.rating == rating)
            return cast(
                list[FeedbackEntry],
                query.order_by(FeedbackEntry.created_at.desc()).limit(limit).all(),
            )
        finally:
            if not self._session:
                session.close()
