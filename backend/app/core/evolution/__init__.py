"""
Janus Evolution Module

Provides autonomous self-improvement capabilities:
- EvolutionManager: Dynamic tool creation and registration
- ReflectorAgent: Self-analysis of past experiences
- SelfStudyManager: Orchestrates the complete self-improvement loop
- JanusLabManager: Spawns isolated test instances for safe experimentation
- SafeEvolutionManager: Lab-validated autonomous evolution (Dream Mode)

Usage:
    from app.core.evolution import EvolutionManager, SafeEvolutionManager, JanusLabManager
"""

from app.core.evolution.evolution_manager import EvolutionManager
from app.core.evolution.prompts import (
    TOOL_GENERATION_PROMPT,
    TOOL_SPECIFICATION_PROMPT,
    tool_validation_prompt,
)
from app.core.evolution.reflector_agent import FailurePattern, ReflectionReport, ReflectorAgent
from app.core.evolution.self_study_manager import (
    SelfStudyManager,
    StudySession,
    quick_self_reflection,
)

# JanusLab and SafeEvolution may not be available if Docker SDK is not installed
try:
    from app.core.evolution.janus_lab import JanusLabManager, LabConfig, LabResult, quick_lab_test
    from app.core.evolution.safe_evolution_manager import (
        SafeEvolutionManager,
        SafeEvolutionSession,
        dream,
    )

    JANUS_LAB_AVAILABLE = True
except ImportError:
    JanusLabManager = None
    LabConfig = None
    LabResult = None
    quick_lab_test = None
    SafeEvolutionManager = None
    SafeEvolutionSession = None
    dream = None
    JANUS_LAB_AVAILABLE = False

__all__ = [
    "JANUS_LAB_AVAILABLE",
    "TOOL_GENERATION_PROMPT",
    "TOOL_SPECIFICATION_PROMPT",
    "EvolutionManager",
    "FailurePattern",
    "JanusLabManager",
    "LabConfig",
    "LabResult",
    "ReflectionReport",
    "ReflectorAgent",
    "SafeEvolutionManager",
    "SafeEvolutionSession",
    "SelfStudyManager",
    "StudySession",
    "dream",
    "quick_lab_test",
    "quick_self_reflection",
    "tool_validation_prompt",
]
