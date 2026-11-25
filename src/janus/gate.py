from __future__ import annotations

from dataclasses import dataclass

from janus.entry import Budget
from janus.tools import ALLOWLIST
from janus.tools.read_record import ToolSpec
from janus.util.codec import (
    MAX_TEXT,
    GateName,
    JanusError,
    as_gate,
    as_object,
    as_str,
    as_string_map,
    canonical_json,
    digest,
    exact_keys,
    has_hidden_char,
    require_text,
    require_token,
    required,
)
from janus.util.pairs import normalize_pairs, pairs_json

ALLOW_REASON = "leitura dentro do orçamento e da permissão"
STEP_REASON = "orçamento de passos esgotado"
COST_REASON = "orçamento de custo esgotado"
DEADLINE_REASON = "prazo esgotado"
ALLOWLIST_REASON = "ferramenta fora da allowlist"
PERMISSION_REASON = "permissão não cobre a leitura"
WRITE_PERMISSION_REASON = "permissão não cobre a escrita"
SCHEMA_REASON = "argumentos fora do schema"
ASK_REASON = "escrita irreversível exige confirmação humana"
IDEMPOTENCY_REASON = "chave de idempotência já usada"
INTERRUPTED_REASON = "run interrompido"
TERMINAL_REASONS = frozenset({STEP_REASON, COST_REASON, DEADLINE_REASON})


@dataclass(frozen=True)
class Decision:
    gate: GateName
    tool_name: str
    arguments: tuple[tuple[str, str], ...]
    risk_class: str
    reason: str

    def __post_init__(self) -> None:
        if self.gate not in ("permitir", "negar", "pedir"):
            raise JanusError("gate inválido")
        require_token(self.tool_name, "tool_name")
        if self.risk_class != "":
            require_token(self.risk_class, "risk_class")
        require_text(self.reason, "reason")
        object.__setattr__(self, "arguments", normalize_pairs(self.arguments))

    def to_json(self) -> dict[str, object]:
        return {
            "arguments": pairs_json(self.arguments),
            "gate": self.gate,
            "reason": self.reason,
            "risk_class": self.risk_class,
            "tool_name": self.tool_name,
        }

    @staticmethod
    def from_json(value: object) -> Decision:
        raw = as_object(value, "decision")
        exact_keys(raw, ("arguments", "gate", "reason", "risk_class", "tool_name"), "decision")
        risk_class = as_str(required(raw, "risk_class"), "risk_class", allow_empty=True)
        return Decision(
            as_gate(required(raw, "gate"), "gate"),
            as_str(required(raw, "tool_name"), "tool_name", allow_empty=False),
            as_string_map(required(raw, "arguments"), "arguments"),
            risk_class,
            as_str(required(raw, "reason"), "reason", allow_empty=False),
        )


def decide_read(
    tool_name: str,
    arguments: tuple[tuple[str, str], ...],
    permission: str,
    budget: Budget,
    spent_steps: int,
    spent_cost: int,
    started_at_ms: int,
    now_ms: int,
    seen_keys: tuple[tuple[str, str], ...] = (),
) -> Decision:
    if spent_steps >= budget.max_steps:
        return _deny(tool_name, arguments, "", STEP_REASON)
    if now_ms - started_at_ms > budget.deadline_ms:
        return _deny(tool_name, arguments, "", DEADLINE_REASON)
    spec = ALLOWLIST.get(tool_name)
    if spec is None:
        return _deny(tool_name, arguments, "", ALLOWLIST_REASON)
    # Fase A executa só leitura. Escrita irreversível pede e não roda.
    if spec.risk_class == "escrita_irreversivel":
        return _decide_irreversible(spec, tool_name, arguments, permission, seen_keys)
    if spec.risk_class != "leitura":
        return _deny(tool_name, arguments, spec.risk_class, "classe de risco não executa")
    if permission != spec.permission:
        return _deny(tool_name, arguments, spec.risk_class, PERMISSION_REASON)
    if not _arguments_match(spec.argument_names, arguments):
        return _deny(tool_name, arguments, spec.risk_class, SCHEMA_REASON)
    if spent_cost + spec.cost > budget.max_cost:
        return _deny(tool_name, arguments, spec.risk_class, COST_REASON)
    return Decision("permitir", tool_name, arguments, spec.risk_class, ALLOW_REASON)


def deny_interrupted(decision: Decision) -> Decision:
    # A parada vale mais que a decisão calculada. A classe fica para o traço.
    return _deny(decision.tool_name, decision.arguments, decision.risk_class, INTERRUPTED_REASON)


def _decide_irreversible(
    spec: ToolSpec,
    tool_name: str,
    arguments: tuple[tuple[str, str], ...],
    permission: str,
    seen_keys: tuple[tuple[str, str], ...],
) -> Decision:
    if permission != spec.permission:
        return _deny(tool_name, arguments, spec.risk_class, WRITE_PERMISSION_REASON)
    if not _arguments_match(spec.argument_names, arguments):
        return _deny(tool_name, arguments, spec.risk_class, SCHEMA_REASON)
    key = _idempotency_key(arguments)
    if key is None:
        return _deny(tool_name, arguments, spec.risk_class, SCHEMA_REASON)
    current = digest(canonical_json(dict(arguments)))
    for seen_key, seen_hash in seen_keys:
        if seen_key == key and seen_hash != current:
            return _deny(tool_name, arguments, spec.risk_class, IDEMPOTENCY_REASON)
    return Decision("pedir", tool_name, arguments, spec.risk_class, ASK_REASON)


def _deny(
    tool_name: str,
    arguments: tuple[tuple[str, str], ...],
    risk_class: str,
    reason: str,
) -> Decision:
    return Decision("negar", tool_name, arguments, risk_class, reason)


def _idempotency_key(arguments: tuple[tuple[str, str], ...]) -> str | None:
    found = ""
    for key, value in arguments:
        if key == "idempotency_key":
            found = value
    try:
        require_token(found, "idempotency_key")
    except JanusError:
        return None
    return found


def _arguments_match(names: tuple[str, ...], arguments: tuple[tuple[str, str], ...]) -> bool:
    keys = tuple(key for key, _ in arguments)
    if keys != tuple(sorted(names)):
        return False
    for _, value in arguments:
        if value.strip() == "" or len(value) > MAX_TEXT or has_hidden_char(value):
            return False
        if "/" in value or "\\" in value or ".." in value:
            return False
    return True
