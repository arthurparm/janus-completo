from __future__ import annotations

import hashlib
import json
import threading
from collections.abc import Callable
from typing import Any

from app.core.infrastructure.filesystem_manager import read_file, write_file


class ProductivityRepositoryError(Exception):
    """Productivity data could not be read or durably persisted."""


class ProductivityNotesRepository:
    """Owner-scoped note persistence over the guarded workspace filesystem."""

    _locks = tuple(threading.Lock() for _ in range(64))

    def __init__(
        self,
        *,
        reader: Callable[[str], str] = read_file,
        writer: Callable[[str, str, bool], str] = write_file,
    ) -> None:
        self._reader = reader
        self._writer = writer

    @staticmethod
    def _owner_key(user_id: str) -> str:
        normalized = str(user_id).strip()
        if not normalized:
            raise ProductivityRepositoryError("Identidade do proprietário ausente.")
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    @classmethod
    def _lock_for(cls, owner_key: str) -> threading.Lock:
        return cls._locks[int(owner_key[:8], 16) % len(cls._locks)]

    @classmethod
    def storage_paths(cls, user_id: str) -> tuple[str, str]:
        owner_key = cls._owner_key(user_id)
        relative = f"productivity/users/{owner_key}/notes.json"
        return f"workspace/{relative}", relative

    def list_notes(self, user_id: str) -> list[dict[str, Any]]:
        read_path, _ = self.storage_paths(user_id)
        raw = self._reader(read_path)
        if raw.startswith("Erro:"):
            if "não foi encontrado" in raw or "not found" in raw.lower():
                return []
            raise ProductivityRepositoryError("Falha ao ler as notas do usuário.")
        try:
            payload = json.loads(raw)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ProductivityRepositoryError(
                "Arquivo de notas corrompido; nenhuma gravação foi realizada."
            ) from exc
        if not isinstance(payload, list) or any(not isinstance(item, dict) for item in payload):
            raise ProductivityRepositoryError(
                "Contrato inválido no arquivo de notas; nenhuma gravação foi realizada."
            )
        return payload

    def add_note(self, user_id: str, note: dict[str, Any]) -> int:
        owner_key = self._owner_key(user_id)
        with self._lock_for(owner_key):
            items = self.list_notes(user_id)
            items.append(dict(note))
            _, write_path = self.storage_paths(user_id)
            outcome = self._writer(
                write_path,
                json.dumps(items, ensure_ascii=False),
                True,
            )
            if outcome.startswith("Erro:"):
                raise ProductivityRepositoryError("Falha ao persistir as notas do usuário.")
            return len(items)
