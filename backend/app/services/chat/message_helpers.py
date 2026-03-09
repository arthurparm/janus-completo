import json
from typing import Any

def estimate_tokens(prompt_service: Any, text: str) -> int:
    if not text:
        return 0
    try:
        est = prompt_service.estimate_tokens(text)
        if isinstance(est, int) and est > 0:
            return est
    except Exception:
        pass
    return max(1, len(text) // 4)


def split_ui(text: str) -> tuple[str, dict[str, Any] | None]:
    return (text or "", None)


def build_understanding_payload(message: str) -> dict[str, Any] | None:
    normalized = " ".join((message or "").strip().split())
    if not normalized:
        return None

    lowered = normalized.lower()
    intent = "general"
    base_confidence = 0.60
    requires_confirmation = False
    signals: list[str] = []

    intent_specs: list[tuple[str, tuple[str, ...], float, bool]] = [
        (
            "file_reference",
            (
                "te mandei um arquivo",
                "te enviei um arquivo",
                "enviei um arquivo",
                "mandei um arquivo",
                "anexo",
                "arquivo",
                "documento",
                "upload",
            ),
            0.88,
            False,
        ),
        (
            "reminder",
            (
                "lembrete",
                "lembrar",
                "me lembra",
                "reminder",
                "remind me",
                "avisa",
                "avisar",
            ),
            0.86,
            True,
        ),
        (
            "documentation_query",
            (
                "documentacao",
                "documentação",
                "docs",
                "readme",
                "manual",
                "sdk",
                "openapi",
                "api reference",
                "spec",
            ),
            0.82,
            False,
        ),
        (
            "action_request",
            (
                "crie",
                "criar",
                "implemente",
                "implementar",
                "faça",
                "faca",
                "adicione",
                "gere",
                "executa",
                "execute",
                "build",
            ),
            0.78,
            True,
        ),
    ]

    for candidate_intent, keywords, confidence, needs_confirmation in intent_specs:
        matched = [kw for kw in keywords if kw in lowered]
        if matched:
            intent = candidate_intent
            base_confidence = confidence
            requires_confirmation = needs_confirmation
            signals = matched
            break

    if intent == "general":
        question_leads = (
            "como",
            "qual",
            "quais",
            "quando",
            "porque",
            "por que",
            "what",
            "how",
            "why",
            "can you",
        )
        if normalized.endswith("?") or any(lowered.startswith(k) for k in question_leads):
            intent = "question"
            base_confidence = 0.72

    summary = normalized
    if intent == "file_reference":
        summary = "Usuario informou que enviou um arquivo para consulta."
    if len(summary) > 180:
        summary = f"{summary[:177].rstrip()}..."

    confidence = min(0.95, base_confidence + (0.03 * min(len(signals), 3)))
    payload: dict[str, Any] = {
        "intent": intent,
        "summary": summary,
        "confidence": round(confidence, 2),
        "requires_confirmation": requires_confirmation,
    }
    if signals:
        payload["signals"] = signals[:5]
    return payload


def attach_understanding(
    payload: dict[str, Any],
    understanding: dict[str, Any] | None,
) -> dict[str, Any]:
    if understanding and isinstance(payload, dict) and payload.get("understanding") is None:
        payload["understanding"] = understanding
    return payload


def is_explicit_tool_creation(message: str) -> bool:
    if not message:
        return False
    lower = message.lower()
    if "tool" not in lower and "ferramenta" not in lower:
        return False
    creation_keywords = ("crie", "criar", "create", "build", "gerar", "generate")
    return any(k in lower for k in creation_keywords)


def format_tool_creation_response(result: dict[str, Any]) -> str:
    if not result:
        return "Tool creation returned an empty result."
    name = result.get("name") or result.get("tool_name") or result.get("tool") or "unknown"
    status = result.get("evolution_message") or "Tool creation completed."
    payload = json.dumps(result, indent=2, ensure_ascii=False)
    return f"{status}\n\nTool: {name}\n\n{payload}"
