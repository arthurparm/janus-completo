from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .facade import KnowledgeFacade


_knowledge_facade: "KnowledgeFacade | None" = None


def set_knowledge_facade(facade: "KnowledgeFacade") -> None:
    global _knowledge_facade
    _knowledge_facade = facade


def get_knowledge_facade() -> "KnowledgeFacade":
    if _knowledge_facade is None:
        raise RuntimeError("KnowledgeFacade is not initialized")
    return _knowledge_facade

