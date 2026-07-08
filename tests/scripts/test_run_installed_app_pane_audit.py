from __future__ import annotations

import importlib.util
import sys

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "audits" / "browser" / "run_installed_app_pane_audit.py"
SPEC = importlib.util.spec_from_file_location("installed_app_pane_audit_module", MODULE_PATH)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def test_categorize_failure_maps_copy_to_markup() -> None:
    category, code_change_needed = MODULE._categorize_failure(
        "unexpected helper/explanatory text present: ['Review the export settings already prepared']"
    )
    assert category == "markup/copy"
    assert code_change_needed is True


def test_categorize_failure_maps_spacing_to_layout() -> None:
    category, code_change_needed = MODULE._categorize_failure(
        "card padding 20.00px drifts from Project/Score/Splits baseline 12.00px"
    )
    assert category == "CSS/layout"
    assert code_change_needed is True


def test_compute_visual_findings_uses_project_score_splits_baseline() -> None:
    dom_summary = {
        "pane_metrics": {
            "project": {
                "title_font_size_px": 20.0,
                "summary_font_size_px": 12.0,
                "label_font_size_px": [12.0],
                "card_padding_px": [12.0],
                "input_height_px": [36.0],
                "toggle_right_offsets_px": [10.0],
                "has_hint_text": [],
            },
            "scoring": {
                "title_font_size_px": 20.0,
                "summary_font_size_px": 12.0,
                "label_font_size_px": [12.0],
                "card_padding_px": [12.0],
                "input_height_px": [36.0],
                "toggle_right_offsets_px": [10.0],
                "has_hint_text": [],
            },
            "timing": {
                "title_font_size_px": 20.0,
                "summary_font_size_px": 12.0,
                "label_font_size_px": [12.0],
                "card_padding_px": [12.0],
                "input_height_px": [36.0],
                "toggle_right_offsets_px": [10.0],
                "has_hint_text": [],
            },
            "queue": {
                "title_font_size_px": 20.0,
                "summary_font_size_px": 12.0,
                "label_font_size_px": [12.0],
                "card_padding_px": [19.0],
                "input_height_px": [36.0],
                "toggle_right_offsets_px": [10.0],
                "has_hint_text": ["Review the export settings already prepared"],
            },
        }
    }

    findings = MODULE._compute_visual_findings(dom_summary)

    assert len(findings) == 2
    assert findings[0]["pane"] == "Queue"
    assert findings[0]["category"] == "CSS/layout"
    assert findings[1]["category"] == "markup/copy"


def test_prepare_project_copy_copies_mutable_files(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "05072026"
    artifact_root = tmp_path / "artifacts"
    (source / "CSV").mkdir(parents=True)
    (source / "project.json").write_text("{}", encoding="utf-8")
    (source / "CSV" / "IDPA.csv").write_text("stage,data\n", encoding="utf-8")
    for name in ("Stage2.MP4", "Stage3.MP4", "Stage4.MP4"):
        (source / name).write_bytes(b"video")

    monkeypatch.setattr(
        MODULE,
        "_normalize_project_for_audit",
        lambda project_root: {"project_root": str(project_root)},
    )

    copy_root, _ = MODULE._prepare_project_copy(source, artifact_root)

    source_project = source / "project.json"
    copy_project = copy_root / "project.json"
    source_csv = source / "CSV" / "IDPA.csv"
    copy_csv = copy_root / "CSV" / "IDPA.csv"
    assert copy_project.exists()
    assert copy_csv.exists()
    assert source_project.stat().st_ino != copy_project.stat().st_ino
    assert source_csv.stat().st_ino != copy_csv.stat().st_ino


def test_project_copy_mutation_does_not_change_source_project(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "05072026"
    artifact_root = tmp_path / "artifacts"
    (source / "CSV").mkdir(parents=True)
    (source / "project.json").write_text('{"name":"source"}', encoding="utf-8")
    (source / "CSV" / "IDPA.csv").write_text("stage,data\n", encoding="utf-8")
    for name in ("Stage2.MP4", "Stage3.MP4", "Stage4.MP4"):
        (source / name).write_bytes(b"video")

    monkeypatch.setattr(
        MODULE,
        "_normalize_project_for_audit",
        lambda project_root: {"project_root": str(project_root)},
    )

    before = MODULE._file_fingerprint(source / "project.json")
    copy_root, _ = MODULE._prepare_project_copy(source, artifact_root)
    (copy_root / "project.json").write_text('{"name":"copy"}', encoding="utf-8")

    MODULE._assert_file_unchanged(source / "project.json", before)
    assert (source / "project.json").read_text(encoding="utf-8") == '{"name":"source"}'


def test_api_post_raises_when_browser_runtime_reports_failure() -> None:
    class FakePage:
        def evaluate(self, script, payload=None):  # noqa: ANN001
            if "callApi(path, payload)" in script:
                return None
            if "status-message" in script:
                return "queue failed"
            raise AssertionError(script)

    with pytest.raises(RuntimeError, match="queue failed"):
        MODULE._api_post(FakePage(), "/api/project/queue/add", {"stage_id": "stage-1"})


def test_run_combined_export_uses_state_combined_output_path(monkeypatch, tmp_path: Path) -> None:
    combined_path = tmp_path / "Output" / "proof-combined.mp4"
    combined_path.parent.mkdir(parents=True, exist_ok=True)
    combined_path.write_bytes(b"video")

    class FakeLocator:
        def click(self, force=False):  # noqa: ANN001, FBT002
            assert force is True

    class FakePage:
        def locator(self, selector):  # noqa: ANN001
            assert selector == "#queue-combined-btn"
            return FakeLocator()

        def wait_for_function(self, script, arg=None, timeout=None):  # noqa: ANN001
            return None

        def evaluate(self, script, payload=None):  # noqa: ANN001
            if "state?.project?.queue" in script:
                return [{"stage_id": "stage-1", "status": "complete"}] * 3
            if "last_combined_output_path" in script:
                return str(combined_path)
            if "status-message" in script:
                return ""
            raise AssertionError(script)

    monkeypatch.setattr(MODULE, "_requeue_all_stages", lambda page: None)
    monkeypatch.setattr(MODULE, "_set_tool", lambda page, tool: None)
    monkeypatch.setattr(
        MODULE,
        "_capture_export_log",
        lambda page, artifact_root, suffix: {"screenshot": "", "text_file": "", "line_count": 0},
    )
    monkeypatch.setattr(MODULE, "_verify_video_file", lambda path: {"path": str(path), "exists": True})

    result = MODULE._run_combined_export(FakePage(), tmp_path, tmp_path)

    assert result["output_path"] == str(combined_path)
    assert result["verification"]["exists"] is True
    assert result["error"] is None


def test_terminate_process_uses_process_group_on_posix(monkeypatch) -> None:
    calls: list[tuple[str, int, object]] = []

    class FakeProc:
        pid = 4321

        def poll(self):  # noqa: ANN001
            return None

        def wait(self, timeout=None):  # noqa: ANN001
            calls.append(("wait", self.pid, timeout))
            return 0

        def terminate(self):  # noqa: ANN001
            calls.append(("terminate", self.pid, None))

        def kill(self):  # noqa: ANN001
            calls.append(("kill", self.pid, None))

    monkeypatch.setattr(MODULE.os, "name", "posix")
    monkeypatch.setattr(MODULE.os, "getpgid", lambda pid: pid)
    monkeypatch.setattr(MODULE.os, "killpg", lambda pgid, sig: calls.append(("killpg", pgid, sig)))

    MODULE._terminate_process(FakeProc())

    assert ("killpg", 4321, MODULE.signal.SIGTERM) in calls
    assert ("wait", 4321, 10) in calls


def test_terminate_matching_processes_kills_matching_bundle_descendants(monkeypatch, tmp_path: Path) -> None:
    bundle = tmp_path / "SplitShot.app"
    ps_output = "\n".join(
        [
            "10 1 /bin/zsh -lc uv run python scripts/audits/browser/run_installed_app_pane_audit.py --app /tmp/SplitShot.app",
            "999 10 /Volumes/Storage/GitHub/splitshot/.venv/bin/python scripts/audits/browser/run_installed_app_pane_audit.py --app /tmp/SplitShot.app",
            f"111 1 {bundle}/Contents/MacOS/SplitShot /tmp/project.ssproj",
            f"222 111 {bundle}/Contents/Resources/bundle/.venv/bin/python -m splitshot --headless",
            "333 1 /usr/bin/other-process",
        ]
    )
    signals: list[tuple[int, object]] = []
    alive = {111, 222}

    class FakeCompleted:
        stdout = ps_output

    def fake_run(cmd, capture_output, text, timeout, check):  # noqa: ANN001
        assert cmd == ["ps", "-axo", "pid=,ppid=,command="]
        assert capture_output is True
        assert text is True
        assert timeout == 10
        assert check is True
        return FakeCompleted()

    def fake_kill(pid, sig):  # noqa: ANN001
        if sig in (MODULE.signal.SIGTERM, MODULE.signal.SIGKILL):
            signals.append((pid, sig))
            alive.discard(pid)
            return
        if pid in alive:
            return
        raise ProcessLookupError

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)
    monkeypatch.setattr(MODULE.os, "getpid", lambda: 999)
    monkeypatch.setattr(MODULE.os, "kill", fake_kill)

    MODULE._terminate_matching_processes(bundle)

    assert (111, MODULE.signal.SIGTERM) in signals
    assert (222, MODULE.signal.SIGTERM) in signals
    assert all(pid != 333 for pid, _sig in signals)
    assert all(pid != 10 for pid, _sig in signals)
    assert all(pid != 999 for pid, _sig in signals)
