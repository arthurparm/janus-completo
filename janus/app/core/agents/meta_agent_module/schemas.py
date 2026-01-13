from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Required, TypedDict, Literal
from pydantic import BaseModel, Field


class IssueSeverity(Enum):
    """Severidade de um problema detectado."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IssueCategory(Enum):
    """Categoria de problema."""

    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    RESOURCE = "resource"
    CONFIGURATION = "configuration"
    SECURITY = "security"


def safe_issue_severity(value: Any) -> IssueSeverity:
    s = (str(value) if value is not None else "").strip().lower()
    try:
        return IssueSeverity(s)
    except Exception:
        if s in ("info", "informational", "notice"):
            return IssueSeverity.LOW
        if s in ("moderate", "medium", "normal"):
            return IssueSeverity.MEDIUM
        if s in ("major", "high", "severe"):
            return IssueSeverity.HIGH
        if s in ("critical", "blocker", "urgent"):
            return IssueSeverity.CRITICAL
        return IssueSeverity.LOW


def safe_issue_category(value: Any) -> IssueCategory:
    s = (str(value) if value is not None else "").strip().lower()
    try:
        return IssueCategory(s)
    except Exception:
        synonyms = {
            "ops": "reliability",
            "operational": "reliability",
            "operations": "reliability",
            "availability": "reliability",
            "stability": "reliability",
            "latency": "performance",
            "throughput": "performance",
            "efficiency": "performance",
            "memory": "resource",
            "cpu": "resource",
            "disk": "resource",
            "io": "resource",
            "quota": "resource",
            "capacity": "resource",
            "misconfiguration": "configuration",
            "config": "configuration",
            "configuration": "configuration",
            "auth": "security",
            "authorization": "security",
            "authentication": "security",
            "vulnerability": "security",
            "security": "security",
        }
        mapped = synonyms.get(s)
        if mapped:
            return IssueCategory(mapped)
        if ("latency" in s) or ("slow" in s) or ("performance" in s):
            return IssueCategory.PERFORMANCE
        if ("availability" in s) or ("stability" in s) or ("reliab" in s) or ("operat" in s):
            return IssueCategory.RELIABILITY
        if ("cpu" in s) or ("memory" in s) or ("disk" in s) or ("resource" in s) or ("quota" in s):
            return IssueCategory.RESOURCE
        if ("config" in s) or ("misconfig" in s) or ("configuration" in s) or ("settings" in s):
            return IssueCategory.CONFIGURATION
        if ("security" in s) or ("auth" in s) or ("vuln" in s) or ("attack" in s):
            return IssueCategory.SECURITY
        return IssueCategory.PERFORMANCE


@dataclass
class DetectedIssue:
    """Problema detectado pelo Meta-Agente."""

    id: str
    severity: IssueSeverity
    category: IssueCategory
    title: str
    description: str
    evidence: dict[str, Any]
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "severity": self.severity.value,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "evidence": self.evidence,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class Recommendation:
    """Recomendação de melhoria."""

    id: str
    category: IssueCategory
    title: str
    description: str
    rationale: str
    estimated_impact: str
    priority: int  # 1-5
    suggested_agent: str | None = None
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "category": self.category.value,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "estimated_impact": self.estimated_impact,
            "priority": self.priority,
            "suggested_agent": self.suggested_agent,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class StateReport:
    """Relatório de estado do sistema."""

    cycle_id: str
    timestamp: datetime
    overall_status: str  # healthy, degraded, critical
    health_score: int  # 0-100
    issues_detected: list[DetectedIssue]
    recommendations: list[Recommendation]
    summary: str
    metrics_snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "timestamp": self.timestamp.isoformat(),
            "overall_status": self.overall_status,
            "health_score": self.health_score,
            "issues_detected": [issue.to_dict() for issue in self.issues_detected],
            "recommendations": [rec.to_dict() for rec in self.recommendations],
            "summary": self.summary,
            "metrics_snapshot": self.metrics_snapshot,
        }


# --- LangGraph State Schema (Industry Benchmark) ---
class AgentState(TypedDict, total=False):
    """Estado do Agente gerenciado pelo LangGraph (TypedDict Standard)."""

    cycle_id: Required[str]
    timestamp: float
    # Metrics & Diagnosis
    metrics: dict[str, Any]
    detected_issues: list[dict[str, Any]]  # Serialized DetectedIssue
    diagnosis: str

    # Planning & Reflexion
    candidate_plan: list[dict[str, Any]]  # Serialized Recommendation
    critique: dict[str, Any] | None
    final_plan: list[dict[str, Any]]

    # Execution
    execution_results: list[dict[str, Any]]

    # Control Flow
    status: str
    retry_count: int
    max_retries: int


class DiagnosisSchema(BaseModel):
    root_cause: str = Field(..., description="A causa raiz técnica identificada.")
    severity: str = Field(..., description="Gravidade: low, medium, high, critical")
    confidence: float = Field(..., description="Nível de confiança no diagnóstico (0.0 a 1.0)")


class RecommendationItem(BaseModel):
    title: str
    description: str
    priority: int = Field(..., ge=1, le=5)
    suggested_agent: str = Field(..., pattern="^(sysadmin|coder|monitor)$")
    category: str = "performance"


class PlanSchema(BaseModel):
    recommendations: list[RecommendationItem]


class CritiqueSchema(BaseModel):
    approved: bool
    reason: str
    safe_subset_ids: list[str] = Field(default_factory=list)
