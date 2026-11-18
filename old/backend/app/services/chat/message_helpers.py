import json
import re
from typing import Any

_UI_TAG_RE = re.compile(
    r"<janus-ui(?P<attrs>[^>]*)>(?P<body>[\s\S]*?)</janus-ui>",
    re.IGNORECASE,
)
_UI_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')
_UI_ALLOWED_TYPES = frozenset({"table", "chart", "list", "card", "code_block"})


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
    """Extrai um bloco `<janus-ui type="..." title="...">DATA_JSON</janus-ui>` do texto.

    O LLM é instruído (ver `backend/app/prompts/generative_ui.txt`) a emitir esse
    marcador quando uma resposta se beneficia de visualização estruturada. Retorna
    o texto sem o marcador e um dict `{type, title, data, description}` pronto para
    persistir em `messages.ui_json` — ou `(text, None)` se nada válido for encontrado,
    caso em que o texto original é preservado sem alteração.
    """
    if not text:
        return (text or "", None)

    match = _UI_TAG_RE.search(text)
    if not match:
        return (text, None)

    attrs = dict(_UI_ATTR_RE.findall(match.group("attrs")))
    ui_type = attrs.get("type", "").strip().lower()
    if ui_type not in _UI_ALLOWED_TYPES:
        return (text, None)

    body = match.group("body").strip()
    try:
        data = json.loads(body) if body else None
    except json.JSONDecodeError:
        return (text, None)
    if data is None:
        return (text, None)

    ui: dict[str, Any] = {"type": ui_type, "data": data}
    title = attrs.get("title", "").strip()
    if title:
        ui["title"] = title
    description = attrs.get("description", "").strip()
    if description:
        ui["description"] = description

    clean_text = (text[: match.start()] + text[match.end() :]).strip()
    return (clean_text, ui)


def _build_question_summary(normalized: str) -> str:
    clean = normalized.rstrip("?.! ").strip()

    history_match = re.search(
        r"(?:historia|história)\s+(?:para|sobre)\s+(.+)$",
        clean,
        re.IGNORECASE,
    )
    if history_match:
        topic = history_match.group(1).strip(" ?.!").strip()
        if topic:
            return f"Usuario pediu uma historia sobre {topic}."

    explain_match = re.search(
        r"^(?:como|qual|quais|quando|porque|por que|what|how|why)\s+(.+)$",
        clean,
        re.IGNORECASE,
    )
    if explain_match:
        topic = explain_match.group(1).strip(" ?.!").strip()
        if topic:
            return f"Usuario fez uma pergunta sobre {topic}."

    if clean:
        return "Usuario fez uma pergunta para obter informacao ou orientacao."
    return normalized


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
            "consegue",
            "pode",
        )
        if normalized.endswith("?") or any(lowered.startswith(k) for k in question_leads):
            intent = "question"
            base_confidence = 0.72

    summary = normalized
    if intent == "file_reference":
        summary = "Usuario informou que enviou um arquivo para consulta."
    elif intent == "question":
        summary = _build_question_summary(normalized)
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


