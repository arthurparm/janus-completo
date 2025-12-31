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
from app.core.evolution.reflector_agent import ReflectorAgent, ReflectionReport, FailurePattern
from app.core.evolution.self_study_manager import SelfStudyManager, StudySession, quick_self_reflection
from app.core.evolution.prompts import (
    TOOL_SPECIFICATION_PROMPT,
    TOOL_GENERATION_PROMPT,
    tool_validation_prompt
)

# JanusLab and SafeEvolution may not be available if Docker SDK is not installed
try:
    from app.core.evolution.janus_lab import JanusLabManager, LabConfig, LabResult, quick_lab_test
    from app.core.evolution.safe_evolution_manager import SafeEvolutionManager, SafeEvolutionSession, dream
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
    "EvolutionManager",
    "ReflectorAgent",
    "ReflectionReport",
    "FailurePattern",
    "SelfStudyManager",
    "StudySession",
    "quick_self_reflection",
    "TOOL_SPECIFICATION_PROMPT",
    "TOOL_GENERATION_PROMPT",
    "tool_validation_prompt",
    "JanusLabManager",
    "LabConfig",
    "LabResult",
    "quick_lab_test",
    "SafeEvolutionManager",
    "SafeEvolutionSession",
    "dream",
    "JANUS_LAB_AVAILABLE"
]
