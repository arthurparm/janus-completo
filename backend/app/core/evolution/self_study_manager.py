"""
SelfStudyManager: Janus Autonomous Self-Improvement Orchestrator

This manager coordinates the complete self-study loop:
1. Reflection - Analyze past experiences for failure patterns
2. Prioritization - Rank improvements by impact
3. Evolution - Create/improve tools based on insights
4. Validation - Verify improvements work

The loop runs during idle time (low system load) to avoid impacting user requests.
"""

import asyncio
import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from app.core.evolution.evolution_manager import EvolutionManager
from app.core.evolution.reflector_agent import ReflectorAgent

logger = logging.getLogger(__name__)


@dataclass
class StudySession:
    """Record of a self-study session."""

    session_id: str
    started_at: str
    completed_at: str | None = None
    reflection_summary: dict[str, Any] | None = None
    evolutions_triggered: int = 0
    evolutions_succeeded: int = 0
    evolutions_failed: int = 0
    status: str = "running"  # running, completed, failed


class SelfStudyManager:
    """
    Orchestrates the autonomous self-improvement loop.

    This is the "dreaming" component - Janus learns while idle.
    """

    SESSION_LOG_FILE = "data/self_study_sessions.json"
    MAX_EVOLUTIONS_PER_SESSION = 3  # Safety limit
    MIN_HEALTH_SCORE_TO_TRIGGER = 0.8  # Only evolve if health below this

    def __init__(self, reflector: ReflectorAgent, evolution_manager: EvolutionManager):
        self.reflector = reflector
        self.evolution_manager = evolution_manager
        self._current_session: StudySession | None = None
        self._is_running = False

    async def run_study_session(
        self, hours_to_analyze: int = 24, max_evolutions: int | None = None, dry_run: bool = False
    ) -> StudySession:
        """
        Execute a complete self-study session.

        Args:
            hours_to_analyze: How many hours of history to analyze.
            max_evolutions: Override max evolutions per session.
            dry_run: If True, only reflect and suggest, don't actually evolve.

        Returns:
            StudySession with results.
        """
        import uuid

        if self._is_running:
            logger.warning("[SelfStudy] Sessão já em andamento. Ignorando.")
            return self._current_session

        self._is_running = True
        session = StudySession(session_id=str(uuid.uuid4()), started_at=datetime.now().isoformat())
        self._current_session = session

        logger.info(f"[SelfStudy] Iniciando sessão de auto-estudo: {session.session_id}")

        try:
            # Phase 1: Reflection
            logger.info("[SelfStudy] Fase 1: Reflexão...")
            report = await self.reflector.analyze_recent_experiences(hours_back=hours_to_analyze)
            session.reflection_summary = self.reflector.to_dict(report)

            logger.info(
                f"[SelfStudy] Reflexão completa. "
                f"Health Score: {report.overall_health_score:.2f}, "
                f"Padrões detectados: {len(report.failure_patterns)}"
            )

            # Phase 2: Decision - Should we evolve?
            if dry_run:
                logger.info("[SelfStudy] Modo dry-run. Pulando evolução.")
                session.status = "completed"
                session.completed_at = datetime.now().isoformat()
                self._save_session(session)
                return session

            if report.overall_health_score >= self.MIN_HEALTH_SCORE_TO_TRIGGER:
                logger.info(
                    f"[SelfStudy] Sistema saudável (score={report.overall_health_score:.2f}). "
                    "Nenhuma evolução necessária."
                )
                session.status = "completed"
                session.completed_at = datetime.now().isoformat()
                self._save_session(session)
                return session

            # Phase 3: Evolution based on insights
            logger.info("[SelfStudy] Fase 3: Evolução baseada em insights...")
            evolutions_limit = max_evolutions or self.MAX_EVOLUTIONS_PER_SESSION

            # Prioritize patterns that suggest tool creation
            evolution_candidates = [
                p
                for p in report.failure_patterns
                if p.pattern_type == "tool_missing" and p.suggested_improvement
            ]

            for i, pattern in enumerate(evolution_candidates[:evolutions_limit]):
                logger.info(
                    f"[SelfStudy] Evolução {i + 1}/{len(evolution_candidates)}: "
                    f"{pattern.description}"
                )

                session.evolutions_triggered += 1

                try:
                    # Queue evolution request (async processing)
                    self.evolution_manager.queue_request(pattern.suggested_improvement)

                    # Optionally process immediately
                    result = await self.evolution_manager.process_next_pending()

                    if result:
                        session.evolutions_succeeded += 1
                        logger.info(f"[SelfStudy] Evolução bem-sucedida: {result.get('name')}")
                    else:
                        session.evolutions_failed += 1

                except Exception as e:
                    logger.error(f"[SelfStudy] Falha na evolução: {e}")
                    session.evolutions_failed += 1

                # Small delay between evolutions
                await asyncio.sleep(2)

            session.status = "completed"
            session.completed_at = datetime.now().isoformat()

            logger.info(
                f"[SelfStudy] Sessão completa. "
                f"Evoluções: {session.evolutions_succeeded}/{session.evolutions_triggered} sucesso"
            )

        except Exception as e:
            logger.error(f"[SelfStudy] Erro na sessão: {e}", exc_info=True)
            session.status = "failed"
            session.completed_at = datetime.now().isoformat()

        finally:
            self._is_running = False
            self._save_session(session)

        return session

    async def run_reflection_only(self, hours: int = 24) -> dict[str, Any]:
        """
        Run only the reflection phase (safe, read-only).

        Returns:
            Reflection report as dictionary.
        """
        logger.info(f"[SelfStudy] Executando reflexão (últimas {hours}h)...")
        report = await self.reflector.analyze_recent_experiences(hours_back=hours)
        return self.reflector.to_dict(report)

    def get_last_session(self) -> dict[str, Any] | None:
        """Get the most recent study session."""
        sessions = self._load_sessions()
        if sessions:
            return sessions[-1]
        return None

    def get_session_history(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent study session history."""
        sessions = self._load_sessions()
        return sessions[-limit:]

    def _save_session(self, session: StudySession):
        """Persist session to log file."""
        import os

        try:
            sessions = self._load_sessions()
            sessions.append(asdict(session))

            # Keep only last 100 sessions
            sessions = sessions[-100:]

            os.makedirs(os.path.dirname(self.SESSION_LOG_FILE), exist_ok=True)
            with open(self.SESSION_LOG_FILE, "w") as f:
                json.dump(sessions, f, indent=2)

        except Exception as e:
            logger.error(f"[SelfStudy] Erro ao salvar sessão: {e}")

    def _load_sessions(self) -> list[dict[str, Any]]:
        """Load sessions from log file."""
        try:
            with open(self.SESSION_LOG_FILE) as f:
                return json.load(f)
        except Exception:
            return []


# Convenience function for quick reflection
async def quick_self_reflection(memory_core) -> dict[str, Any]:
    """
    Quick helper to run reflection without full setup.

    Usage:
        from app.core.evolution.self_study_manager import quick_self_reflection
        report = await quick_self_reflection(memory_db)
        print(report)
    """
    reflector = ReflectorAgent(memory_core)
    report = await reflector.analyze_recent_experiences(hours_back=24)
    return reflector.to_dict(report)
