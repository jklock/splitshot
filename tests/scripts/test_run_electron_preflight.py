from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "testing" / "run_electron_preflight.py"
SPEC = importlib.util.spec_from_file_location("run_electron_preflight_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_preflight_uses_packaged_artifact_validator_on_macos(monkeypatch) -> None:
    commands: list[list[str]] = []
    summaries: list[dict] = []

    monkeypatch.setattr(MODULE.sys, "platform", "darwin")
    monkeypatch.setattr(MODULE, "run", lambda command: commands.append(command) or 0.1)
    monkeypatch.setattr(
        MODULE,
        "write_release_gate_summary",
        lambda **kwargs: summaries.append(kwargs) or kwargs,
    )

    assert MODULE.main() == 0
    assert ["uv", "run", "python", "scripts/testing/test_packaged_artifact.py"] in commands
    assert not ["uv", "run", "python", "scripts/testing/test_electron_app.py"] in commands
    assert summaries[-1]["status"] == "passed"
