from typing import Any

__all__ = [
    "MemoryCore",
    "close_memory_db",
    "get_memory_db",
    "initialize_memory_db",
]


def __getattr__(name: str) -> Any:
    """Load memory-core exports lazily to avoid vector-store import cycles."""
    if name not in __all__:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from .memory_core import MemoryCore, close_memory_db, get_memory_db, initialize_memory_db

    exports = {
        "MemoryCore": MemoryCore,
        "close_memory_db": close_memory_db,
        "get_memory_db": get_memory_db,
        "initialize_memory_db": initialize_memory_db,
    }
    return exports[name]
