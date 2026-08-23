from __future__ import annotations

import importlib.util
import sys
import urllib.error
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


def test_prepare_project_copy_supports_project_input_media_layout(
    monkeypatch, tmp_path: Path
) -> None:
    source = tmp_path / "project"
    artifact_root = tmp_path / "artifacts"
    (source / "CSV").mkdir(parents=True)
    (source / "Input").mkdir()
    (source / "project.json").write_text("{}", encoding="utf-8")
    (source / "CSV" / "IDPA.csv").write_text("stage,data\n", encoding="utf-8")
    for name in ("Stage2.MP4", "Stage3.MP4", "Stage4.MP4"):
        (source / "Input" / name).write_bytes(b"video")

    monkeypatch.setattr(
        MODULE,
        "_normalize_project_for_audit",
        lambda project_root: {
            "media": str(MODULE._project_media_path(project_root, "Stage2.MP4"))
        },
    )

    copy_root, normalized = MODULE._prepare_project_copy(source, artifact_root)

    assert (copy_root / "Input" / "Stage2.MP4").exists()
    assert normalized["media"] == str(copy_root / "Input" / "Stage2.MP4")


def test_build_parser_defaults_slice_to_full() -> None:
    parser = MODULE.build_parser()
    args = parser.parse_args([])
    assert args.slice == "full"
    assert args.fresh_project_copy is False


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


def test_prepare_project_copy_reuses_matching_cached_copy(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "05072026"
    artifact_root = tmp_path / "artifacts"
    (source / "CSV").mkdir(parents=True)
    (source / "project.json").write_text('{"name":"source"}', encoding="utf-8")
    (source / "CSV" / "IDPA.csv").write_text("stage,data\n", encoding="utf-8")
    for name in ("Stage2.MP4", "Stage3.MP4", "Stage4.MP4"):
        (source / name).write_bytes(b"video")

    calls: list[Path] = []
    monkeypatch.setattr(
        MODULE,
        "_normalize_project_for_audit",
        lambda project_root: calls.append(project_root) or {"project_root": str(project_root)},
    )

    first_copy_root, _ = MODULE._prepare_project_copy(source, artifact_root)
    first_project_path = first_copy_root / "project.json"
    first_inode = first_project_path.stat().st_ino

    second_copy_root, _ = MODULE._prepare_project_copy(source, artifact_root)

    assert second_copy_root == first_copy_root
    assert (second_copy_root / "project.json").stat().st_ino == first_inode
    assert calls == [first_copy_root, second_copy_root]


def test_api_post_raises_when_browser_runtime_reports_failure() -> None:
    class FakePage:
        def evaluate(self, script, payload=None):
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
        def click(self, force=False):
            assert force is True

    class FakePage:
        def locator(self, selector):
            assert selector == "#queue-combined-btn"
            return FakeLocator()

        def wait_for_function(self, script, arg=None, timeout=None):
            return None

        def evaluate(self, script, payload=None):
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
    monkeypatch.setattr(
        MODULE, "_verify_video_file", lambda path: {"path": str(path), "exists": True}
    )

    result = MODULE._run_combined_export(FakePage(), tmp_path, tmp_path)

    assert result["output_path"] == str(combined_path)
    assert result["verification"]["exists"] is True
    assert result["error"] is None


def test_requeue_all_stages_clears_existing_queue_before_readding(monkeypatch) -> None:
    calls: list[tuple[str, str]] = []

    class FakePage:
        def evaluate(self, script, payload=None):
            if "state?.project?.queue" in script:
                return ["stage-1", "stage-2"]
            if "state?.project?.stages" in script:
                return ["stage-1", "stage-2", "stage-3"]
            raise AssertionError(script)

        def wait_for_function(self, script, arg=None, timeout=None):
            assert "state?.project?.queue" in script

    monkeypatch.setattr(
        MODULE,
        "_api_post",
        lambda page, path, payload: calls.append((path, payload["stage_id"])),
    )
    monkeypatch.setattr(
        MODULE,
        "_wait_for_queue_statuses",
        lambda page, statuses, expected_count, timeout_ms=300_000: [],
    )

    MODULE._requeue_all_stages(FakePage())

    assert calls == [
        ("/api/project/queue/remove", "stage-1"),
        ("/api/project/queue/remove", "stage-2"),
        ("/api/project/queue/add", "stage-1"),
        ("/api/project/queue/add", "stage-2"),
        ("/api/project/queue/add", "stage-3"),
    ]


def test_warm_installed_app_media_ignores_missing_urls(monkeypatch) -> None:
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return None

        def read(self, _size):
            return b"x"

    calls: list[str] = []

    def fake_urlopen(url, timeout):
        calls.append(url)
        if url.endswith("/media/secondary"):
            raise urllib.error.HTTPError(url, 404, "Not Found", hdrs=None, fp=None)
        return FakeResponse()

    monkeypatch.setattr(MODULE, "urlopen", fake_urlopen)

    MODULE._warm_installed_app_media(
        "http://127.0.0.1:9999",
        {
            "media": {"secondary_url": "/media/secondary"},
            "project": {"merge_sources": [{"id": "merge-1"}]},
        },
    )

    assert calls == [
        "http://127.0.0.1:9999/media/primary",
        "http://127.0.0.1:9999/media/secondary",
        "http://127.0.0.1:9999/media/merge/merge-1",
    ]


def test_terminate_process_uses_process_group_on_posix(monkeypatch) -> None:
    calls: list[tuple[str, int, object]] = []

    class FakeProc:
        pid = 4321

        def poll(self):
            return None

        def wait(self, timeout=None):
            calls.append(("wait", self.pid, timeout))
            return 0

        def terminate(self):
            calls.append(("terminate", self.pid, None))

        def kill(self):
            calls.append(("kill", self.pid, None))

    monkeypatch.setattr(MODULE.os, "name", "posix")
    monkeypatch.setattr(MODULE.os, "getpgid", lambda pid: pid, raising=False)
    monkeypatch.setattr(
        MODULE.os,
        "killpg",
        lambda pgid, sig: calls.append(("killpg", pgid, sig)),
        raising=False,
    )

    MODULE._terminate_process(FakeProc())

    assert ("killpg", 4321, MODULE.signal.SIGTERM) in calls
    assert ("wait", 4321, 10) in calls


def test_terminate_matching_processes_kills_matching_bundle_descendants(
    monkeypatch, tmp_path: Path
) -> None:
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

    def fake_run(cmd, capture_output, text, timeout, check):
        assert cmd == ["ps", "-axo", "pid=,ppid=,command="]
        assert capture_output is True
        assert text is True
        assert timeout == 10
        assert check is True
        return FakeCompleted()

    def fake_kill(pid, sig):
        force_signal = getattr(MODULE.signal, "SIGKILL", MODULE.signal.SIGTERM)
        if sig in (MODULE.signal.SIGTERM, force_signal):
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
