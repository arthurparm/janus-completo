from __future__ import annotations

import argparse
from pathlib import Path

import tooling.dev as dev


def test_parse_args_doctor_defaults(monkeypatch):
    monkeypatch.setattr("sys.argv", ["dev.py", "doctor"])
    args = dev.parse_args()

    assert args.command == "doctor"
    assert args.host == "100.89.17.105"
    assert args.backend_port == 8000
    assert args.frontend_port == 4300
    assert args.timeout == 5.0
    assert args.json_out == ""
    assert args.verify_tls is False


def test_cmd_doctor_builds_command(monkeypatch, tmp_path: Path):
    captured: dict[str, object] = {}

    def fake_run(cmd: list[str], *, cwd: Path | None = None) -> None:
        captured["cmd"] = cmd
        captured["cwd"] = cwd

    monkeypatch.setattr(dev, "run", fake_run)

    args = argparse.Namespace(
        host="100.89.17.105",
        backend_port=8000,
        frontend_port=4300,
        timeout=7.5,
        json_out=str(tmp_path / "diag.json"),
        verify_tls=True,
    )
    dev.cmd_doctor(args)

    cmd = captured["cmd"]
    assert isinstance(cmd, list)
    assert Path(cmd[0]).name.startswith("python")
    assert cmd[1].endswith("tooling/quick_diagnostics.py")
    assert "--host" in cmd and "100.89.17.105" in cmd
    assert "--backend-port" in cmd and "8000" in cmd
    assert "--frontend-port" in cmd and "4300" in cmd
    assert "--timeout" in cmd and "7.5" in cmd
    assert "--json-out" in cmd
    assert "--verify-tls" in cmd
    assert captured["cwd"] == dev.REPO_ROOT
