from __future__ import annotations

import json
import os
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Literal

from janus.entry import Identity
from janus.experience import Experience, as_hash
from janus.trace import TraceEntry
from janus.util.codec import (
    JanusError,
    as_count,
    as_gate,
    as_id,
    as_object,
    as_result_label,
    as_str,
    as_timestamp,
    exact_keys,
    parse_json,
    require_id,
    require_text,
    require_token,
    required,
)

RunStatus = Literal["aberto", "encerrado"]
PendingStatus = Literal["aberta", "aprovada", "negada", "expirada"]
_PENDING_STATUS = ("aberta", "aprovada", "negada", "expirada")


def _as_stored_label(value: object) -> str:
    text = as_str(value, "last_result_label", allow_empty=True)
    if text == "":
        return ""
    return as_result_label(text, "last_result_label")


def _as_stored_gate(value: object) -> str:
    text = as_str(value, "last_gate", allow_empty=True)
    if text == "":
        return ""
    return as_gate(text, "last_gate")


def _as_status(value: object) -> RunStatus:
    text = as_str(value, "status", allow_empty=False)
    if text == "aberto":
        return "aberto"
    if text == "encerrado":
        return "encerrado"
    raise JanusError("status inválido")


def _as_pending_status(value: object) -> PendingStatus:
    text = as_str(value, "status", allow_empty=False)
    if text == "aberta":
        return "aberta"
    if text == "aprovada":
        return "aprovada"
    if text == "negada":
        return "negada"
    if text == "expirada":
        return "expirada"
    raise JanusError("status inválido")


@dataclass(frozen=True)
class Checkpoint:
    run_id: str
    step_index: int
    spent_steps: int
    spent_cost: int
    started_at_ms: int
    status: RunStatus
    stop_reason: str
    last_gate: str
    last_result_label: str
    last_result_text: str

    @staticmethod
    def initial(run_id: str, started_at_ms: int) -> Checkpoint:
        return Checkpoint(run_id, 0, 0, 0, started_at_ms, "aberto", "", "", "", "")

    def to_json(self) -> dict[str, object]:
        return {
            "last_gate": self.last_gate,
            "last_result_label": self.last_result_label,
            "last_result_text": self.last_result_text,
            "run_id": self.run_id,
            "spent_cost": self.spent_cost,
            "spent_steps": self.spent_steps,
            "started_at_ms": self.started_at_ms,
            "status": self.status,
            "step_index": self.step_index,
            "stop_reason": self.stop_reason,
        }

    @staticmethod
    def from_json(value: object) -> Checkpoint:
        raw = as_object(value, "checkpoint")
        exact_keys(
            raw,
            (
                "last_gate",
                "last_result_label",
                "last_result_text",
                "run_id",
                "spent_cost",
                "spent_steps",
                "started_at_ms",
                "status",
                "step_index",
                "stop_reason",
            ),
            "checkpoint",
        )
        return Checkpoint(
            run_id=as_id(required(raw, "run_id"), "run_id"),
            step_index=as_count(required(raw, "step_index"), "step_index"),
            spent_steps=as_count(required(raw, "spent_steps"), "spent_steps"),
            spent_cost=as_count(required(raw, "spent_cost"), "spent_cost"),
            started_at_ms=as_count(required(raw, "started_at_ms"), "started_at_ms"),
            status=_as_status(required(raw, "status")),
            stop_reason=as_str(required(raw, "stop_reason"), "stop_reason", allow_empty=True),
            last_gate=_as_stored_gate(required(raw, "last_gate")),
            last_result_label=_as_stored_label(required(raw, "last_result_label")),
            last_result_text=as_str(required(raw, "last_result_text"), "last_result_text", allow_empty=True),
        )


@dataclass(frozen=True)
class Pending:
    run_id: str
    action: str
    effect: str
    risk_class: str
    deadline_ms: int
    status: PendingStatus
    idempotency_key: str
    arguments_hash: str
    opened_at: str
    tool_name: str

    def __post_init__(self) -> None:
        require_id(self.run_id, "run_id")
        require_text(self.action, "action")
        require_text(self.effect, "effect")
        require_token(self.risk_class, "risk_class")
        if isinstance(self.deadline_ms, bool) or not isinstance(self.deadline_ms, int) or self.deadline_ms < 0:
            raise JanusError("deadline_ms inválido")
        if self.status not in _PENDING_STATUS:
            raise JanusError("status inválido")
        require_token(self.idempotency_key, "idempotency_key")
        as_hash(self.arguments_hash, "arguments_hash")
        as_timestamp(self.opened_at, "opened_at")
        require_token(self.tool_name, "tool_name")

    def to_json(self) -> dict[str, object]:
        return {
            "action": self.action,
            "arguments_hash": self.arguments_hash,
            "deadline_ms": self.deadline_ms,
            "effect": self.effect,
            "idempotency_key": self.idempotency_key,
            "opened_at": self.opened_at,
            "risk_class": self.risk_class,
            "run_id": self.run_id,
            "status": self.status,
            "tool_name": self.tool_name,
        }

    @staticmethod
    def from_json(value: object) -> Pending:
        raw = as_object(value, "pending")
        exact_keys(
            raw,
            (
                "action",
                "arguments_hash",
                "deadline_ms",
                "effect",
                "idempotency_key",
                "opened_at",
                "risk_class",
                "run_id",
                "status",
                "tool_name",
            ),
            "pending",
        )
        return Pending(
            run_id=as_id(required(raw, "run_id"), "run_id"),
            action=as_str(required(raw, "action"), "action", allow_empty=False),
            effect=as_str(required(raw, "effect"), "effect", allow_empty=False),
            risk_class=as_str(required(raw, "risk_class"), "risk_class", allow_empty=False),
            deadline_ms=as_count(required(raw, "deadline_ms"), "deadline_ms"),
            status=_as_pending_status(required(raw, "status")),
            idempotency_key=as_str(required(raw, "idempotency_key"), "idempotency_key", allow_empty=False),
            arguments_hash=as_str(required(raw, "arguments_hash"), "arguments_hash", allow_empty=False),
            opened_at=as_timestamp(required(raw, "opened_at"), "opened_at"),
            tool_name=as_str(required(raw, "tool_name"), "tool_name", allow_empty=False),
        )


class RunStore:
    def __init__(self, root: Path) -> None:
        self._root = root

    def create(self, identity: Identity, checkpoint: Checkpoint) -> None:
        directory = self._directory(identity.run_id)
        directory.mkdir(parents=True, exist_ok=False)
        _write_json(directory / "identity.json", identity.to_json())
        _write_json(directory / "checkpoint.json", checkpoint.to_json())
        (directory / "trace.jsonl").write_text("", encoding="utf-8", newline="\n")
        (directory / "experiences.jsonl").write_text("", encoding="utf-8", newline="\n")
        (directory / "pending.jsonl").write_text("", encoding="utf-8", newline="\n")

    def load_identity(self, run_id: str) -> Identity:
        return Identity.from_json(_read_json(self._directory(run_id) / "identity.json"))

    def load_checkpoint(self, run_id: str) -> Checkpoint:
        checkpoint = Checkpoint.from_json(_read_json(self._directory(run_id) / "checkpoint.json"))
        if self.is_interrupted(run_id):
            return replace(checkpoint, status="encerrado", stop_reason="interrompido")
        return checkpoint

    def mark_interrupted(self, run_id: str) -> None:
        # Arquivo à parte, que o passo não escreve: nenhuma gravação posterior reabre o run.
        (self._directory(run_id) / "interrupted").touch()

    def is_interrupted(self, run_id: str) -> bool:
        return (self._directory(run_id) / "interrupted").is_file()

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        _write_json(self._directory(checkpoint.run_id) / "checkpoint.json", checkpoint.to_json())

    def append_trace(self, entry: TraceEntry) -> None:
        if entry.weight_version != "":
            raise JanusError("versão de peso nasce vazia")
        _append_line(self._directory(entry.run_id) / "trace.jsonl", entry.to_json())

    def append_experience(self, experience: Experience) -> None:
        # Fase A: a voz não verifica e o peso ainda não existe.
        if not experience.outcome.is_empty():
            raise JanusError("outcome nasce vazio")
        if experience.weight_version_before != "" or experience.weight_version_after != "":
            raise JanusError("versão de peso nasce vazia")
        _append_line(self._directory(experience.run_id) / "experiences.jsonl", experience.to_json())

    def append_pending(self, pending: Pending) -> None:
        current = self.read_pending(pending.run_id)
        for item in current:
            if item.idempotency_key != pending.idempotency_key:
                continue
            if item.arguments_hash != pending.arguments_hash:
                raise JanusError("chave de idempotência já usada")
            return
        _append_line(self._directory(pending.run_id) / "pending.jsonl", pending.to_json())

    def read_trace(self, run_id: str) -> tuple[TraceEntry, ...]:
        path = self._directory(run_id) / "trace.jsonl"
        return tuple(TraceEntry.from_json(item) for item in _read_lines(path))

    def read_experiences(self, run_id: str) -> tuple[Experience, ...]:
        path = self._directory(run_id) / "experiences.jsonl"
        return tuple(Experience.from_json(item) for item in _read_lines(path))

    def read_pending(self, run_id: str) -> tuple[Pending, ...]:
        path = self._directory(run_id) / "pending.jsonl"
        return tuple(Pending.from_json(item) for item in _read_lines(path))

    def settle_pending(self, pending: Pending, status: PendingStatus) -> Pending:
        if status != "aprovada" and status != "negada":
            raise JanusError("status inválido")
        current = self.read_pending(pending.run_id)
        rows: list[Pending] = []
        updated: Pending | None = None
        for item in current:
            if updated is None and _same_request(item, pending):
                if (
                    item.action != pending.action
                    or item.effect != pending.effect
                    or item.risk_class != pending.risk_class
                ):
                    raise JanusError("pendência não confere")
                if item.status != "aberta":
                    raise JanusError("pendência não está aberta")
                updated = replace(item, status=status)
                rows.append(updated)
            else:
                rows.append(item)
        if updated is None:
            raise JanusError("pendência ausente")
        _write_lines(
            self._directory(pending.run_id) / "pending.jsonl",
            tuple(item.to_json() for item in rows),
        )
        return updated

    def _directory(self, run_id: str) -> Path:
        require_id(run_id, "run_id")
        return self._root / "runs" / run_id


def _write_json(path: Path, payload: dict[str, object]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def _append_line(path: Path, payload: dict[str, object]) -> None:
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(line + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_lines(path: Path, rows: tuple[dict[str, object], ...]) -> None:
    body = "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n" for row in rows
    )
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def _same_request(stored: Pending, incoming: Pending) -> bool:
    return (
        stored.idempotency_key == incoming.idempotency_key
        and stored.arguments_hash == incoming.arguments_hash
        and stored.tool_name == incoming.tool_name
    )


def _read_json(path: Path) -> object:
    if not path.is_file():
        raise JanusError("run ausente")
    return parse_json(path.read_text(encoding="utf-8"))


def _read_lines(path: Path) -> tuple[object, ...]:
    if not path.is_file():
        raise JanusError("run ausente")
    rows: list[object] = []
    # Só a quebra de linha separa registros. U+2028, U+2029 e U+0085 ficam dentro do JSON.
    for line in path.read_text(encoding="utf-8").split("\n"):
        if line.strip() == "":
            continue
        rows.append(parse_json(line))
    return tuple(rows)
