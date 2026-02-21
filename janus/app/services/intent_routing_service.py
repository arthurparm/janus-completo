import re
import unicodedata
from dataclasses import asdict, dataclass, field

from app.config import settings
from app.core.llm import ModelRole


@dataclass
class IntentRoutingDecision:
    intent: str
    risk_level: str
    urgency_level: str
    confidence: float
    suggested_role: ModelRole
    signals: list[str] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)
    alternatives: list[dict[str, float | str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["suggested_role"] = self.suggested_role.value
        payload["confidence"] = round(float(self.confidence), 2)
        return payload


class IntentRoutingService:
    _INTENT_RULES: dict[str, dict] = {
        "code_generation": {
            "role": ModelRole.CODE_GENERATOR,
            "weight": 1.45,
            "keywords": (
                "codigo",
                "code",
                "python",
                "typescript",
                "javascript",
                "refator",
                "refactor",
                "implemente",
                "implementar",
                "create function",
                "funcao",
                "bugfix",
                "fix bug",
                "teste unitario",
                "unit test",
                "endpoint",
                "pull request",
                ".py",
                ".ts",
                ".js",
            ),
        },
        "knowledge_query": {
            "role": ModelRole.KNOWLEDGE_CURATOR,
            "weight": 1.20,
            "keywords": (
                "documentacao",
                "docs",
                "readme",
                "como funciona",
                "arquitetura",
                "explica",
                "explain",
                "resuma",
                "resumo",
                "knowledge",
                "rag",
                "fonte",
                "citation",
                "citacao",
            ),
        },
        "security_audit": {
            "role": ModelRole.SECURITY_AUDITOR,
            "weight": 1.80,
            "keywords": (
                "seguranca",
                "vulnerabilidade",
                "vulnerability",
                "injection",
                "sql injection",
                "xss",
                "csrf",
                "token",
                "secret",
                "senha",
                "password",
                "auth bypass",
                "privilege escalation",
                "exploit",
                "rce",
                "hardening",
                "mitigar",
            ),
        },
        "incident_response": {
            "role": ModelRole.SECURITY_AUDITOR,
            "weight": 1.65,
            "keywords": (
                "incidente",
                "incident",
                "sev1",
                "sev 1",
                "p0",
                "producao caiu",
                "outage",
                "rollback",
                "indisponivel",
                "critical failure",
            ),
        },
        "deep_reasoning": {
            "role": ModelRole.REASONER,
            "weight": 1.10,
            "keywords": (
                "trade-off",
                "tradeoff",
                "analise",
                "comparar",
                "compare",
                "estrategia",
                "hipotese",
                "planejamento",
                "planejar",
                "what if",
            ),
        },
    }

    _HIGH_RISK_KEYWORDS = (
        "drop table",
        "truncate",
        "delete all",
        "rm -rf",
        "bypass auth",
        "exploit",
        "steal token",
        "exfiltrate",
        "credential dump",
        "disable security",
    )

    _MEDIUM_RISK_KEYWORDS = (
        "delete",
        "remove",
        "reset",
        "token",
        "password",
        "secret",
        "sudo",
        "admin",
        "privileged",
        "production",
        "rollback",
    )

    _DEFENSIVE_CONTEXT_KEYWORDS = (
        "mitigar",
        "corrigir",
        "fix",
        "patch",
        "proteger",
        "prevent",
        "detectar",
        "secure",
        "hardening",
        "defesa",
        "defensive",
    )

    _HIGH_URGENCY_KEYWORDS = (
        "urgente",
        "urgent",
        "agora",
        "asap",
        "imediato",
        "immediately",
        "p0",
        "sev1",
        "incidente",
        "incident",
        "producao caiu",
        "outage",
    )

    _MEDIUM_URGENCY_KEYWORDS = (
        "hoje",
        "today",
        "ate amanha",
        "tomorrow",
        "prioridade",
        "soon",
    )

    def classify(self, message: str) -> IntentRoutingDecision:
        raw = (message or "").strip()
        text = self._normalize_text(raw)
        if not text:
            return IntentRoutingDecision(
                intent="general",
                risk_level="low",
                urgency_level="low",
                confidence=0.55,
                suggested_role=ModelRole.ORCHESTRATOR,
            )

        scores: dict[str, float] = {}
        matched_signals: dict[str, list[str]] = {}

        for intent_name, rule in self._INTENT_RULES.items():
            hits = self._keyword_hits(text, rule["keywords"])
            if not hits:
                continue
            matched_signals[intent_name] = hits
            scores[intent_name] = float(len(hits)) * float(rule["weight"])

        if "```" in raw or any(ext in text for ext in (".py", ".ts", ".js", ".go", ".java")):
            scores["code_generation"] = scores.get("code_generation", 0.0) + 1.6
            matched_signals.setdefault("code_generation", []).append("code_block_or_extension")

        risk_level, risk_signals = self._detect_risk(text)
        urgency_level = self._detect_urgency(text)

        if not scores:
            suggested_role = (
                ModelRole.SECURITY_AUDITOR if risk_level == "high" else ModelRole.ORCHESTRATOR
            )
            guardrails = self._guardrails_for(risk_level=risk_level, urgency_level=urgency_level)
            return IntentRoutingDecision(
                intent="general",
                risk_level=risk_level,
                urgency_level=urgency_level,
                confidence=0.55,
                suggested_role=suggested_role,
                signals=risk_signals,
                guardrails=guardrails,
                alternatives=[],
            )

        sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        best_intent, best_score = sorted_scores[0]
        second_score = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
        best_hits = matched_signals.get(best_intent, [])
        confidence = self._calibrate_confidence(
            best_score=best_score,
            second_score=second_score,
            hit_count=len(best_hits),
        )

        if best_intent == "incident_response" and risk_level == "low":
            risk_level = "medium"

        suggested_role = self._INTENT_RULES[best_intent]["role"]
        if risk_level == "high":
            suggested_role = ModelRole.SECURITY_AUDITOR

        alternatives = [
            {
                "intent": intent_name,
                "score": round(float(score), 2),
                "role": self._INTENT_RULES[intent_name]["role"].value,
            }
            for intent_name, score in sorted_scores[1:4]
        ]
        guardrails = self._guardrails_for(risk_level=risk_level, urgency_level=urgency_level)
        signals = list(dict.fromkeys((best_hits + risk_signals)[:8]))

        return IntentRoutingDecision(
            intent=best_intent,
            risk_level=risk_level,
            urgency_level=urgency_level,
            confidence=round(confidence, 2),
            suggested_role=suggested_role,
            signals=signals,
            guardrails=guardrails,
            alternatives=alternatives,
        )

    def resolve_role(
        self,
        requested_role: str | None,
        message: str,
    ) -> tuple[ModelRole, IntentRoutingDecision | None, bool]:
        raw = (requested_role or ModelRole.ORCHESTRATOR.value).strip().lower()
        if raw == "auto":
            base_role = ModelRole.ORCHESTRATOR
        else:
            try:
                base_role = ModelRole(raw)
            except ValueError as exc:
                raise ValueError("Invalid role or priority") from exc

        if not bool(getattr(settings, "AI_INTENT_ROUTING_ENABLED", True)):
            return base_role, None, False

        decision = self.classify(message)
        min_conf_auto = float(getattr(settings, "AI_INTENT_ROUTING_MIN_CONFIDENCE", 0.72))
        min_conf_orchestrator = float(
            getattr(settings, "AI_INTENT_ROUTING_ORCHESTRATOR_OVERRIDE_CONFIDENCE", 0.82)
        )
        urgency_override_conf = float(
            getattr(settings, "AI_INTENT_ROUTING_URGENCY_OVERRIDE_CONFIDENCE", 0.76)
        )
        risk_escalation = bool(getattr(settings, "AI_INTENT_RISK_ESCALATION_ENABLED", True))

        selected = base_role
        route_applied = False

        if raw == "auto":
            if decision.risk_level == "high" and risk_escalation:
                selected = ModelRole.SECURITY_AUDITOR
            elif decision.confidence >= min_conf_auto:
                selected = decision.suggested_role
            elif (
                decision.urgency_level == "high"
                and decision.confidence >= urgency_override_conf
                and decision.intent in {"incident_response", "code_generation"}
            ):
                selected = decision.suggested_role
            route_applied = selected != ModelRole.ORCHESTRATOR
        elif base_role == ModelRole.ORCHESTRATOR:
            if decision.risk_level == "high" and risk_escalation:
                selected = ModelRole.SECURITY_AUDITOR
                route_applied = True
            elif (
                decision.confidence >= min_conf_orchestrator
                and decision.suggested_role != ModelRole.ORCHESTRATOR
            ):
                selected = decision.suggested_role
                route_applied = True
            elif (
                decision.urgency_level == "high"
                and decision.confidence >= urgency_override_conf
                and decision.intent in {"incident_response", "code_generation"}
            ):
                selected = decision.suggested_role
                route_applied = True

        return selected, decision, route_applied

    def _detect_risk(self, text: str) -> tuple[str, list[str]]:
        high_hits = self._keyword_hits(text, self._HIGH_RISK_KEYWORDS)
        medium_hits = self._keyword_hits(text, self._MEDIUM_RISK_KEYWORDS)
        defensive_hits = self._keyword_hits(text, self._DEFENSIVE_CONTEXT_KEYWORDS)

        signals = list(dict.fromkeys((high_hits + medium_hits + defensive_hits)[:6]))

        if high_hits:
            if defensive_hits:
                return "medium", signals
            return "high", signals

        if len(medium_hits) >= 3:
            return "medium", signals
        if len(medium_hits) >= 1 and defensive_hits:
            return "medium", signals
        return "low", signals

    def _detect_urgency(self, text: str) -> str:
        if self._keyword_hits(text, self._HIGH_URGENCY_KEYWORDS):
            return "high"
        if self._keyword_hits(text, self._MEDIUM_URGENCY_KEYWORDS):
            return "medium"
        return "low"

    def _guardrails_for(self, *, risk_level: str, urgency_level: str) -> list[str]:
        guardrails: list[str] = []
        if risk_level == "high":
            guardrails.extend(
                [
                    "manual_confirmation_required",
                    "restrict_destructive_actions",
                    "security_audit_recommended",
                    "audit_log_required",
                ]
            )
        elif risk_level == "medium":
            guardrails.extend(
                [
                    "confirm_before_sensitive_changes",
                    "audit_log_required",
                ]
            )

        if urgency_level == "high":
            guardrails.append("expedite_triage")
        return guardrails

    def _calibrate_confidence(self, *, best_score: float, second_score: float, hit_count: int) -> float:
        margin = max(0.0, best_score - second_score)
        spread = best_score / max(best_score + second_score + 0.9, 1.0)
        hit_boost = min(0.18, 0.03 * max(0, hit_count - 1))
        margin_boost = min(0.16, margin / 20.0)
        confidence = 0.50 + (spread * 0.30) + hit_boost + margin_boost
        return max(0.50, min(0.97, confidence))

    @staticmethod
    def _normalize_text(value: str) -> str:
        lowered = (value or "").strip().lower()
        nfkd = unicodedata.normalize("NFKD", lowered)
        ascii_text = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
        ascii_text = re.sub(r"[^a-z0-9._/\-\s:+#]", " ", ascii_text)
        ascii_text = re.sub(r"\s+", " ", ascii_text)
        return ascii_text.strip()

    def _keyword_hits(self, text: str, keywords: tuple[str, ...]) -> list[str]:
        hits: list[str] = []
        for keyword in keywords:
            normalized_keyword = self._normalize_text(keyword)
            if not normalized_keyword:
                continue

            if (
                " " in normalized_keyword
                or "." in normalized_keyword
                or "/" in normalized_keyword
                or ":" in normalized_keyword
            ):
                if normalized_keyword in text:
                    hits.append(normalized_keyword)
                continue

            if re.search(rf"\b{re.escape(normalized_keyword)}\b", text):
                hits.append(normalized_keyword)
        return hits


_intent_routing_service: IntentRoutingService | None = None


def get_intent_routing_service() -> IntentRoutingService:
    global _intent_routing_service
    if _intent_routing_service is None:
        _intent_routing_service = IntentRoutingService()
    return _intent_routing_service
