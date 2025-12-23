import structlog
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from app.db.mysql_config import mysql_db
from app.models.user_models import Session as ChatSession, Message
from app.repositories.user_repository import UserRepository

logger = structlog.get_logger(__name__)

class ChatRepositoryError(Exception):
    pass

class ChatRepositorySQL:
    def __init__(self, session: Optional[Session] = None):
        self._session = session
        self._user_repo = UserRepository(session=session) if session else UserRepository()

    def _get_session(self) -> Session:
        if self._session:
            return self._session
        return mysql_db.get_session_direct()

    def _resolve_user_id(self, user_id: str) -> Optional[int]:
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
        if user_id == 'current-user':
            return None
        
        return None

    def start_conversation(self, persona: Optional[str], user_id: Optional[str], project_id: Optional[str], title: Optional[str] = None) -> str:
        s = self._get_session()
        try:
            resolved_user_id = self._resolve_user_id(user_id) if user_id else None
            cs = ChatSession(user_id=resolved_user_id, persona=persona, project_id=project_id, title=title or "Nova Conversa")
            s.add(cs)
            s.commit()
            s.refresh(cs)
            return str(cs.id)
        finally:
            if not self._session:
                s.close()

    def add_message(self, conversation_id: str, role: str, text: str) -> None:
        s = self._get_session()
        try:
            sid = int(conversation_id)
            m = Message(session_id=sid, role=role, text=text)
            s.add(m)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs:
                cs.updated_at = datetime.utcnow()
            s.commit()
        finally:
            if not self._session:
                s.close()

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        s = self._get_session()
        try:
            sid = int(conversation_id)
            cs = s.query(ChatSession).filter(ChatSession.id == sid).first()
            if cs is None:
                raise ChatRepositoryError("Conversation not found")
            msgs = s.query(Message).filter(Message.session_id == sid).order_by(Message.timestamp.asc()).all()
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
                "messages": [{"timestamp": _ts(m.timestamp), "role": m.role, "text": m.text} for m in msgs],
            }
        finally:
            if not self._session:
                s.close()

    def get_history(self, conversation_id: str) -> List[Dict[str, Any]]:
        return list(self.get_conversation(conversation_id)["messages"])

    def get_history_paginated(self, conversation_id: str, limit: int = 50, offset: int = 0, 
                             before_ts: Optional[float] = None, after_ts: Optional[float] = None) -> Dict[str, Any]:
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
                
            result_messages = [
                {"timestamp": _ts(m.timestamp), "role": m.role, "text": m.text} 
                for m in messages
            ]
            
            has_more = (offset + len(result_messages)) < total_count
            next_offset = offset + len(result_messages) if has_more else None
            
            return {
                "messages": result_messages,
                "total_count": total_count,
                "has_more": has_more,
                "next_offset": next_offset,
                "limit": limit,
                "offset": offset
            }
            
        finally:
            if not self._session:
                s.close()

    def get_recent_messages(self, conversation_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        hist = self.get_history(conversation_id)
        return hist[-limit:] if limit > 0 else hist

    def list_conversations(self, user_id: Optional[str] = None, project_id: Optional[str] = None, limit: int = 50) -> List[Dict[str, Any]]:
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
            result: List[Dict[str, Any]] = []
            for cs in items:
                last = s.query(Message).filter(Message.session_id == cs.id).order_by(Message.timestamp.desc()).first()
                last_dict = None
                if last:
                    last_dict = {"timestamp": _ts(last.timestamp), "role": last.role, "text": last.text}
                result.append({
                    "conversation_id": str(cs.id),
                    "title": cs.title,
                    "created_at": _ts(cs.created_at),
                    "updated_at": _ts(cs.updated_at),
                    "last_message": last_dict,
                })
            return result
        finally:
            if not self._session:
                s.close()

    def rename_conversation(self, conversation_id: str, new_title: str, user_id: Optional[str] = None, project_id: Optional[str] = None) -> None:
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

    def delete_conversation(self, conversation_id: str, user_id: Optional[str] = None, project_id: Optional[str] = None) -> None:
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

    def update_message_text(self, conversation_id: str, message_id: int, new_text: str, user_id: Optional[str] = None) -> None:
        s = self._get_session()
        try:
            sid = int(conversation_id)
            msg = s.query(Message).filter(Message.id == int(message_id), Message.session_id == sid).first()
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

    def delete_message(self, conversation_id: str, message_id: int, user_id: Optional[str] = None) -> None:
        s = self._get_session()
        try:
            sid = int(conversation_id)
            msg = s.query(Message).filter(Message.id == int(message_id), Message.session_id == sid).first()
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

    def update_summary(self, conversation_id: str, summary: Optional[str]) -> None:
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
        s = self._get_session()
        try:
            sid = int(conversation_id)
            return s.query(Message).filter(Message.session_id == sid).count()
        finally:
            if not self._session:
                s.close()

    def count_conversations(self) -> int:
        s = self._get_session()
        try:
            return s.query(ChatSession).count()
        finally:
            if not self._session:
                s.close()