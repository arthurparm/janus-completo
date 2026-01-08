import time
import uuid
import sqlite3
import shutil
import os
import json
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional

import structlog
from fastapi import Request

from app.services.memory_service import MemoryService
from app.config import settings
from app.core.infrastructure.firebase import get_firebase_service

logger = structlog.get_logger(__name__)


class GoalStatus(str):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Goal:
    id: str
    title: str
    description: str
    priority: int = 5  # 1 alta, 10 baixa
    status: str = GoalStatus.PENDING
    success_criteria: Optional[str] = None
    deadline_ts: Optional[float] = None
    created_at: float = field(default_factory=lambda: time.time())
    updated_at: float = field(default_factory=lambda: time.time())

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        valid_keys = cls.__dataclass_fields__.keys()
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)


class GoalManager:
    """Gerenciador de metas com armazenamento em memória e persistência no Firestore (se configurado)."""

    def __init__(self, memory_service: MemoryService):
        self._memory_service = memory_service
        self._goals: Dict[str, Goal] = {}
        self._firestore_enabled = getattr(settings, "FIREBASE_ENABLED", False)
        self._collection = "goals"
        self._db_path = settings.SQLITE_DB_PATH

        self._init_sqlite()
        self._load_from_sqlite()

        # If Firestore is enabled, it might be used for initial migration or secondary sync
        if self._firestore_enabled:
            # Optionally, you might want to reconcile data between SQLite and Firestore here
            # For now, we'll assume SQLite is the source of truth on startup.
            pass

    def _init_sqlite(self):
        """Inicializa SQLite com 'Maximum Robustness': Check, Backup, Connect."""
        try:
            # 1. Self-Healing: Integrity Check on Boot
            if os.path.exists(self._db_path):
                try:
                    with sqlite3.connect(self._db_path) as conn:
                        cursor = conn.execute("PRAGMA integrity_check")
                        result = cursor.fetchone()[0]
                        if result != "ok":
                            logger.critical(f"SQLite CORRUPTED ({result}). Initiating Emergency Restore...")
                            self._restore_from_backup()
                except sqlite3.DatabaseError:
                    logger.critical("SQLite completely unreadable. Initiating Emergency Restore...")
                    self._restore_from_backup()

            # 2. Time Machine: Rolling Backup
            self._rotate_backups()

            # 3. Connection & Optimization
            with sqlite3.connect(self._db_path) as conn:
                conn.execute("PRAGMA journal_mode=WAL;") 
                conn.execute("PRAGMA synchronous=NORMAL;")
                conn.execute("PRAGMA optimize;") # Auto-vacuum logic
                
                # Table 1: Snapshots (Fast Read State)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS snapshots (
                        id TEXT PRIMARY KEY,
                        data JSON,
                        updated_at REAL
                    )
                """)
                
                # Table 2: Events (Audit Log / Time Travel)
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS events (
                        seq INTEGER PRIMARY KEY AUTOINCREMENT,
                        goal_id TEXT,
                        event_type TEXT,
                        payload JSON,
                        timestamp REAL
                    )
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_events_goal_id ON events(goal_id);")
        except Exception as e:
            logger.error(f"Failed to init SQLite Hybrid Persistence: {e}")

    def _rotate_backups(self):
        """Mantém backups rotativos: .bak (recente) -> .bak.old (antigo)."""
        if not os.path.exists(self._db_path): return
        try:
            bak_1 = f"{self._db_path}.bak"
            bak_2 = f"{self._db_path}.bak.old"
            
            # Rotate 1 -> 2
            if os.path.exists(bak_1):
                shutil.copy2(bak_1, bak_2)
            
            # Current -> 1
            shutil.copy2(self._db_path, bak_1)
            logger.info("SQLite Backup Rotated Successfully.")
        except Exception as e:
            logger.warning(f"Backup Rotation Failed: {e}")

    def _restore_from_backup(self):
        """Tenta restaurar do backup mais recente viável."""
        bak_1 = f"{self._db_path}.bak"
        bak_2 = f"{self._db_path}.bak.old"
        
        candidates = [bak_1, bak_2]
        restored = False
        
        for bk in candidates:
            if os.path.exists(bk):
                logger.warning(f"Restoring from {bk}...")
                try:
                    # Verify backup integrity before copy
                    with sqlite3.connect(bk) as conn:
                        res = conn.execute("PRAGMA integrity_check").fetchone()[0]
                        if res == "ok":
                            shutil.copy2(bk, self._db_path)
                            logger.info(f"Restored successfully from {bk}")
                            restored = True
                            break
                        else:
                            logger.error(f"Backup {bk} is also corrupted!")
                except Exception as e:
                    logger.error(f"Failed to restore from {bk}: {e}")
        
        if not restored:
            logger.critical("ALL BACKUPS FAILED or NOT FOUND. Creating fresh DB (Data Loss likely).")
            if os.path.exists(self._db_path):
                os.rename(self._db_path, f"{self._db_path}.corrupted.{int(time.time())}")

    def _persist_change(self, goal: Optional[Goal], event_type: str, goal_id: str):
        """
        ACID Transaction:
        1. Access Append-Only Log (Event)
        2. Update Current State (Snapshot)
        """
        try:
            timestamp = time.time()
            payload = json.dumps(goal.to_dict(), ensure_ascii=False) if goal else "{}"
            
            with sqlite3.connect(self._db_path) as conn:
                # 1. Append Event
                conn.execute(
                    "INSERT INTO events (goal_id, event_type, payload, timestamp) VALUES (?, ?, ?, ?)",
                    (goal_id, event_type, payload, timestamp)
                )
                
                # 2. Update Snapshot
                if event_type == "DELETED":
                    conn.execute("DELETE FROM snapshots WHERE id = ?", (goal_id,))
                else:
                    # Upsert Snapshot
                    conn.execute(
                        "INSERT INTO snapshots (id, data, updated_at) VALUES (?, ?, ?) "
                        "ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at",
                        (goal_id, payload, timestamp)
                    )
        except Exception as e:
            logger.error("Failed Hybrid Persistence Transaction", id=goal_id, error=str(e))

    # --- Lifecycle Management (RAM Optimization) ---

    def _load_from_sqlite(self):
        """Hydrates ONLY active goals (Pending/In Progress) to prevent OOM."""
        try:
            with sqlite3.connect(self._db_path) as conn:
                # Optimized Query: Only fetch active goals
                cursor = conn.execute("SELECT data FROM snapshots")
                rows = cursor.fetchall()
                count = 0
                for row in rows:
                    try:
                        data = json.loads(row[0])
                        # Active Set Filter
                        if data.get("status") in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]:
                            goal = Goal.from_dict(data)
                            self._goals[goal.id] = goal
                            count += 1
                    except Exception:
                        continue
                logger.info(f"Active Set Hydrated: {count} goals (Cold storage ignored).")
        except Exception as e:
            logger.error("Failed to hydrate from SQLite", error=str(e))

    def create_goal(self, title: str, description: str, priority: int = 5,
                    success_criteria: Optional[str] = None, deadline_ts: Optional[float] = None) -> Goal:
        goal_id = uuid.uuid4().hex
        goal = Goal(id=goal_id, title=title.strip(), description=description.strip(), priority=priority,
                    success_criteria=success_criteria, deadline_ts=deadline_ts)
        
        # 1. Update RAM (Active Set)
        self._goals[goal_id] = goal
        
        # 2. Persist Hybrid
        self._persist_change(goal, "CREATED", goal_id)
        
        # 3. Sync Cloud
        self._save_to_firestore(goal)

        self._log_to_memory_service(goal, "created")
        return goal

    def list_goals(self, status: Optional[str] = None) -> List[Goal]:
        """Smart Listing: RAM for Active, Disk for Cold."""
        
        # 1. If asking for Active, serve from RAM (Microsecond latency)
        if status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]:
            items = [g for g in self._goals.values() if g.status == status]
            return sorted(items, key=lambda g: (g.priority, g.created_at))
        
        # 2. If asking for History (Completed/Failed/All), fetch from Cold Storage
        try:
            items = []
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute("SELECT data FROM snapshots")
                for row in cursor:
                    try:
                        g_dict = json.loads(row[0])
                        if status and g_dict.get("status") != status:
                            continue
                        items.append(Goal.from_dict(g_dict))
                    except: pass
            return sorted(items, key=lambda g: (g.priority, g.created_at))
        except Exception as e:
            logger.error(f"Failed to list cold goals: {e}")
            return []

    def update_goal_status(self, goal_id: str, status: str) -> Optional[Goal]:
        # 1. Try to find in RAM
        goal = self._goals.get(goal_id)
        
        # 2. If not in RAM (was cold), fetch from Disk
        if not goal:
            goal = self.get_goal(goal_id) # Should fetch from disk logic below
            if not goal: return None
            # Re-hydrate to RAM temporarily for update
            self._goals[goal_id] = goal

        goal.status = status
        goal.updated_at = time.time()
        
        # 3. Lifecycle Logic: Evict if terminal state
        if status in [GoalStatus.COMPLETED, GoalStatus.FAILED]:
            # Evict from RAM (Cold Storage only)
            self._goals.pop(goal_id, None)
            logger.info(f"Goal {goal_id} archived to Cold Storage (RAM Eviction).")
        else:
            # Ensure it's in RAM (Promotion)
            self._goals[goal_id] = goal
        
        self._persist_change(goal, "UPDATED", goal_id)
        self._save_to_firestore(goal)
        
        return goal

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        # 1. L1 Cache: RAM
        if goal_id in self._goals:
            return self._goals[goal_id]
        
        # 2. L2 Storage: SQLite
        try:
            with sqlite3.connect(self._db_path) as conn:
                cursor = conn.execute("SELECT data FROM snapshots WHERE id = ?", (goal_id,))
                row = cursor.fetchone()
                if row:
                    data = json.loads(row[0])
                    return Goal.from_dict(data)
        except Exception:
            return None
        return None

    def get_next_goal(self) -> Optional[Goal]:
        # Always served from RAM (Active Set)
        pending = [g for g in self._goals.values() if g.status == GoalStatus.PENDING]
        sorted_pending = sorted(pending, key=lambda g: (g.priority, g.created_at))
        return sorted_pending[0] if sorted_pending else None

    def delete_goal(self, goal_id: str) -> bool:
        # Check RAM
        removed = self._goals.pop(goal_id, None)
        
        # Persist Dels
        self._persist_change(None, "DELETED", goal_id)
        self._delete_from_firestore(goal_id)
        
        # If it was in RAM, log it
        if removed:
             self._log_to_memory_service(removed, "deleted")
             return True
        
        # If active, return True. If cold, we assume deleted via persist_change.
        return True


# --- Dependency Injection Helper ---
def get_goal_manager(request: Request) -> "GoalManager":
    return request.app.state.goal_manager