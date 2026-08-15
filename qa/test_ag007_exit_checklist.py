from __future__ import annotations

import argparse
from pathlib import Path

import tooling.dev as dev
from tooling.exit_checklist import build_checklist


def test_build_checklist_codigo_contract():
    payload = build_checklist("codigo")
    assert payload["task_type"] == "codigo"
    items = payload["items"]
    assert isinstance(items, list)
    assert len(items) == 4
    assert all("id" in item and "text" in item for item in items if isinstance(item, dict))


def test_build_checklist_rejects_invalid_type():
    try:
        build_checklist("infra")
    except ValueError as exc:
        assert "Allowed: codigo, docs, deploy." in str(exc)
    else:
        raise AssertionError("build_checklist should fail for invalid task type")


def test_build_checklist_deploy_includes_identity_and_evidence_gates():
    payload = build_checklist("deploy")
    item_ids = [item["id"] for item in payload["items"] if isinstance(item, dict)]

    assert "deploy-identity-gate" in item_ids
    assert "deploy-evidence-bundle" in item_ids


def test_parse_args_checklist_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dev.py", "checklist", "--type", "deploy"])
    args = dev.parse_args()
    assert args.command == "checklist"
    assert args.task_type == "deploy"
    assert args.format == "markdown"
    assert args.out == ""


def test_cmd_checklist_builds_command(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], *, cwd: Path | None = None) -> None:
        captured["cmd"] = cmd
        captured["cwd"] = cwd

    monkeypatch.setattr(dev, "run", fake_run)

    args = argparse.Namespace(task_type="docs", format="json", out=str(tmp_path / "checklist.json"))
    dev.cmd_checklist(args)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert Path(cmd[0]).name.startswith("python")
    assert Path(cmd[1]) == dev.REPO_ROOT / "tooling" / "exit_checklist.py"
    assert "--type" in cmd and "docs" in cmd
    assert "--format" in cmd and "json" in cmd
    assert "--out" in cmd
    assert captured["cwd"] == dev.REPO_ROOT
