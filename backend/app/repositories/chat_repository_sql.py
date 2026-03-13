import os
from copy import deepcopy
from datetime import datetime
from typing import Any

import structlog
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.db import db
from app.models.user_models import Message
from app.models.user_models import Session as ChatSession
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)


class ChatRepositoryError(Exception):
    pass


class ChatRepositorySQL:
    def __init__(self, session: Session | None = None):
        self._session = session
        self._user_repo = UserRepository(session=session) if session else UserRepository()
        self._use_fallback = bool(os.getenv("PYTEST_CURRENT_TEST")) or os.getenv(
            "CHAT_REPO_FALLBACK", "0"
        ) == "1"
        self._fallback_sessions: dict[int, dict[str, Any]] = {}
        self._fallback_messages: dict[int, list[dict[str, Any]]] = {}
        self._fallback_next_id = 1
        self._fallback_next_msg_id = 1

    def _fallback_ts(self, dt: datetime) -> float:
        return dt.timestamp() if isinstance(dt, datetime) else float(dt)

    def _message_to_dict(self, message: Message | dict[str, Any]) -> dict[str, Any]:
        if isinstance(message, dict):
            payload = {
                "id": message.get("id"),
                "timestamp": self._fallback_ts(message.get("timestamp")),
                "role": message.get("role"),
                "text": message.get("text"),
            }
            for key in (
                "knowledge_space_id",
                "mode_used",
                "base_used",
                "citations",
                "citation_status",
                "ui",
                "source_scope",
                "gaps_or_conflicts",
                "understanding",
                "confirmation",
                "agent_state",
                "delivery_status",
                "failure_classification",
                "provider",
                "model",
            ):
                if key in message and message.get(key) is not None:
                    payload[key] = deepcopy(message.get(key))
            return payload

        payload = {
            "id": str(message.id),
            "timestamp": self._fallback_ts(message.timestamp),
            "role": message.role,
            "text": message.text,
        }
        mapping = {
            "knowledge_space_id": message.knowledge_space_id,
            "mode_used": message.mode_used,
            "base_used": message.base_used,
            "citations": message.citations_json,
            "citation_status": message.citation_status_json,
            "ui": message.ui_json,
            "source_scope": message.source_scope_json,
            "gaps_or_conflicts": message.gaps_or_conflicts_json,
            "understanding": message.understanding_json,
            "confirmation": message.confirmation_json,
            "agent_state": message.agent_state_json,
            "delivery_status": message.delivery_status,
            "failure_classification": message.failure_classification,
            "provider": message.provider,
            "model": message.model,
        }
        for key, value in mapping.items():
            if value is not None:
                payload[key] = deepcopy(value)
        return payload

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return db.get_session_direct()

    def _resolve_user_id(self, user_id: str) -> int | None:
        """
        Resolve different user ID formats to database user ID.
        Supports:
        - Numeric strings: "123" -> 123
        - Current user placeholder: "current-user" -> None (for now)
        - User email or external ID: maps to internal user ID
        """
        if not user_id:
            return None

        # Handle numeric user IDs
        try:
            numeric_id = int(user_id)
            return numeric_id
        except ValueError:
            pass

        # Handle special identifiers
        if user_id == "current-user":
            return None

        return None

    def start_conversation(
        self,
        persona: str | None,
        user_id: str | None,
        project_id: str | None,
        title: str | None = None,
    ) -> str:
        if self._use_fallback:
            sid = self._fallback_next_id
            self._fallback_next_id += 1
            now = datetime.utcnow()
            self._fallback_sessions[sid] = {
                "persona": persona,
                "user_id": str(self._resolve_user_id(user_id)) if user_id else None,
                "project_id": project_id,
                "title": title or "Nova Conversa",
                "created_at": now,
                "updated_at": now,
                "summary": None,
            }
            self._fallback_messages[sid] = []
            return str(sid)
        s = self._get_session()
        try:
            resolved_user_id = self._resolve_user_id(user_id) if user_id else None
            cs = ChatSession(
                user_id=resolved_user_id,
                persona=persona,
                project_id=project_id,
                title=title or "Nova Conversa",
            )
            s.add(cs)
            s.commit()
            s.refresh(cs)
            return str(cs.id)
        finally:
            if not self._session:
                s.close()

    def add_message(
        self,
        conversation_id: str,
        role: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._use_fallback:
            sid = int(conversation_id)
            if sid not in self._fallback_sessions:
                raise ChatRepositoryError("Conversation not found")
            msg = {
                "id": self._fallback_next_msg_id,
                "timestamp": datetime.utcnow(),
                "role": role,
                "text": text,
                **(metadata or {}),
            }
            self._fallback_next_msg_id += 1
            self._fallback_messages.setdefault(sid, []).append(msg)
            self._fallback_sessions[sid]["updated_at"] = datetime.utcnow()
            return self._message_to_dict(msg)
        s = self._get_session()
        try:
            sid = int(conversation_id)
            m = Message(
                session_id=sid,
                role=role,
                text=text,
                knowledge_space_id=(metadata or {}).get("knowledge_space_id"),
                mode_used=(metadata or {}).get("mode_used"),
                base_used=(metadata or {}).get("base_used"),
                citations_json=(metadata or {}).get("citations"),
                citation_status_json=(metadata or {}).get("citation_status"),
                ui_json=(metadata or {}).get("ui"),
                source_scope_json=(metadata or {}).get("source_scope"),
                gaps_or_conflicts_json=(metadata or {}).get("gaps_or_conflicts"),
                understanding_json=(metadata or {}).get("understanding"),
                confirmation_json=(metadata or {}).get("confirmation"),
                agent_state_json=(metadata or {}).get("agent_state"),
                delivery_status=(metadata or {}).get("delivery_status"),
                failure_classification=(metadata or {}).get("failure_classification"),
                provider=(metadata or {}).get("provider"),
                model=(metadata or {}).get("model"),
            )
            s.add(m)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs:
                cs.updated_at = datetime.utcnow()
            s.commit()
            s.refresh(m)
            return self._message_to_dict(m)
        finally:
            if not self._session:
                s.close()

    def get_conversation(self, conversation_id: str) -> dict[str, Any]:
        if self._use_fallback:
            sid = int(conversation_id)
            cs = self._fallback_sessions.get(sid)
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            msgs = self._fallback_messages.get(sid, [])
            return {
                "persona": cs.get("persona"),
                "user_id": cs.get("user_id"),
                "project_id": cs.get("project_id"),
                "title": cs.get("title"),
                "created_at": self._fallback_ts(cs.get("created_at")),
                "updated_at": self._fallback_ts(cs.get("updated_at")),
                "summary": cs.get("summary"),
                "messages": [self._message_to_dict(m) for m in msgs],
            }
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            msgs = (
                s.query(Message)
                .filter(Message.session_id == sid)
                .order_by(Message.timestamp.asc())
                .all()
            )

            def _ts(d: datetime) -> float:
                return d.timestamp() if isinstance(d, datetime) else float(d)

            return {
                "persona": cs.persona,
                "user_id": str(cs.user_id) if cs.user_id is not None else None,
                "project_id": cs.project_id,
                "title": cs.title,
                "created_at": _ts(cs.created_at),
                "updated_at": _ts(cs.updated_at),
                "summary": cs.summary,
                "messages": [self._message_to_dict(m) for m in msgs],
            }
        finally:
            if not self._session:
                s.close()

    def get_history(self, conversation_id: str) -> list[dict[str, Any]]:
        return list(self.get_conversation(conversation_id)["messages"])

    def get_history_paginated(
        self,
        conversation_id: str,
        limit: int = 50,
        offset: int = 0,
        before_ts: float | None = None,
        after_ts: float | None = None,
    ) -> dict[str, Any]:
        """
        Retorna histórico paginado de mensagens com metadados.

        Args:
            conversation_id: ID da conversa
            limit: Número máximo de mensagens (max 200)
            offset: Número de mensagens a pular
            before_ts: Timestamp para buscar mensagens antes desta data
            after_ts: Timestamp para buscar mensagens após esta data

        Returns:
            Dict com messages, total_count, has_more, next_offset
        """
        if self._use_fallback:
            sid = int(conversation_id)
            msgs = list(self._fallback_messages.get(sid, []))
            if before_ts:
                msgs = [m for m in msgs if self._fallback_ts(m["timestamp"]) < before_ts]
            if after_ts:
                msgs = [m for m in msgs if self._fallback_ts(m["timestamp"]) > after_ts]
            total_count = len(msgs)
            msgs = msgs[offset : offset + limit]
            result_messages = [self._message_to_dict(m) for m in msgs]
            has_more = (offset + len(result_messages)) < total_count
            next_offset = offset + len(result_messages) if has_more else None
            return {
                "messages": result_messages,
                "total_count": total_count,
                "has_more": has_more,
                "next_offset": next_offset,
                "limit": limit,
                "offset": offset,
            }
        s = self._get_session()
        try:
            sid = int(conversation_id)

            # Query base
            q = s.query(Message).filter(Message.session_id == sid)

            # Filtros por timestamp
            if before_ts:
                q = q.filter(Message.timestamp < datetime.fromtimestamp(before_ts))
            if after_ts:
                q = q.filter(Message.timestamp > datetime.fromtimestamp(after_ts))

            # Conta total de mensagens (sem limite)
            total_count = q.count()

            # Aplica ordenação e paginação
            messages = q.order_by(Message.timestamp.asc()).offset(offset).limit(limit).all()

            def _ts(d: datetime) -> float:
                return d.timestamp() if isinstance(d, datetime) else float(d)

            result_messages = [self._message_to_dict(m) for m in messages]

            has_more = (offset + len(result_messages)) < total_count
            next_offset = offset + len(result_messages) if has_more else None

            return {
                "messages": result_messages,
                "total_count": total_count,
                "has_more": has_more,
                "next_offset": next_offset,
                "limit": limit,
                "offset": offset,
            }

        finally:
            if not self._session:
                s.close()

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> list[dict[str, Any]]:
        hist = self.get_history(conversation_id)
        return hist[-limit:] if limit > 0 else hist

    def list_conversations(
        self, user_id: str | None = None, project_id: str | None = None, limit: int = 50
    ) -> list[dict[str, Any]]:
        if self._use_fallback:
            items = list(self._fallback_sessions.items())
            items = items[-limit:]
            result: list[dict[str, Any]] = []
            for sid, cs in items:
                msgs = self._fallback_messages.get(sid, [])
                last = msgs[-1] if msgs else None
                last_dict = None
                if last:
                    last_dict = self._message_to_dict(last)
                result.append(
                    {
                        "conversation_id": str(sid),
                        "title": cs.get("title"),
                        "created_at": self._fallback_ts(cs.get("created_at")),
                        "updated_at": self._fallback_ts(cs.get("updated_at")),
                        "last_message": last_dict,
                    }
                )
            return result
        s = self._get_session()
        try:
            q = s.query(ChatSession)

            # Use the resolved user_id instead of direct int conversion
            if user_id:
                resolved_user_id = self._resolve_user_id(user_id)
                if resolved_user_id is not None:
                    q = q.filter(ChatSession.user_id == resolved_user_id)
            if project_id:
                q = q.filter(ChatSession.project_id == project_id)
            items = q.order_by(desc(ChatSession.updated_at)).limit(limit).all()

            def _ts(d: datetime) -> float:
                return d.timestamp() if isinstance(d, datetime) else float(d)

            result: list[dict[str, Any]] = []
            for cs in items:
                last = (
                    s.query(Message)
                    .filter(Message.session_id == cs.id)
                    .order_by(Message.timestamp.desc())
                    .first()
                )
                last_dict = None
                if last:
                    last_dict = self._message_to_dict(last)
                result.append(
                    {
                        "conversation_id": str(cs.id),
                        "title": cs.title,
                        "created_at": _ts(cs.created_at),
                        "updated_at": _ts(cs.updated_at),
                        "last_message": last_dict,
                    }
                )
            return result
        finally:
            if not self._session:
                s.close()

    def rename_conversation(
        self,
        conversation_id: str,
        new_title: str,
        user_id: str | None = None,
        project_id: str | None = None,
    ) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            cs = self._fallback_sessions.get(sid)
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            cs["title"] = new_title
            cs["updated_at"] = datetime.utcnow()
            return
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            if project_id and cs.project_id and cs.project_id != project_id:
                raise ChatRepositoryError("Access denied: project_id mismatch")
            cs.title = new_title
            cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def delete_conversation(
        self, conversation_id: str, user_id: str | None = None, project_id: str | None = None
    ) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            if sid not in self._fallback_sessions:
                raise ChatRepositoryError("Conversation not found")
            self._fallback_sessions.pop(sid, None)
            self._fallback_messages.pop(sid, None)
            return
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            if project_id and cs.project_id and cs.project_id != project_id:
                raise ChatRepositoryError("Access denied: project_id mismatch")
            s.delete(cs)
            s.commit()
        finally:
            if not self._session:
                s.close()

    def update_message_text(
        self, conversation_id: str, message_id: int, new_text: str, user_id: str | None = None
    ) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            msgs = self._fallback_messages.get(sid, [])
            msg = next((m for m in msgs if int(m.get("id")) == int(message_id)), None)
            if msg is None:
                raise ChatRepositoryError("Message not found")
            msg["text"] = new_text
            self._fallback_sessions[sid]["updated_at"] = datetime.utcnow()
            return
        s = self._get_session()
        try:
            sid = int(conversation_id)
            msg = (
                s.query(Message)
                .filter(Message.id == int(message_id), Message.session_id == sid)
                .first()
            )
            if msg is None:
                raise ChatRepositoryError("Message not found")
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            msg.text = new_text
            cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def replace_last_assistant_message(
        self, conversation_id: str, new_text: str, user_id: str | None = None
    ) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            if sid not in self._fallback_sessions:
                raise ChatRepositoryError("Conversation not found")
            msgs = self._fallback_messages.get(sid, [])
            for msg in reversed(msgs):
                if str(msg.get("role")) == "assistant":
                    msg["text"] = new_text
                    self._fallback_sessions[sid]["updated_at"] = datetime.utcnow()
                    return
            raise ChatRepositoryError("Assistant message not found")
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")

            msg = (
                s.query(Message)
                .filter(Message.session_id == sid, Message.role == "assistant")
                .order_by(desc(Message.timestamp), desc(Message.id))
                .first()
            )
            if msg is None:
                raise ChatRepositoryError("Assistant message not found")
            msg.text = new_text
            cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def get_last_assistant_message(
        self, conversation_id: str, user_id: str | None = None
    ) -> dict[str, Any]:
        if self._use_fallback:
            sid = int(conversation_id)
            if sid not in self._fallback_sessions:
                raise ChatRepositoryError("Conversation not found")
            for msg in reversed(self._fallback_messages.get(sid, [])):
                if str(msg.get("role")) == "assistant":
                    return self._message_to_dict(msg)
            raise ChatRepositoryError("Assistant message not found")
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            msg = (
                s.query(Message)
                .filter(Message.session_id == sid, Message.role == "assistant")
                .order_by(desc(Message.timestamp), desc(Message.id))
                .first()
            )
            if msg is None:
                raise ChatRepositoryError("Assistant message not found")
            return self._message_to_dict(msg)
        finally:
            if not self._session:
                s.close()

    def update_message_payload(
        self,
        conversation_id: str,
        message_id: int,
        patch: dict[str, Any],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        if self._use_fallback:
            sid = int(conversation_id)
            msgs = self._fallback_messages.get(sid, [])
            msg = next((m for m in msgs if int(m.get("id") or 0) == int(message_id)), None)
            if msg is None:
                raise ChatRepositoryError("Message not found")
            for key, value in patch.items():
                if value is None:
                    msg.pop(key, None)
                else:
                    msg[key] = deepcopy(value)
            self._fallback_sessions[sid]["updated_at"] = datetime.utcnow()
            return self._message_to_dict(msg)
        s = self._get_session()
        try:
            sid = int(conversation_id)
            msg = (
                s.query(Message)
                .filter(Message.id == int(message_id), Message.session_id == sid)
                .first()
            )
            if msg is None:
                raise ChatRepositoryError("Message not found")
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            mapping = {
                "text": "text",
                "knowledge_space_id": "knowledge_space_id",
                "mode_used": "mode_used",
                "base_used": "base_used",
                "citations": "citations_json",
                "citation_status": "citation_status_json",
                "ui": "ui_json",
                "source_scope": "source_scope_json",
                "gaps_or_conflicts": "gaps_or_conflicts_json",
                "understanding": "understanding_json",
                "confirmation": "confirmation_json",
                "agent_state": "agent_state_json",
                "delivery_status": "delivery_status",
                "failure_classification": "failure_classification",
                "provider": "provider",
                "model": "model",
            }
            for key, column_name in mapping.items():
                if key not in patch:
                    continue
                setattr(msg, column_name, deepcopy(patch.get(key)))
            cs.updated_at = datetime.utcnow()
            s.commit()
            s.refresh(msg)
            return self._message_to_dict(msg)
        finally:
            if not self._session:
                s.close()

    def delete_message(
        self, conversation_id: str, message_id: int, user_id: str | None = None
    ) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            msgs = self._fallback_messages.get(sid, [])
            idx = next(
                (i for i, m in enumerate(msgs) if int(m.get("id")) == int(message_id)),
                None,
            )
            if idx is None:
                raise ChatRepositoryError("Message not found")
            msgs.pop(idx)
            self._fallback_sessions[sid]["updated_at"] = datetime.utcnow()
            return
        s = self._get_session()
        try:
            sid = int(conversation_id)
            msg = (
                s.query(Message)
                .filter(Message.id == int(message_id), Message.session_id == sid)
                .first()
            )
            if msg is None:
                raise ChatRepositoryError("Message not found")
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            if user_id:
                uid = self._resolve_user_id(user_id)
                if uid is not None and cs.user_id is not None and cs.user_id != uid:
                    if not self._user_repo.is_admin(uid):
                        raise ChatRepositoryError("Access denied: user_id mismatch")
            s.delete(msg)
            cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def update_summary(self, conversation_id: str, summary: str | None) -> None:
        if self._use_fallback:
            sid = int(conversation_id)
            cs = self._fallback_sessions.get(sid)
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            cs["summary"] = summary
            cs["updated_at"] = datetime.utcnow()
            return
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            cs.summary = summary
            cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def count_messages(self, conversation_id: str) -> int:
        """Conta o número total de mensagens em uma conversa."""
        if self._use_fallback:
            sid = int(conversation_id)
            return len(self._fallback_messages.get(sid, []))
        s = self._get_session()
        try:
            sid = int(conversation_id)
            return s.query(Message).filter(Message.session_id == sid).count()
        finally:
            if not self._session:
                s.close()

    def count_conversations(self) -> int:
        if self._use_fallback:
            return len(self._fallback_sessions)
        s = self._get_session()
        try:
            return s.query(ChatSession).count()
        finally:
            if not self._session:
                s.close()
