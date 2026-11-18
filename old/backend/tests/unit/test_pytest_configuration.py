import os
import subprocess
import sys
import tomllib
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_pytest_pythonpath_points_to_backend_package_root() -> None:
    config = tomllib.loads((BACKEND_ROOT / "pyproject.toml").read_text(encoding="utf-8"))

    assert config["tool"]["pytest"]["ini_options"]["pythonpath"] == ["."]


def test_conftest_preserves_explicit_environment_and_has_no_audit_patch() -> None:
    conftest_path = BACKEND_ROOT / "tests" / "conftest.py"
    source = conftest_path.read_text(encoding="utf-8")
    env = os.environ.copy()
    env["APP_ENV"] = "explicit-profile"
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import os, runpy; "
                f"runpy.run_path({str(conftest_path)!r}); "
                "print(os.environ['APP_ENV'])"
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        env=env,
    )

    assert result.stdout.strip() == "explicit-profile"
    assert "record_audit_event_direct" not in source
    assert "monkeypatch" not in source
