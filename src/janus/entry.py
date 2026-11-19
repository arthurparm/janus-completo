from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from janus.adapter import Proposal, ScriptedAdapter
from janus.util.codec import (
    JanusError,
    as_bool,
    as_count,
    as_id,
    as_object,
    as_str,
    exact_keys,
    parse_json,
    require_text,
    require_token,
    required,
)


@dataclass(frozen=True)
class Budget:
    max_steps: int
    deadline_ms: int
    max_cost: int

    def __post_init__(self) -> None:
        for label, value in (
            ("max_steps", self.max_steps),
            ("deadline_ms", self.deadline_ms),
            ("max_cost", self.max_cost),
        ):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise JanusError(f"{label} inválido")

    def to_json(self) -> dict[str, object]:
        return {
            "deadline_ms": self.deadline_ms,
            "max_cost": self.max_cost,
            "max_steps": self.max_steps,
        }

    @staticmethod
    def from_json(value: object) -> Budget:
        raw = as_object(value, "budget")
        exact_keys(raw, ("deadline_ms", "max_cost", "max_steps"), "budget")
        return Budget(
            max_steps=as_count(required(raw, "max_steps"), "max_steps"),
            deadline_ms=as_count(required(raw, "deadline_ms"), "deadline_ms"),
            max_cost=as_count(required(raw, "max_cost"), "max_cost"),
        )


@dataclass(frozen=True)
class OpenRunRequest:
    requester: str
    permission: str
    budget: Budget
    voice_is_model: bool
    model_id: str
    task: str

    def __post_init__(self) -> None:
        require_token(self.requester, "requester")
        require_token(self.permission, "permission")
        require_token(self.model_id, "model_id")
        require_text(self.task, "task")
        if self.voice_is_model is not True:
            raise JanusError("a entrada tem de registrar que a voz é um modelo")

    def to_json(self) -> dict[str, object]:
        return {
            "budget": self.budget.to_json(),
            "model_id": self.model_id,
            "permission": self.permission,
            "requester": self.requester,
            "task": self.task,
            "voice_is_model": self.voice_is_model,
        }


@dataclass(frozen=True)
class Identity:
    run_id: str
    request: OpenRunRequest

    def to_json(self) -> dict[str, object]:
        body = self.request.to_json()
        body["run_id"] = self.run_id
        return body

    @staticmethod
    def from_json(value: object) -> Identity:
        raw = as_object(value, "identity")
        exact_keys(
            raw,
            ("budget", "model_id", "permission", "requester", "run_id", "task", "voice_is_model"),
            "identity",
        )
        request = OpenRunRequest(
            requester=as_str(required(raw, "requester"), "requester", allow_empty=False),
            permission=as_str(required(raw, "permission"), "permission", allow_empty=False),
            budget=Budget.from_json(required(raw, "budget")),
            voice_is_model=as_bool(required(raw, "voice_is_model"), "voice_is_model"),
            model_id=as_str(required(raw, "model_id"), "model_id", allow_empty=False),
            task=as_str(required(raw, "task"), "task", allow_empty=False),
        )
        return Identity(as_id(required(raw, "run_id"), "run_id"), request)


def main(argv: list[str]) -> int:
    from janus.loop import Runtime

    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(prog="janus")
    parser.add_argument("--root", required=True)
    parser.add_argument("--request", required=True)
    args = parser.parse_args(argv)
    try:
        request, proposal, records = _load_request(Path(args.request))
        runtime = Runtime(Path(args.root), records)
        run_id = runtime.open_run(request)
        result = runtime.step(run_id, ScriptedAdapter(request.model_id, (proposal,)))
    except JanusError as error:
        sys.stderr.write(error.reason + "\n")
        return 2
    sys.stdout.write(json.dumps(result.to_json(), ensure_ascii=False, sort_keys=True) + "\n")
    return 0


def _load_request(path: Path) -> tuple[OpenRunRequest, Proposal, dict[str, str]]:
    raw = as_object(parse_json(path.read_text(encoding="utf-8")), "request")
    exact_keys(
        raw,
        ("budget", "model_id", "permission", "proposal", "records", "requester", "task", "voice_is_model"),
        "request",
    )
    request = OpenRunRequest(
        requester=as_str(required(raw, "requester"), "requester", allow_empty=False),
        permission=as_str(required(raw, "permission"), "permission", allow_empty=False),
        budget=Budget.from_json(required(raw, "budget")),
        voice_is_model=as_bool(required(raw, "voice_is_model"), "voice_is_model"),
        model_id=as_str(required(raw, "model_id"), "model_id", allow_empty=False),
        task=as_str(required(raw, "task"), "task", allow_empty=False),
    )
    return request, Proposal.from_json(required(raw, "proposal")), _records(required(raw, "records"))


def _records(value: object) -> dict[str, str]:
    raw = as_object(value, "records")
    records: dict[str, str] = {}
    for key, item in raw.items():
        records[key] = as_str(item, "records", allow_empty=True)
    return records
