from __future__ import annotations

import errno
import inspect
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import splitshot.browser.server as browser_server_module
import splitshot.ui.controller as controller_module

from splitshot.browser.activity import ActivityLogger
from splitshot.analysis.detection import DetectionResult
from splitshot.browser.server import (
    BrowserControlServer,
    QuietThreadingHTTPServer,
    display_name_for_path,
    is_expected_disconnect_error,
)
from splitshot.browser.state import browser_state
from splitshot.domain.models import OverlayPosition, Project, ShotEvent, ShotSource, VideoAsset
from splitshot.ui.controller import ProjectController


REPO_ROOT = Path(__file__).resolve().parents[2]
EXAMPLES_DIR = REPO_ROOT / "example_data"

DIRECT_PROJECT_JSON_ASSERTION_TESTS_BY_ROUTE: dict[str, tuple[str, ...]] = {
    "/api/project/details": ("test_browser_project_details_autosave_persists_after_reopen",),
    "/api/project/practiscore": ("test_browser_autosave_persists_practiscore_routes_to_project_json",),
    "/api/project/ui-state": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/threshold": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/shotml-settings": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/shotml/proposals": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/shotml/apply-proposal": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/shotml/discard-proposal": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/analysis/shotml/reset-defaults": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/settings/reset-defaults": ("test_browser_settings_reset_defaults_restores_project_state",),
    "/api/beep": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/shots/add": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/shots/move": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/shots/restore": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/shots/delete": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/shots/select": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/scoring": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/scoring/profile": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/scoring/score": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/scoring/restore": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/scoring/position": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/events/add": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/events/delete": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/files/primary": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/files/secondary": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/files/merge": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/files/practiscore": ("test_browser_autosave_persists_practiscore_routes_to_project_json",),
    "/api/import/primary": ("test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json",),
    "/api/import/secondary": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/import/merge": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/overlay": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/popups": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/merge": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/merge/remove": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/merge/source": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/sync": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/swap": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/export/settings": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/export/preset": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
    "/api/export": ("test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json",),
}

PROJECT_LIFECYCLE_POST_ROUTES = {
    "/api/project/new",
    "/api/project/open",
    "/api/project/save",
    "/api/project/delete",
}

NON_PROJECT_JSON_POST_ROUTES = {
    "/api/activity",
    "/api/dialog/path",
    "/api/project/probe",
    "/api/settings",
}


def _post_json(url: str, payload: dict) -> dict:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _post_multipart(url: str, field_name: str, filename: str, payload: bytes) -> dict:
    boundary = "----splitshot-test-boundary"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'
        "Content-Type: video/mp4\r\n\r\n"
    ).encode("utf-8") + payload + f"\r\n--{boundary}--\r\n".encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _read_project_json(project_path: Path) -> dict:
    return json.loads((project_path / "project.json").read_text(encoding="utf-8"))


def _changed_place_idpa_results(tmp_path: Path) -> Path:
    source = (EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_text(encoding="utf-8")
    source = source.replace(
        "4,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,29.83,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
        "6,CO,UN,Klockenkemper,John,A1035577,,1,1,0,,83.01,11,1,1,,,,14.55,1,,,,,,,20.57,5,1,,,,,,18.62,5,,,,,,,20.01,,,1,,,,",
    )
    path = tmp_path / "thursday-night.csv"
    path.write_text(source, encoding="utf-8")
    return path


def _shot_from_project_json(project_payload: dict, shot_id: str) -> dict:
    return next(shot for shot in project_payload["analysis"]["shots"] if shot["id"] == shot_id)


def _merge_source_from_project_json(project_payload: dict, source_id: str) -> dict:
    return next(source for source in project_payload["merge_sources"] if source["id"] == source_id)


def _extract_browser_post_routes_from_server_source() -> set[str]:
    server_source = Path(browser_server_module.__file__).read_text(encoding="utf-8")
    direct_routes = set(re.findall(r'if self\.path == "([^"]+)"', server_source))
    mapped_routes = set(re.findall(r'"(/api/[^"]+)": self\._[A-Za-z0-9_]+', server_source))
    return direct_routes | mapped_routes


def test_browser_foreground_server_handles_keyboard_interrupt_cleanly(capsys) -> None:
    class InterruptingHTTPD:
        server_address = ("127.0.0.1", 8765)

        def __init__(self) -> None:
            self.closed = False

        def serve_forever(self) -> None:
            raise KeyboardInterrupt

        def server_close(self) -> None:
            self.closed = True

    fake_httpd = InterruptingHTTPD()
    server = BrowserControlServer(port=0)
    server._build_httpd = lambda: fake_httpd  # type: ignore[method-assign]

    server.serve_forever(open_browser=False)

    assert fake_httpd.closed is True
    assert "SplitShot browser control stopped." in capsys.readouterr().out


def test_browser_foreground_server_reports_failed_browser_open(monkeypatch, capsys) -> None:
    opened_urls: list[str] = []

    def fake_open(url: str) -> bool:
        opened_urls.append(url)
        return False

    monkeypatch.setattr(browser_server_module.webbrowser, "open", fake_open)

    class FakeHTTPD:
        server_address = ("127.0.0.1", 8765)

        def __init__(self) -> None:
            self.closed = False
            self.started = False

        def serve_forever(self) -> None:
            self.started = True

        def server_close(self) -> None:
            self.closed = True

    fake_httpd = FakeHTTPD()
    server = BrowserControlServer(port=0)
    server._build_httpd = lambda: fake_httpd  # type: ignore[method-assign]

    server.serve_forever(open_browser=True)

    output = capsys.readouterr().out
    assert opened_urls == [server.url]
    assert "Failed to open the local browser automatically." in output
    assert f"Open SplitShot manually at {server.url}" in output
    assert fake_httpd.closed is True


def test_browser_foreground_server_reports_bind_failure(monkeypatch, capsys) -> None:
    def failing_build_httpd(self) -> ThreadingHTTPServer:
        raise OSError(errno.EADDRINUSE, "Address already in use")

    server = BrowserControlServer(port=0)
    monkeypatch.setattr(server, "_build_httpd", failing_build_httpd.__get__(server, BrowserControlServer))

    with pytest.raises(OSError):
        server.serve_forever(open_browser=False)

    output = capsys.readouterr().out
    assert "SplitShot could not bind to" in output
    assert "Use --port to select a different port" in output


def test_browser_http_server_suppresses_expected_disconnect_errors(monkeypatch) -> None:
    calls: list[tuple[object, tuple[str, int]]] = []

    def fake_handle_error(self, request, client_address) -> None:
        calls.append((request, client_address))

    monkeypatch.setattr(ThreadingHTTPServer, "handle_error", fake_handle_error)
    httpd = QuietThreadingHTTPServer(("127.0.0.1", 0), BaseHTTPRequestHandler)
    try:
        try:
            raise BrokenPipeError
        except BrokenPipeError:
            httpd.handle_error(object(), ("127.0.0.1", 1))
        assert calls == []

        try:
            raise RuntimeError("real failure")
        except RuntimeError:
            httpd.handle_error(object(), ("127.0.0.1", 1))
        assert len(calls) == 1
    finally:
        httpd.server_close()


def test_expected_disconnect_helper_matches_browser_cancel_errors() -> None:
    assert is_expected_disconnect_error(BrokenPipeError())
    assert is_expected_disconnect_error(ConnectionResetError())
    assert is_expected_disconnect_error(ConnectionAbortedError())
    assert is_expected_disconnect_error(OSError(errno.ENOBUFS, "No buffer space available"))
    assert not is_expected_disconnect_error(RuntimeError())


def test_display_name_fallback_strips_browser_session_prefix() -> None:
    assert display_name_for_path("/tmp/1234567890abcdef1234567890abcdef_Stage1.MP4", "None") == "Stage1.MP4"
    assert display_name_for_path("", "None") == "None"


def test_activity_logger_defaults_to_file_only(tmp_path, capsys) -> None:
    logger = ActivityLogger(log_dir=tmp_path)

    logger.log("http.get", path="/")

    assert capsys.readouterr().out == ""
    log_text = logger.path.read_text(encoding="utf-8")
    assert '"event": "http.get"' in log_text
    assert '"level": "debug"' in log_text


def test_activity_logger_console_level_filters_events(tmp_path, capsys) -> None:
    logger = ActivityLogger(log_dir=tmp_path, console_level="info")

    logger.log("http.get", path="/")
    logger.log("server.initialized", host="127.0.0.1", port=8765, log_path="/tmp/splitshot.log")

    output = capsys.readouterr().out
    assert "server.initialized" in output
    assert '"level": "info"' in output
    assert "http.get" not in output


def test_browser_server_primes_export_runtime_on_construction(monkeypatch) -> None:
    calls: list[str] = []

    def fake_prepare_export_runtime() -> None:
        calls.append(threading.current_thread().name)

    monkeypatch.setattr(browser_server_module, "prepare_export_runtime", fake_prepare_export_runtime)
    server = BrowserControlServer(port=0)
    try:
        assert calls == [threading.current_thread().name]
    finally:
        server.shutdown()


def test_browser_activity_logger_writes_run_file_and_browser_events(tmp_path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_dir=tmp_path)
    server.start_background(open_browser=False)
    try:
        _get_json(f"{server.url}api/state")
        payload = _post_json(
            f"{server.url}api/activity",
            {"event": "test.click", "detail": {"target": "waveform"}},
        )

        assert payload == {"ok": True}
        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "server.initialized" in log_text
        assert '"level": "info"' in log_text
        assert '"level": "debug"' in log_text
        assert "http.get" in log_text
        assert "browser.activity" in log_text
        assert "test.click" in log_text
    finally:
        server.shutdown()


def test_browser_activity_poll_returns_recent_entries(tmp_path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, log_dir=tmp_path)
    server.start_background(open_browser=False)
    try:
        server.activity.log("api.export.progress", progress=0.35)
        server.activity.log("api.export.log", line="Encoder command: ffmpeg ...")

        payload = _get_json(f"{server.url}api/activity/poll?after=0")

        assert payload["cursor"] >= 2
        events = [entry["event"] for entry in payload["entries"]]
        assert "api.export.progress" in events
        assert "api.export.log" in events
        assert any(entry.get("line") == "Encoder command: ffmpeg ..." for entry in payload["entries"])
    finally:
        server.shutdown()


def test_browser_server_sets_security_headers_on_state_and_static_routes() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with urllib.request.urlopen(f"{server.url}api/state", timeout=30) as response:
            csp = response.headers["Content-Security-Policy"]
            assert "default-src 'none'" in csp
            assert "script-src 'self'" in csp
            assert "style-src 'self' 'unsafe-inline'" in csp
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "no-referrer"

        with urllib.request.urlopen(server.url, timeout=30) as response:
            assert "default-src 'none'" in response.headers["Content-Security-Policy"]
            assert response.headers["X-Content-Type-Options"] == "nosniff"
            assert response.headers["X-Frame-Options"] == "DENY"
            assert response.headers["Referrer-Policy"] == "no-referrer"
    finally:
        server.shutdown()


def test_browser_file_upload_rejects_requests_larger_than_limit(monkeypatch) -> None:
    controller = ProjectController()
    monkeypatch.setattr(browser_server_module, "MAX_BROWSER_UPLOAD_BYTES", 256)
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_multipart(f"{server.url}api/files/primary", "file", "Stage1.MP4", b"x" * 1024)

        assert exc_info.value.code == 400
        payload = json.loads(exc_info.value.read().decode("utf-8"))
        assert "Browser upload exceeds the" in payload["error"]
        assert controller.project.primary_video.path == ""
    finally:
        server.shutdown()


def test_browser_overlay_api_supports_repeatable_text_boxes() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/overlay",
            {
                "timer_lock_to_stack": False,
                "draw_lock_to_stack": True,
                "score_lock_to_stack": False,
                "timer_x": 0.21,
                "timer_y": 0.32,
                "score_x": 0.74,
                "score_y": 0.18,
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
                        "lock_to_stack": True,
                        "source": "manual",
                        "text": "Session summary",
                        "quadrant": "top_left",
                        "background_color": "#101010",
                        "text_color": "#ffffff",
                        "opacity": 0.8,
                        "width": 200,
                        "height": 60,
                    },
                    {
                        "id": "summary-box",
                        "enabled": True,
                        "source": "imported_summary",
                        "text": "",
                        "quadrant": "above_final",
                        "background_color": "#ff7b22",
                        "text_color": "#ffffff",
                        "opacity": 0.9,
                        "width": 0,
                        "height": 0,
                    },
                    {
                        "id": "imported-box",
                        "enabled": True,
                        "source": "imported_summary",
                        "text": "",
                        "quadrant": "custom",
                        "x": 0.5,
                        "y": 0.4,
                        "background_color": "#000000",
                        "text_color": "#f8fafc",
                        "opacity": 0.9,
                        "width": 180,
                        "height": 48,
                    },
                ],
            },
        )

        boxes = state["project"]["overlay"]["text_boxes"]
        assert len(boxes) == 3
        assert boxes[0]["text"] == "Session summary"
        assert boxes[0]["lock_to_stack"] is True
        assert boxes[0]["quadrant"] == "top_left"
        assert boxes[1]["source"] == "imported_summary"
        assert boxes[1]["quadrant"] == "above_final"
        assert boxes[2]["source"] == "imported_summary"
        assert boxes[2]["quadrant"] == "custom"
        assert boxes[2]["x"] == pytest.approx(0.5)
        assert boxes[2]["y"] == pytest.approx(0.4)
        assert state["project"]["overlay"]["timer_lock_to_stack"] is False
        assert state["project"]["overlay"]["draw_lock_to_stack"] is True
        assert state["project"]["overlay"]["score_lock_to_stack"] is False
        assert state["project"]["overlay"]["timer_x"] == pytest.approx(0.21)
        assert state["project"]["overlay"]["timer_y"] == pytest.approx(0.32)
        assert state["project"]["overlay"]["score_x"] == pytest.approx(0.74)
        assert state["project"]["overlay"]["score_y"] == pytest.approx(0.18)
        assert state["project"]["overlay"]["custom_box_mode"] == "imported_summary"
    finally:
        server.shutdown()


def test_browser_state_exposes_metrics_after_primary_ingest(synthetic_video_factory) -> None:
    controller = ProjectController()
    video_path = synthetic_video_factory()

    controller.ingest_primary_video(str(video_path))
    payload = browser_state(controller.project, controller.status_message)

    assert payload["metrics"]["total_shots"] == 3
    assert payload["metrics"]["draw_ms"] is not None
    assert payload["metrics"]["raw_time_ms"] == payload["metrics"]["stage_time_ms"]
    assert payload["media"]["primary_url"] == "/media/primary"
    assert payload["media"]["cache_token"] == ""
    assert len(payload["split_rows"]) == 3
    assert len(payload["timing_segments"]) == 3
    assert payload["split_rows"][0]["split_ms"] == payload["metrics"]["draw_ms"]
    assert payload["split_rows"][0]["row_type"] == "shot"
    assert payload["split_rows"][0]["label"] == "Shot 1"
    assert payload["split_rows"][0]["interval_label"] == "Draw"
    assert payload["split_rows"][0]["sequence_total_ms"] == payload["metrics"]["draw_ms"]
    assert payload["split_rows"][1]["split_ms"] is not None
    assert payload["timing_segments"][0]["label"] == "Shot 1"
    assert payload["timing_segments"][0]["interval_label"] == "Draw"
    assert payload["timing_segments"][0]["segment_ms"] == payload["metrics"]["draw_ms"]
    assert payload["timing_segments"][0]["sequence_total_ms"] == payload["metrics"]["draw_ms"]
    assert payload["timing_segments"][-1]["cumulative_ms"] == payload["metrics"]["raw_time_ms"]


def test_browser_control_api_imports_and_edits_video(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        state = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        assert state["metrics"]["total_shots"] == 3

        first_shot_id = state["project"]["analysis"]["shots"][0]["id"]
        state = _post_json(
            f"{server.url}api/shots/move",
            {"shot_id": first_shot_id, "time_ms": 830},
        )
        assert state["project"]["analysis"]["shots"][0]["time_ms"] == 830

        state = _post_json(
            f"{server.url}api/scoring/score",
            {"shot_id": first_shot_id, "letter": "C", "penalty_counts": {"procedural_errors": 1}},
        )
        assert state["project"]["analysis"]["shots"][0]["score"]["letter"] == "C"
        assert state["project"]["analysis"]["shots"][0]["score"]["penalty_counts"] == {"procedural_errors": 1}

        state = _get_json(f"{server.url}api/state")
        assert state["metrics"]["total_shots"] == 3
    finally:
        server.shutdown()


def test_browser_control_api_restores_original_split_and_score(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        state = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})

        first_shot = state["project"]["analysis"]["shots"][0]
        shot_id = first_shot["id"]
        original_time_ms = first_shot["time_ms"]
        original_source = first_shot["source"]

        state = _post_json(
            f"{server.url}api/shots/move",
            {"shot_id": shot_id, "time_ms": original_time_ms + 250},
        )
        moved_shot = next(shot for shot in state["project"]["analysis"]["shots"] if shot["id"] == shot_id)
        assert moved_shot["source"] == "manual"
        assert moved_shot["confidence"] is None

        state = _post_json(
            f"{server.url}api/scoring/score",
            {"shot_id": shot_id, "letter": "C", "penalty_counts": {"procedural_errors": 1}},
        )
        scored_shot = next(shot for shot in state["project"]["analysis"]["shots"] if shot["id"] == shot_id)
        assert scored_shot["score"]["letter"] == "C"

        state = _post_json(f"{server.url}api/shots/restore", {"shot_id": shot_id})
        restored_timing = next(shot for shot in state["project"]["analysis"]["shots"] if shot["id"] == shot_id)
        assert restored_timing["time_ms"] == original_time_ms
        assert restored_timing["source"] == original_source

        state = _post_json(f"{server.url}api/scoring/restore", {"shot_id": shot_id})
        restored_score = next(shot for shot in state["project"]["analysis"]["shots"] if shot["id"] == shot_id)
        assert restored_score["score"]["letter"] == "A"
    finally:
        server.shutdown()


def test_browser_export_route_syncs_scoring_overlay_and_merge_payloads_before_render(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        primary_path = Path(synthetic_video_factory(name="export-sync-primary"))
        merge_path = Path(synthetic_video_factory(name="export-sync-merge", beep_ms=650))

        _post_json(f"{server.url}api/import/primary", {"path": str(primary_path)})
        state = _post_json(f"{server.url}api/import/merge", {"path": str(merge_path)})
        merge_source_id = state["project"]["merge_sources"][0]["id"]
        output_path = tmp_path / "browser-export-sync.mp4"

        def fake_export_project(project, output_target, progress_callback=None, log_callback=None):
            assert project.scoring.enabled is True
            assert project.scoring.ruleset == "uspsa_major"
            assert project.overlay.position == OverlayPosition.TOP
            assert project.overlay.custom_box_enabled is True
            assert project.overlay.custom_box_text == "Session summary"
            assert project.overlay.custom_box_width == 160
            assert project.overlay.custom_box_height == 48
            assert project.overlay.show_timer is False
            assert project.merge.enabled is True
            assert project.merge.layout.value == "pip"
            assert project.merge.pip_size_percent == 44
            assert len(project.merge_sources) == 1
            assert project.merge_sources[0].pip_size_percent == 44
            assert project.merge_sources[0].pip_x == pytest.approx(0.12)
            assert project.merge_sources[0].pip_y == pytest.approx(0.76)
            assert project.merge_sources[0].sync_offset_ms == -25
            assert project.analysis.sync_offset_ms == -25
            export_target = Path(output_target)
            export_target.write_bytes(b"ok")
            return export_target

        monkeypatch.setattr(browser_server_module, "export_project", fake_export_project)

        state = _post_json(
            f"{server.url}api/export",
            {
                "path": str(output_path),
                "preset": "custom",
                "quality": "high",
                "aspect_ratio": "original",
                "scoring": {
                    "ruleset": "uspsa_major",
                    "enabled": True,
                    "penalties": 0,
                    "penalty_counts": {},
                },
                "overlay": {
                    "position": "top",
                    "show_timer": False,
                    "show_draw": False,
                    "show_shots": True,
                    "show_score": False,
                    "custom_box_enabled": True,
                    "custom_box_text": "Session summary",
                    "custom_box_width": 160,
                    "custom_box_height": 48,
                },
                "merge": {
                    "enabled": True,
                    "layout": "pip",
                    "pip_size_percent": 44,
                    "pip_x": 0.12,
                    "pip_y": 0.76,
                    "sources": [
                        {
                            "source_id": merge_source_id,
                            "pip_size_percent": 44,
                            "pip_x": 0.12,
                            "pip_y": 0.76,
                            "sync_offset_ms": -25,
                        }
                    ],
                },
            },
        )

        assert output_path.exists()
        assert state["project"]["overlay"]["position"] == "top"
        assert state["project"]["scoring"]["ruleset"] == "uspsa_major"
        assert state["project"]["overlay"]["custom_box_text"] == "Session summary"
        assert state["project"]["overlay"]["custom_box_width"] == 160
        assert state["project"]["overlay"]["custom_box_height"] == 48
        assert state["project"]["merge"]["pip_size_percent"] == 44
        assert state["project"]["merge_sources"][0]["pip_size_percent"] == 44
        assert state["project"]["merge_sources"][0]["sync_offset_ms"] == -25
        assert state["project"]["analysis"]["sync_offset_ms"] == -25
    finally:
        server.shutdown()


def test_browser_primary_replacement_preserves_reusable_settings_and_clears_video_state(
    synthetic_video_factory,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        first_primary = Path(synthetic_video_factory(name="primary-one", beep_ms=400))
        second_primary = Path(synthetic_video_factory(name="primary-two", beep_ms=520))
        secondary = Path(synthetic_video_factory(name="secondary-angle", beep_ms=680))

        state = _post_json(f"{server.url}api/import/primary", {"path": str(first_primary)})
        first_shot_id = state["project"]["analysis"]["shots"][0]["id"]

        _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "custom_box_enabled": True,
                "custom_box_text": "Classifier ready",
                "custom_box_x": 0.45,
                "custom_box_y": 0.55,
            },
        )
        _post_json(f"{server.url}api/export/preset", {"preset": "universal_vertical"})
        _post_json(
            f"{server.url}api/export/settings",
            {"video_bitrate_mbps": 18, "two_pass": True},
        )
        _post_json(f"{server.url}api/scoring/profile", {"ruleset": "uspsa_major"})
        _post_json(
            f"{server.url}api/scoring",
            {"enabled": True, "penalties": 1.5, "penalty_counts": {"procedural_errors": 2}},
        )
        _post_json(
            f"{server.url}api/events/add",
            {"kind": "reload", "after_shot_id": first_shot_id, "note": "Old review note"},
        )
        _post_json(f"{server.url}api/shots/select", {"shot_id": first_shot_id})
        _post_json(f"{server.url}api/import/secondary", {"path": str(secondary)})
        _post_json(
            f"{server.url}api/merge",
            {"layout": "pip", "pip_size_percent": 50, "pip_x": 0.2, "pip_y": 0.8},
        )
        controller.project.export.output_path = "/tmp/browser-template-export.mp4"
        controller.project.export.last_log = "previous export log"
        controller.project.export.last_error = "previous export error"
        controller.project.ui_state.timeline_offset_ms = 999

        state = _post_json(f"{server.url}api/import/primary", {"path": str(second_primary)})

        assert state["project"]["primary_video"]["path"] == str(second_primary)
        assert state["project"]["analysis"]["beep_time_ms_secondary"] is None
        assert state["project"]["analysis"]["sync_offset_ms"] == 0
        assert state["project"]["analysis"]["events"] == []
        assert len(state["project"]["analysis"]["shots"]) == 3
        assert all(shot["score"]["letter"] == "A" for shot in state["project"]["analysis"]["shots"])
        assert state["project"]["overlay"]["position"] == "top"
        assert state["project"]["overlay"]["custom_box_enabled"] is True
        assert state["project"]["overlay"]["custom_box_text"] == ""
        assert state["project"]["overlay"]["custom_box_x"] == 0.45
        assert state["project"]["overlay"]["custom_box_y"] == 0.55
        assert state["project"]["scoring"]["enabled"] is True
        assert state["project"]["scoring"]["ruleset"] == "uspsa_major"
        assert state["project"]["scoring"]["penalties"] == 0.0
        assert state["project"]["scoring"]["penalty_counts"] == {}
        assert state["project"]["scoring"]["hit_factor"] > 0.0
        assert state["project"]["secondary_video"] is None
        assert state["project"]["merge_sources"] == []
        assert state["project"]["merge"]["enabled"] is False
        assert state["project"]["merge"]["layout"] == "side_by_side"
        assert state["project"]["merge"]["pip_size_percent"] == 35
        assert state["project"]["merge"]["pip_x"] == 1.0
        assert state["project"]["merge"]["pip_y"] == 1.0
        assert state["project"]["export"]["target_width"] == 1080
        assert state["project"]["export"]["target_height"] == 1920
        assert state["project"]["export"]["video_bitrate_mbps"] == 18.0
        assert state["project"]["export"]["two_pass"] is True
        assert state["project"]["export"]["output_path"] == "/tmp/browser-template-export.mp4"
        assert state["project"]["export"]["last_log"] == ""
        assert state["project"]["export"]["last_error"] is None
        assert state["project"]["ui_state"]["selected_shot_id"] is None
        assert state["project"]["ui_state"]["timeline_offset_ms"] == 0
    finally:
        server.shutdown()


def test_browser_control_api_imports_practiscore_results() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = EXAMPLES_DIR / "USPSA"
    try:
        server.start_background(open_browser=False)

        state = _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "uspsa",
                "stage_number": 1,
                "competitor_name": "Lutman, Stephen",
                "competitor_place": 1,
            },
        )

        assert state["project"]["overlay"]["custom_box_enabled"] is False
        assert state["project"]["overlay"]["custom_box_mode"] == "manual"

        state = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "report.txt",
            (examples_dir / "report.txt").read_bytes(),
        )

        assert state["project"]["scoring"]["enabled"] is True
        assert state["project"]["scoring"]["ruleset"] == "uspsa_minor"
        assert state["project"]["scoring"]["match_type"] == "uspsa"
        assert state["project"]["scoring"]["stage_number"] == 1
        assert state["project"]["scoring"]["competitor_name"] == "Stephen Lutman"
        assert state["project"]["scoring"]["competitor_place"] == 1
        assert state["project"]["scoring"]["imported_stage"]["source_name"] == "report.txt"
        assert state["project"]["scoring"]["imported_stage"]["stage_name"] == "Stage 1 Swangin’"
        assert state["project"]["scoring"]["imported_stage"]["aggregate_points"] == 101.0
        assert state["practiscore_options"]["source_name"] == "report.txt"
        assert state["practiscore_options"]["detected_match_type"] == "uspsa"
        assert state["practiscore_options"]["stage_numbers"] == [1, 2, 3, 4, 5, 6]
        assert any(
            option == {"name": "Stephen Lutman", "place": 1}
            for option in state["practiscore_options"]["competitors"]
        )
        assert state["project"]["overlay"]["custom_box_enabled"] is True
        assert state["project"]["overlay"]["custom_box_mode"] == "imported_summary"
        assert state["scoring_summary"]["imported_overlay_text"] == "Imported\nRaw 23.24\nPoints 101\nHF 4.3460"
        assert state["scoring_summary"]["hit_factor"] == pytest.approx(101.0 / 23.24)
        assert state["scoring_summary"]["display_value"] == "4.35"
    finally:
        server.shutdown()


def test_browser_control_api_infers_practiscore_results_without_manual_context() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = EXAMPLES_DIR / "USPSA"
    try:
        server.start_background(open_browser=False)

        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 4,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )
        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "",
                "stage_number": "",
                "competitor_name": "",
                "competitor_place": "",
            },
        )

        state = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "report.txt",
            (examples_dir / "report.txt").read_bytes(),
        )

        assert state["project"]["scoring"]["enabled"] is True
        assert state["project"]["scoring"]["ruleset"] == "uspsa_minor"
        assert state["project"]["scoring"]["match_type"] == "uspsa"
        assert state["project"]["scoring"]["stage_number"] == 1
        assert state["project"]["scoring"]["competitor_name"] == "Ben Rice"
        assert state["project"]["scoring"]["competitor_place"] == 1
        assert state["project"]["scoring"]["imported_stage"]["source_name"] == "report.txt"
        assert state["project"]["scoring"]["imported_stage"]["competitor_name"] == "Ben Rice"
        assert state["project"]["scoring"]["imported_stage"]["stage_name"] == "Stage 1 Swangin’"
        assert state["practiscore_options"]["source_name"] == "report.txt"
        assert state["practiscore_options"]["detected_match_type"] == "uspsa"
        assert state["project"]["overlay"]["custom_box_enabled"] is True
        assert state["project"]["overlay"]["custom_box_mode"] == "imported_summary"
    finally:
        server.shutdown()


def test_browser_control_reimports_practiscore_from_staged_file_when_context_changes() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = EXAMPLES_DIR / "IDPA"
    try:
        server.start_background(open_browser=False)

        state = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "IDPA.csv",
            (examples_dir / "IDPA.csv").read_bytes(),
        )

        assert state["project"]["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert state["practiscore_options"]["source_name"] == "IDPA.csv"
        assert state["practiscore_options"]["stage_numbers"] == [1, 2, 3, 4]

        state = _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 2,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )

        assert state["project"]["scoring"]["match_type"] == "idpa"
        assert state["project"]["scoring"]["stage_number"] == 2
        assert state["project"]["scoring"]["competitor_name"] == "John Klockenkemper"
        assert state["project"]["scoring"]["competitor_place"] == 4
        assert state["project"]["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert state["project"]["scoring"]["imported_stage"]["stage_number"] == 2
        assert state["project"]["scoring"]["imported_stage"]["competitor_name"] == "John Klockenkemper"
        assert state["project"]["scoring"]["imported_stage"]["competitor_place"] == 4
    finally:
        server.shutdown()


def test_browser_control_loading_new_practiscore_csv_keeps_current_selection(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = EXAMPLES_DIR / "IDPA"
    try:
        server.start_background(open_browser=False)

        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 2,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )
        _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "old-results.csv",
            (examples_dir / "IDPA.csv").read_bytes(),
        )

        state = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "thursday-night.csv",
            _changed_place_idpa_results(tmp_path).read_bytes(),
        )

        assert state["practiscore_options"]["source_name"] == "thursday-night.csv"
        assert state["practiscore_options"]["detected_match_type"] == "idpa"
        assert state["project"]["scoring"]["match_type"] == "idpa"
        assert state["project"]["scoring"]["stage_number"] == 2
        assert state["project"]["scoring"]["competitor_name"] == "John Klockenkemper"
        assert state["project"]["scoring"]["competitor_place"] == 6
        assert state["project"]["scoring"]["imported_stage"]["source_name"] == "thursday-night.csv"
        assert state["project"]["scoring"]["imported_stage"]["final_time"] == 20.57
        assert state["project"]["overlay"]["custom_box_mode"] == "imported_summary"
        imported_box = next(box for box in state["project"]["overlay"]["text_boxes"] if box["source"] == "imported_summary")
        assert imported_box["quadrant"] == "above_final"
        assert imported_box["x"] is None
        assert imported_box["y"] is None
        assert imported_box["width"] == 0
        assert imported_box["height"] == 0
        assert state["scoring_summary"]["display_label"] == "Final"
        assert state["scoring_summary"]["display_value"] == "20.57"
    finally:
        server.shutdown()


def test_browser_project_open_restores_practiscore_state(tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = EXAMPLES_DIR / "IDPA"
    server.start_background(open_browser=False)
    try:
        project_path = tmp_path / "practiscore-reopen.ssproj"

        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 2,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )
        imported = _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "IDPA.csv",
            (examples_dir / "IDPA.csv").read_bytes(),
        )

        assert imported["project"]["scoring"]["imported_stage"]["competitor_name"] == "John Klockenkemper"
        assert imported["project"]["scoring"]["imported_stage"]["stage_number"] == 2

        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})
        assert Path(saved["project"]["scoring"]["practiscore_source_path"]).parent == project_path / "CSV"

        _post_json(f"{server.url}api/project/new", {})

        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        assert reopened["project"]["path"] == str(project_path)
        assert reopened["project"]["scoring"]["match_type"] == "idpa"
        assert reopened["project"]["scoring"]["stage_number"] == 2
        assert reopened["project"]["scoring"]["competitor_name"] == "John Klockenkemper"
        assert reopened["project"]["scoring"]["competitor_place"] == 4
        assert reopened["project"]["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert reopened["project"]["scoring"]["imported_stage"]["stage_number"] == 2
        assert reopened["project"]["scoring"]["imported_stage"]["competitor_name"] == "John Klockenkemper"
        assert reopened["project"]["scoring"]["imported_stage"]["final_time"] == 29.83
        assert reopened["practiscore_options"]["has_source"] is True
        assert reopened["practiscore_options"]["source_name"] == "IDPA.csv"
        assert reopened["practiscore_options"]["detected_match_type"] == "idpa"
        assert reopened["practiscore_options"]["stage_numbers"] == [1, 2, 3, 4]
        assert reopened["scoring_summary"]["imported_stage"]["competitor_name"] == "John Klockenkemper"
        assert reopened["scoring_summary"]["display_value"] == "29.83"
    finally:
        server.shutdown()


def test_browser_control_api_can_delete_timing_event() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    try:
        server.start_background(open_browser=False)

        state = _post_json(
            f"{server.url}api/events/add",
            {"kind": "reload", "note": "Cleanup"},
        )
        event_id = state["project"]["analysis"]["events"][0]["id"]

        state = _post_json(
            f"{server.url}api/events/delete",
            {"event_id": event_id},
        )

        assert state["project"]["analysis"]["events"] == []
    finally:
        server.shutdown()


def test_browser_control_api_covers_remaining_browser_routes(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        primary_path = Path(synthetic_video_factory(name="primary-route-cover"))
        merge_path = Path(synthetic_video_factory(name="merge-route-cover", beep_ms=620))

        state = _post_json(f"{server.url}api/import/primary", {"path": str(primary_path)})
        assert state["project"]["primary_video"]["path"] == str(primary_path)

        state = _get_json(f"{server.url}api/state")
        assert state["metrics"]["total_shots"] == 3
        first_shot_id = state["project"]["analysis"]["shots"][0]["id"]
        shot_count = len(state["project"]["analysis"]["shots"])

        state = _post_json(f"{server.url}api/analysis/threshold", {"threshold": 0.4})
        assert state["project"]["analysis"]["detection_threshold"] == 0.4

        state = _post_json(f"{server.url}api/beep", {"time_ms": 405})
        assert state["project"]["analysis"]["beep_time_ms_primary"] == 405

        state = _post_json(f"{server.url}api/shots/add", {"time_ms": 1750})
        assert len(state["project"]["analysis"]["shots"]) == shot_count + 1
        first_shot_id = state["project"]["analysis"]["shots"][0]["id"]
        added_shot_id = next(
            shot["id"]
            for shot in state["project"]["analysis"]["shots"]
            if shot["time_ms"] == 1750
        )

        state = _post_json(f"{server.url}api/shots/select", {"shot_id": first_shot_id})
        assert state["project"]["ui_state"]["selected_shot_id"] == first_shot_id

        state = _post_json(f"{server.url}api/shots/delete", {"shot_id": added_shot_id})
        assert len(state["project"]["analysis"]["shots"]) == shot_count
        assert all(shot["id"] != added_shot_id for shot in state["project"]["analysis"]["shots"])

        state = _post_json(f"{server.url}api/import/merge", {"path": str(merge_path)})
        assert len(state["project"]["merge_sources"]) == 1
        merge_source_id = state["project"]["merge_sources"][0]["id"]
        assert state["project"]["secondary_video"]["path"] == str(merge_path)

        state = _post_json(f"{server.url}api/merge/remove", {"source_id": merge_source_id})
        assert state["project"]["merge_sources"] == []
        assert state["project"]["secondary_video"] is None

        state = _post_json(
            f"{server.url}api/export/settings",
            {"quality": "medium", "target_width": 720, "target_height": 1280, "aspect_ratio": "9:16"},
        )
        assert state["project"]["export"]["preset"] == "custom"
        assert state["project"]["export"]["quality"] == "medium"
        assert state["project"]["export"]["target_width"] == 720
        assert state["project"]["export"]["target_height"] == 1280
        assert state["project"]["export"]["aspect_ratio"] == "9:16"

        bundle_path = tmp_path / "delete-me.ssproj"
        _post_json(f"{server.url}api/project/details", {"name": "Delete Me"})
        state = _post_json(f"{server.url}api/project/save", {"path": str(bundle_path)})
        assert bundle_path.exists()
        assert state["project"]["name"] == "Delete Me"

        state = _post_json(f"{server.url}api/project/delete", {})
        assert not bundle_path.exists()
        assert state["project"]["name"] == "Untitled Project"
        assert state["status"] == "Deleted the saved project folder."
    finally:
        server.shutdown()


def test_browser_threshold_rerun_preserves_manual_shots_and_timing_events(monkeypatch) -> None:
    controller = ProjectController()
    controller.project.primary_video = VideoAsset(path="/tmp/primary.mp4", duration_ms=2000, width=640, height=360, fps=30.0)
    first = ShotEvent(time_ms=250, source=ShotSource.AUTO, confidence=0.9)
    second = ShotEvent(time_ms=500, source=ShotSource.AUTO, confidence=0.9)
    third = ShotEvent(time_ms=900, source=ShotSource.AUTO, confidence=0.9)
    controller.project.analysis.beep_time_ms_primary = 100
    controller.project.analysis.shots = [first, second, third]
    controller.add_timing_event("reload", after_shot_id=first.id, before_shot_id=second.id, note="Keep me")
    controller.add_shot(1200)

    def fake_analyze(path: str, threshold: float) -> DetectionResult:
        return DetectionResult(
            beep_time_ms=105,
            shots=[
                ShotEvent(time_ms=260, source=ShotSource.AUTO, confidence=0.95),
                ShotEvent(time_ms=515, source=ShotSource.AUTO, confidence=0.95),
                ShotEvent(time_ms=880, source=ShotSource.AUTO, confidence=0.95),
            ],
            waveform=[0.2],
            sample_rate=22050,
        )

    monkeypatch.setattr(controller_module, "analyze_video_audio", fake_analyze)

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(f"{server.url}api/analysis/threshold", {"threshold": 0.55})

        assert any(
            shot["source"] == "manual" and shot["time_ms"] == 1200
            for shot in state["project"]["analysis"]["shots"]
        )
        assert len(state["project"]["analysis"]["events"]) == 1
        assert state["project"]["analysis"]["events"][0]["note"] == "Keep me"
        assert state["split_rows"][1]["interval_label"] == "Reload"
    finally:
        server.shutdown()


def test_browser_file_picker_endpoint_imports_selected_primary_video(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        state = _post_multipart(
            f"{server.url}api/files/primary",
            "file",
            video_path.name,
            video_path.read_bytes(),
        )

        assert state["metrics"]["total_shots"] == 3
        assert state["media"]["primary_available"] is True
        assert state["media"]["primary_display_name"] == video_path.name
        assert video_path.name in state["media"]["primary_display_name"]
        assert "splitshot-browser-" not in state["media"]["primary_display_name"]
        assert state["project"]["primary_video"]["path"] != str(video_path)
        assert Path(state["project"]["primary_video"]["path"]).exists()
    finally:
        server.shutdown()


def test_browser_file_picker_import_preserves_trailing_bytes(monkeypatch) -> None:
    controller = ProjectController()
    captured: dict[str, bytes] = {}

    def fake_ingest(path: str, source_name: str | None = None) -> None:
        captured["bytes"] = Path(path).read_bytes()
        controller.status_message = "Imported primary video."

    monkeypatch.setattr(controller, "ingest_primary_video", fake_ingest)
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        payload = b"splitshot-binary-payload--"
        _post_multipart(
            f"{server.url}api/files/primary",
            "file",
            "stage.mp4",
            payload,
        )

        assert captured["bytes"] == payload
    finally:
        server.shutdown()


def test_browser_file_picker_endpoint_preserves_secondary_display_name(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        primary_path = Path(synthetic_video_factory(name="primary"))
        secondary_path = Path(synthetic_video_factory(name="secondary"))

        _post_multipart(
            f"{server.url}api/files/primary",
            "file",
            primary_path.name,
            primary_path.read_bytes(),
        )
        state = _post_multipart(
            f"{server.url}api/files/secondary",
            "file",
            secondary_path.name,
            secondary_path.read_bytes(),
        )

        assert state["media"]["secondary_display_name"] == secondary_path.name
        assert state["project"]["secondary_video"]["path"] != str(secondary_path)
        assert Path(state["project"]["secondary_video"]["path"]).exists()
    finally:
        server.shutdown()


def test_browser_path_dialog_endpoint_uses_local_path_chooser(tmp_path) -> None:
    selected = tmp_path / "review.mp4"
    calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        calls.append((kind, current))
        return str(selected)

    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, path_chooser=fake_path_chooser)
    server.start_background(open_browser=False)
    try:
        payload = _post_json(
            f"{server.url}api/dialog/path",
            {"kind": "export", "current": "/tmp/current.mp4"},
        )

        assert payload == {"path": str(selected)}
        assert calls == [("export", "/tmp/current.mp4")]
        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "api.dialog.path.start" in log_text
        assert "api.dialog.path.success" in log_text
    finally:
        server.shutdown()


def test_browser_path_dialog_endpoint_supports_video_path_fields(tmp_path) -> None:
    selected = tmp_path / "stage.mp4"
    calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        calls.append((kind, current))
        return str(selected)

    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, path_chooser=fake_path_chooser)
    server.start_background(open_browser=False)
    try:
        payload = _post_json(
            f"{server.url}api/dialog/path",
            {"kind": "primary", "current": "/tmp/current-stage.mp4"},
        )

        assert payload == {"path": str(selected)}
        assert calls == [("primary", "/tmp/current-stage.mp4")]
    finally:
        server.shutdown()


def test_browser_path_dialog_endpoint_supports_project_folder_selection(tmp_path) -> None:
    project_path = tmp_path / "existing-project"
    calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        calls.append((kind, current))
        return str(project_path)

    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, path_chooser=fake_path_chooser)
    server.start_background(open_browser=False)
    try:
        assert _post_json(
            f"{server.url}api/dialog/path",
            {"kind": "project_folder", "current": "/tmp/current.ssproj"},
        ) == {"path": str(project_path)}
        assert calls == [("project_folder", "/tmp/current.ssproj")]
    finally:
        server.shutdown()


def test_browser_project_probe_reports_project_metadata_state(tmp_path) -> None:
    project_path = tmp_path / "probe-project"
    project_path.mkdir()

    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        assert _post_json(
            f"{server.url}api/project/probe",
            {"path": str(project_path)},
        ) == {"path": str(project_path), "has_project_file": False}

        (project_path / "project.json").write_text("{}", encoding="utf-8")

        assert _post_json(
            f"{server.url}api/project/probe",
            {"path": str(project_path)},
        ) == {"path": str(project_path), "has_project_file": True}
    finally:
        server.shutdown()


def test_choose_local_path_macos_prompts_for_project_folder(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        captured["script"] = command[2]

        class Result:
            returncode = 0
            stdout = "/Users/klock/splitshot/review.ssproj\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(browser_server_module.subprocess, "run", fake_run)

    chosen = browser_server_module.choose_local_path_macos("project_folder")

    assert chosen == "/Users/klock/splitshot/review.ssproj"
    assert captured["command"] == ["osascript", "-e", captured["script"]]
    script = str(captured["script"])
    assert "choose folder with prompt" in script
    assert "Choose SplitShot project folder" in script


def test_choose_local_path_macos_falls_back_to_existing_parent_for_missing_media_path(monkeypatch, tmp_path: Path) -> None:
    captured: dict[str, object] = {}
    missing_media_path = tmp_path / "Stage2.MP4"

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        captured["script"] = command[2]

        class Result:
            returncode = 0
            stdout = f"{tmp_path / 'picked.mp4'}\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(browser_server_module.subprocess, "run", fake_run)

    chosen = browser_server_module.choose_local_path_macos("secondary", str(missing_media_path))

    assert chosen == str(tmp_path / "picked.mp4")
    script = str(captured["script"])
    assert "choose file with prompt" in script
    assert "Choose secondary angle video" in script
    assert str(tmp_path) in script


def test_browser_control_api_layout_route_is_not_available(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        with pytest.raises(urllib.error.HTTPError) as error_info:
            _post_json(
                f"{server.url}api/layout",
                {"quality": "medium", "aspect_ratio": "9:16"},
            )

        assert error_info.value.code == 404
    finally:
        server.shutdown()


def test_browser_project_open_replaces_stale_media_state(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        project_path = tmp_path / "saved.ssproj"

        imported = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        assert imported["media"]["primary_available"] is True

        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})
        assert saved["project"]["path"] == str(project_path)

        cleared = _post_json(f"{server.url}api/project/new", {})
        assert cleared["media"]["primary_available"] is False
        assert cleared["media"]["primary_display_name"] == "No Video Selected"

        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        assert reopened["project"]["path"] == str(project_path)
        assert reopened["media"]["primary_available"] is True
        assert Path(reopened["project"]["primary_video"]["path"]).parent == project_path / "Input"
        assert controller.project_path == project_path
    finally:
        server.shutdown()


def test_browser_project_open_recovers_renamed_project_root_media(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory(name="Stage2"))

        _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        _post_json(f"{server.url}api/project/save", {"path": str(tmp_path)})

        saved_primary = Path(controller.project.primary_video.path)
        assert saved_primary.parent == tmp_path
        renamed_primary = saved_primary.with_name("Stage02.MP4")
        saved_primary.rename(renamed_primary)

        _post_json(f"{server.url}api/project/new", {})
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(tmp_path)})

        assert reopened["project"]["path"] == str(tmp_path)
        assert reopened["media"]["primary_available"] is True
        assert Path(reopened["project"]["primary_video"]["path"]) == renamed_primary.resolve()
        assert "restored renamed project media" in reopened["status"].lower()
    finally:
        server.shutdown()


def test_browser_project_open_restores_ui_state_and_export_output_path(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        project_path = tmp_path / "restore-ui-state.ssproj"
        output_path = project_path / "Output" / "custom-output.mp4"

        imported = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        selected_shot_id = imported["project"]["analysis"]["shots"][0]["id"]
        original_preset = imported["project"]["export"]["preset"]

        _post_json(f"{server.url}api/shots/select", {"shot_id": selected_shot_id})
        ui_state = _post_json(
            f"{server.url}api/project/ui-state",
            {
                "selected_shot_id": selected_shot_id,
                "timeline_zoom": 9.5,
                "timeline_offset_ms": 420,
                "active_tool": "timing",
                "waveform_mode": "add",
                "waveform_expanded": False,
                "timing_expanded": True,
                "layout_locked": False,
                "rail_width": 70,
                "inspector_width": 512,
                "waveform_height": 260,
                "scoring_shot_expansion": {selected_shot_id: True},
                "waveform_shot_amplitudes": {selected_shot_id: 1.5},
                "timing_edit_shot_ids": [selected_shot_id],
                "timing_column_widths": {"segment": 128, "split": 224, "action": 244},
            },
        )
        assert ui_state["project"]["ui_state"]["active_tool"] == "timing"
        assert ui_state["project"]["ui_state"]["timing_expanded"] is True

        export_state = _post_json(
            f"{server.url}api/export/settings",
            {"output_path": str(output_path)},
        )
        assert export_state["project"]["export"]["output_path"] == str(output_path)
        assert export_state["project"]["export"]["preset"] == original_preset

        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})
        assert saved["project"]["path"] == str(project_path)

        _post_json(f"{server.url}api/project/new", {})
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        assert reopened["project"]["path"] == str(project_path)
        assert reopened["project"]["ui_state"]["selected_shot_id"] == selected_shot_id
        assert reopened["project"]["ui_state"]["timeline_zoom"] == pytest.approx(9.5)
        assert reopened["project"]["ui_state"]["timeline_offset_ms"] == 420
        assert reopened["project"]["ui_state"]["active_tool"] == "timing"
        assert reopened["project"]["ui_state"]["waveform_mode"] == "add"
        assert reopened["project"]["ui_state"]["waveform_expanded"] is False
        assert reopened["project"]["ui_state"]["timing_expanded"] is True
        assert reopened["project"]["ui_state"]["layout_locked"] is False
        assert reopened["project"]["ui_state"]["rail_width"] == 70
        assert reopened["project"]["ui_state"]["inspector_width"] == 512
        assert reopened["project"]["ui_state"]["waveform_height"] == 260
        assert reopened["project"]["ui_state"]["scoring_shot_expansion"] == {selected_shot_id: True}
        assert reopened["project"]["ui_state"]["waveform_shot_amplitudes"] == {selected_shot_id: 1.5}
        assert reopened["project"]["ui_state"]["timing_edit_shot_ids"] == [selected_shot_id]
        assert reopened["project"]["ui_state"]["timing_column_widths"]["segment"] == 128
        assert reopened["project"]["ui_state"]["timing_column_widths"]["split"] == 224
        assert reopened["project"]["ui_state"]["timing_column_widths"]["action"] == 244
        assert reopened["project"]["export"]["output_path"] == str(output_path)
        assert reopened["project"]["export"]["preset"] == original_preset
    finally:
        server.shutdown()


def test_browser_project_details_autosave_persists_after_reopen(tmp_path: Path) -> None:
    project_path = tmp_path / "metadata-autosave.ssproj"
    bootstrap = ProjectController()
    bootstrap.save_project(str(project_path))

    first_server = BrowserControlServer(controller=ProjectController(), port=0)
    first_server.start_background(open_browser=False)
    try:
        opened = _post_json(f"{first_server.url}api/project/open", {"path": str(project_path)})
        assert opened["project"]["name"] == "Untitled Project"
        assert opened["project"]["description"] == ""

        updated = _post_json(
            f"{first_server.url}api/project/details",
            {"name": "Test Project", "description": "Test Description"},
        )

        assert updated["project"]["name"] == "Test Project"
        assert updated["project"]["description"] == "Test Description"
        assert updated["status"] == "Updated project details."

        unchanged = _post_json(
            f"{first_server.url}api/project/details",
            {"name": "Test Project", "description": "Test Description"},
        )

        assert unchanged["status"] == "Project details unchanged."
    finally:
        first_server.shutdown()

    saved_metadata = _read_project_json(project_path)
    assert saved_metadata["name"] == "Test Project"
    assert saved_metadata["description"] == "Test Description"

    second_server = BrowserControlServer(controller=ProjectController(), port=0)
    second_server.start_background(open_browser=False)
    try:
        reopened = _post_json(f"{second_server.url}api/project/open", {"path": str(project_path)})

        assert reopened["project"]["path"] == str(project_path)
        assert reopened["project"]["name"] == "Test Project"
        assert reopened["project"]["description"] == "Test Description"
    finally:
        second_server.shutdown()


def test_browser_post_route_manifest_is_classified_and_disk_asserted() -> None:
    actual_post_routes = _extract_browser_post_routes_from_server_source()
    classified_post_routes = (
        set(DIRECT_PROJECT_JSON_ASSERTION_TESTS_BY_ROUTE)
        | PROJECT_LIFECYCLE_POST_ROUTES
        | NON_PROJECT_JSON_POST_ROUTES
    )

    assert actual_post_routes == classified_post_routes

    for route, test_names in DIRECT_PROJECT_JSON_ASSERTION_TESTS_BY_ROUTE.items():
        assert test_names
        for test_name in test_names:
            test_func = globals().get(test_name)
            assert callable(test_func), f"Missing persistence test function: {test_name}"
            test_source = inspect.getsource(test_func)
            assert route in test_source or route.lstrip("/") in test_source, f"{test_name} does not exercise {route}"
            assert "_read_project_json(" in test_source, f"{test_name} does not assert project.json writes"


def test_browser_autosave_persists_analysis_scoring_timing_and_ui_changes_to_project_json(
    synthetic_video_factory,
    tmp_path: Path,
) -> None:
    project_path = tmp_path / "analysis-autosave.ssproj"
    ProjectController().save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        primary_path = Path(synthetic_video_factory(name="analysis-primary"))

        imported = _post_json(f"{server.url}api/import/primary", {"path": str(primary_path)})
        saved = _read_project_json(project_path)
        assert saved["primary_video"]["path"].startswith("Input/")
        assert saved["analysis"]["beep_time_ms_primary"] == imported["project"]["analysis"]["beep_time_ms_primary"]
        assert len(saved["analysis"]["shots"]) == len(imported["project"]["analysis"]["shots"])

        threshold = _post_json(f"{server.url}api/analysis/threshold", {"threshold": 0.4})
        saved = _read_project_json(project_path)
        assert saved["analysis"]["detection_threshold"] == 0.4
        assert saved["analysis"]["shotml_settings"]["detection_threshold"] == 0.4

        _post_json(
            f"{server.url}api/analysis/shotml-settings",
            {"settings": {"min_shot_interval_ms": 130, "shot_peak_min_spacing_ms": 230}, "rerun": False},
        )
        saved = _read_project_json(project_path)
        assert saved["analysis"]["shotml_settings"]["min_shot_interval_ms"] == 130
        assert saved["analysis"]["shotml_settings"]["shot_peak_min_spacing_ms"] == 230

        _post_json(f"{server.url}api/analysis/shotml/reset-defaults", {})
        saved = _read_project_json(project_path)
        assert saved["analysis"]["shotml_settings"]["detection_threshold"] == 0.35
        assert saved["analysis"]["detection_threshold"] == 0.35
        assert saved["analysis"]["shotml_settings"]["min_shot_interval_ms"] == 100

        first_shot = threshold["project"]["analysis"]["shots"][0]
        first_shot_id = first_shot["id"]
        original_time_ms = first_shot["time_ms"]

        _post_json(f"{server.url}api/beep", {"time_ms": 405})
        saved = _read_project_json(project_path)
        assert saved["analysis"]["beep_time_ms_primary"] == 405

        added = _post_json(f"{server.url}api/shots/add", {"time_ms": 1750})
        added_shot = next(
            shot for shot in added["project"]["analysis"]["shots"]
            if shot["time_ms"] == 1750 and shot["source"] == "manual"
        )
        added_shot_id = added_shot["id"]
        saved = _read_project_json(project_path)
        assert any(
            shot["id"] == added_shot_id and shot["time_ms"] == 1750 and shot["source"] == "manual"
            for shot in saved["analysis"]["shots"]
        )

        _post_json(f"{server.url}api/shots/select", {"shot_id": first_shot_id})
        saved = _read_project_json(project_path)
        assert saved["ui_state"]["selected_shot_id"] == first_shot_id

        _post_json(
            f"{server.url}api/project/ui-state",
            {
                "selected_shot_id": first_shot_id,
                "timeline_zoom": 9.5,
                "timeline_offset_ms": 420,
                "active_tool": "timing",
                "waveform_mode": "add",
                "waveform_expanded": False,
                "timing_expanded": True,
                "layout_locked": False,
                "rail_width": 70,
                "inspector_width": 512,
                "waveform_height": 260,
                "scoring_shot_expansion": {first_shot_id: True},
                "waveform_shot_amplitudes": {first_shot_id: 1.5},
                "timing_edit_shot_ids": [first_shot_id],
                "timing_column_widths": {"segment": 128, "split": 224, "action": 244},
            },
        )
        saved = _read_project_json(project_path)
        assert saved["ui_state"]["selected_shot_id"] == first_shot_id
        assert saved["ui_state"]["timeline_zoom"] == pytest.approx(9.5)
        assert saved["ui_state"]["timeline_offset_ms"] == 420
        assert saved["ui_state"]["active_tool"] == "timing"
        assert saved["ui_state"]["waveform_mode"] == "add"
        assert saved["ui_state"]["waveform_expanded"] is False
        assert saved["ui_state"]["timing_expanded"] is True
        assert saved["ui_state"]["layout_locked"] is False
        assert saved["ui_state"]["rail_width"] == 70
        assert saved["ui_state"]["inspector_width"] == 512
        assert saved["ui_state"]["waveform_height"] == 260
        assert saved["ui_state"]["scoring_shot_expansion"] == {first_shot_id: True}
        assert saved["ui_state"]["waveform_shot_amplitudes"] == {first_shot_id: 1.5}
        assert saved["ui_state"]["timing_edit_shot_ids"] == [first_shot_id]
        assert saved["ui_state"]["timing_column_widths"]["segment"] == 128
        assert saved["ui_state"]["timing_column_widths"]["split"] == 224
        assert saved["ui_state"]["timing_column_widths"]["action"] == 244

        _post_json(f"{server.url}api/shots/move", {"shot_id": first_shot_id, "time_ms": 830})
        saved = _read_project_json(project_path)
        moved_shot = _shot_from_project_json(saved, first_shot_id)
        assert moved_shot["time_ms"] == 830
        assert moved_shot["source"] == "manual"
        assert moved_shot["confidence"] is None

        generated = _post_json(f"{server.url}api/analysis/shotml/proposals", {})
        restore_proposal = next(
            proposal
            for proposal in generated["project"]["analysis"]["timing_change_proposals"]
            if proposal["proposal_type"] == "restore_shot" and proposal["shot_id"] == first_shot_id
        )
        saved = _read_project_json(project_path)
        assert any(proposal["id"] == restore_proposal["id"] for proposal in saved["analysis"]["timing_change_proposals"])

        _post_json(
            f"{server.url}api/analysis/shotml/discard-proposal",
            {"proposal_id": restore_proposal["id"]},
        )
        saved = _read_project_json(project_path)
        assert next(
            proposal for proposal in saved["analysis"]["timing_change_proposals"] if proposal["id"] == restore_proposal["id"]
        )["status"] == "discarded"

        generated = _post_json(f"{server.url}api/analysis/shotml/proposals", {})
        apply_proposal = next(
            proposal
            for proposal in generated["project"]["analysis"]["timing_change_proposals"]
            if proposal["proposal_type"] == "restore_shot" and proposal["status"] == "pending"
        )
        _post_json(
            f"{server.url}api/analysis/shotml/apply-proposal",
            {"proposal_id": apply_proposal["id"]},
        )
        saved = _read_project_json(project_path)
        restored_by_proposal = _shot_from_project_json(saved, first_shot_id)
        assert restored_by_proposal["time_ms"] == original_time_ms

        _post_json(f"{server.url}api/scoring/profile", {"ruleset": "uspsa_major"})
        saved = _read_project_json(project_path)
        assert saved["scoring"]["ruleset"] == "uspsa_major"

        _post_json(
            f"{server.url}api/scoring",
            {"enabled": True, "penalties": 1.5, "penalty_counts": {"procedural_errors": 2}},
        )
        saved = _read_project_json(project_path)
        assert saved["scoring"]["enabled"] is True
        assert saved["scoring"]["penalties"] == pytest.approx(1.5)
        assert saved["scoring"]["penalty_counts"] == {"procedural_errors": 2.0}

        _post_json(
            f"{server.url}api/scoring/score",
            {"shot_id": first_shot_id, "letter": "C", "penalty_counts": {"procedural_errors": 1}},
        )
        saved = _read_project_json(project_path)
        scored_shot = _shot_from_project_json(saved, first_shot_id)
        assert scored_shot["score"]["letter"] == "C"
        assert scored_shot["score"]["penalty_counts"] == {"procedural_errors": 1.0}

        _post_json(
            f"{server.url}api/scoring/position",
            {"shot_id": first_shot_id, "x_norm": 0.25, "y_norm": 0.75},
        )
        saved = _read_project_json(project_path)
        positioned_shot = _shot_from_project_json(saved, first_shot_id)
        assert positioned_shot["score"]["x_norm"] == pytest.approx(0.25)
        assert positioned_shot["score"]["y_norm"] == pytest.approx(0.75)

        added_event = _post_json(
            f"{server.url}api/events/add",
            {"kind": "reload", "after_shot_id": first_shot_id, "note": "Cleanup"},
        )
        event_id = added_event["project"]["analysis"]["events"][0]["id"]
        saved = _read_project_json(project_path)
        assert saved["analysis"]["events"][0]["note"] == "Cleanup"
        assert saved["analysis"]["events"][0]["after_shot_id"] == first_shot_id

        _post_json(f"{server.url}api/events/delete", {"event_id": event_id})
        saved = _read_project_json(project_path)
        assert saved["analysis"]["events"] == []

        _post_json(f"{server.url}api/shots/restore", {"shot_id": first_shot_id})
        saved = _read_project_json(project_path)
        restored_shot = _shot_from_project_json(saved, first_shot_id)
        assert restored_shot["time_ms"] == original_time_ms

        _post_json(f"{server.url}api/scoring/restore", {"shot_id": first_shot_id})
        saved = _read_project_json(project_path)
        restored_score = _shot_from_project_json(saved, first_shot_id)
        assert restored_score["score"]["letter"] == "A"

        _post_json(f"{server.url}api/shots/delete", {"shot_id": added_shot_id})
        saved = _read_project_json(project_path)
        assert all(shot["id"] != added_shot_id for shot in saved["analysis"]["shots"])
    finally:
        server.shutdown()


def test_browser_autosave_persists_overlay_merge_export_and_media_routes_to_project_json(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    project_path = tmp_path / "overlay-merge-autosave.ssproj"
    ProjectController().save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        primary_path = Path(synthetic_video_factory(name="upload-primary"))
        secondary_one = Path(synthetic_video_factory(name="secondary-one", beep_ms=620))
        secondary_two = Path(synthetic_video_factory(name="secondary-two", beep_ms=640))
        secondary_three = Path(synthetic_video_factory(name="secondary-three", beep_ms=660))
        secondary_four = Path(synthetic_video_factory(name="secondary-four", beep_ms=680))

        uploaded_primary = _post_multipart(
            f"{server.url}api/files/primary",
            "file",
            primary_path.name,
            primary_path.read_bytes(),
        )
        first_shot_id = uploaded_primary["project"]["analysis"]["shots"][0]["id"]
        saved = _read_project_json(project_path)
        assert saved["primary_video"]["path"].startswith("Input/")
        assert len(saved["analysis"]["shots"]) == len(uploaded_primary["project"]["analysis"]["shots"])

        uploaded_secondary = _post_multipart(
            f"{server.url}api/files/secondary",
            "file",
            secondary_one.name,
            secondary_one.read_bytes(),
        )
        first_source_id = uploaded_secondary["project"]["merge_sources"][0]["id"]
        saved = _read_project_json(project_path)
        assert len(saved["merge_sources"]) == 1
        assert saved["secondary_video"]["path"].startswith("Input/")

        _post_multipart(
            f"{server.url}api/files/merge",
            "file",
            secondary_two.name,
            secondary_two.read_bytes(),
        )
        saved = _read_project_json(project_path)
        assert len(saved["merge_sources"]) == 2

        _post_json(f"{server.url}api/import/secondary", {"path": str(secondary_three)})
        saved = _read_project_json(project_path)
        assert len(saved["merge_sources"]) == 3

        _post_json(f"{server.url}api/import/merge", {"path": str(secondary_four)})
        saved = _read_project_json(project_path)
        assert len(saved["merge_sources"]) == 4

        _post_json(
            f"{server.url}api/merge",
            {"enabled": True, "layout": "pip", "pip_size_percent": 44, "pip_x": 0.12, "pip_y": 0.76},
        )
        saved = _read_project_json(project_path)
        assert saved["merge"]["enabled"] is True
        assert saved["merge"]["layout"] == "pip"
        assert saved["merge"]["pip_size_percent"] == 44
        assert saved["merge"]["pip_x"] == pytest.approx(0.12)
        assert saved["merge"]["pip_y"] == pytest.approx(0.76)

        _post_json(f"{server.url}api/merge", {"pip_size": "50%"})
        saved = _read_project_json(project_path)
        assert saved["merge"]["pip_size"] == "50%"
        assert saved["merge"]["pip_size_percent"] == 50

        _post_json(
            f"{server.url}api/merge/source",
            {
                "source_id": first_source_id,
                "pip_size_percent": 33,
                "pip_x": 0.21,
                "pip_y": 0.68,
                "sync_offset_ms": -25,
            },
        )
        saved = _read_project_json(project_path)
        first_source = _merge_source_from_project_json(saved, first_source_id)
        assert first_source["pip_size_percent"] == 33
        assert first_source["pip_x"] == pytest.approx(0.21)
        assert first_source["pip_y"] == pytest.approx(0.68)
        assert first_source["sync_offset_ms"] == -25
        assert saved["analysis"]["sync_offset_ms"] == -25

        _post_json(f"{server.url}api/merge/source", {"source_id": first_source_id, "sync_delta_ms": 5})
        saved = _read_project_json(project_path)
        first_source = _merge_source_from_project_json(saved, first_source_id)
        assert first_source["sync_offset_ms"] == -20
        assert saved["analysis"]["sync_offset_ms"] == -20

        _post_json(f"{server.url}api/sync", {"offset_ms": 35})
        saved = _read_project_json(project_path)
        first_source = _merge_source_from_project_json(saved, first_source_id)
        assert saved["analysis"]["sync_offset_ms"] == 35
        assert first_source["sync_offset_ms"] == 35

        _post_json(f"{server.url}api/sync", {"delta_ms": -10})
        saved = _read_project_json(project_path)
        first_source = _merge_source_from_project_json(saved, first_source_id)
        assert saved["analysis"]["sync_offset_ms"] == 25
        assert first_source["sync_offset_ms"] == 25

        _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "badge_size": "XL",
                "style_type": "bubble",
                "spacing": 9,
                "margin": 7,
                "show_timer": False,
                "show_draw": False,
                "show_shots": True,
                "show_score": False,
                "custom_box_enabled": True,
                "custom_box_mode": "manual",
                "custom_box_text": "Session summary",
                "custom_box_quadrant": "top_left",
                "custom_box_width": 180,
                "custom_box_height": 64,
                "custom_box_background_color": "#101010",
                "custom_box_text_color": "#ffffff",
                "custom_box_opacity": 0.75,
                "styles": {
                    "timer_badge": {
                        "background_color": "#123456",
                        "text_color": "#ffffff",
                        "opacity": 0.5,
                    }
                },
                "scoring_colors": {"A": "#22C55E"},
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
                        "source": "manual",
                        "text": "Session summary",
                        "quadrant": "top_left",
                        "background_color": "#101010",
                        "text_color": "#ffffff",
                        "opacity": 0.75,
                        "width": 180,
                        "height": 64,
                    }
                ],
            },
        )
        saved = _read_project_json(project_path)
        assert saved["overlay"]["position"] == "top"
        assert saved["overlay"]["badge_size"] == "XL"
        assert saved["overlay"]["style_type"] == "bubble"
        assert saved["overlay"]["spacing"] == 9
        assert saved["overlay"]["margin"] == 7
        assert saved["overlay"]["show_timer"] is False
        assert saved["overlay"]["show_draw"] is False
        assert saved["overlay"]["show_shots"] is True
        assert saved["overlay"]["show_score"] is False
        assert saved["overlay"]["custom_box_enabled"] is True
        assert saved["overlay"]["custom_box_text"] == "Session summary"
        assert saved["overlay"]["custom_box_quadrant"] == "top_left"
        assert saved["overlay"]["custom_box_width"] == 180
        assert saved["overlay"]["custom_box_height"] == 64
        assert saved["overlay"]["timer_badge"]["background_color"] == "#123456"
        assert saved["overlay"]["timer_badge"]["opacity"] == pytest.approx(0.5)
        assert saved["overlay"]["scoring_colors"]["A"] == "#22C55E"
        assert saved["overlay"]["text_boxes"][0]["text"] == "Session summary"

        _post_json(
            f"{server.url}api/popups",
            {
                "popups": [
                    {
                        "id": "popup-one",
                        "enabled": True,
                        "text": "-0",
                        "anchor_mode": "shot",
                        "shot_id": first_shot_id,
                        "time_ms": 1200,
                        "duration_ms": 1000,
                        "follow_motion": True,
                        "motion_path": [
                            {"offset_ms": 250, "x": 0.45, "y": 0.55},
                            {"offset_ms": 750, "x": 0.52, "y": 0.63},
                        ],
                        "quadrant": "custom",
                        "x": 0.42,
                        "y": 0.58,
                        "background_color": "#000000",
                        "text_color": "#ffffff",
                        "opacity": 0.8,
                        "width": 88,
                        "height": 36,
                    }
                ]
            },
        )
        saved = _read_project_json(project_path)
        assert saved["popups"][0]["text"] == "-0"
        assert saved["popups"][0]["anchor_mode"] == "shot"
        assert saved["popups"][0]["shot_id"] == first_shot_id
        assert saved["popups"][0]["time_ms"] == 1200
        assert saved["popups"][0]["duration_ms"] == 1000
        assert saved["popups"][0]["follow_motion"] is True
        assert saved["popups"][0]["motion_path"][0]["offset_ms"] == 250
        assert saved["popups"][0]["motion_path"][0]["x"] == pytest.approx(0.45)
        assert saved["popups"][0]["motion_path"][1]["offset_ms"] == 750
        assert saved["popups"][0]["quadrant"] == "custom"
        assert saved["popups"][0]["x"] == pytest.approx(0.42)
        assert saved["popups"][0]["y"] == pytest.approx(0.58)

        project_output_path = project_path / "Output" / "autosave-output.mp4"
        _post_json(
            f"{server.url}api/export/settings",
            {
                "output_path": str(project_output_path),
                "quality": "medium",
                "aspect_ratio": "9:16",
                "target_width": 720,
                "target_height": 1280,
            },
        )
        saved = _read_project_json(project_path)
        assert saved["export"]["output_path"] == "Output/autosave-output.mp4"
        assert saved["export"]["quality"] == "medium"
        assert saved["export"]["aspect_ratio"] == "9:16"
        assert saved["export"]["target_width"] == 720
        assert saved["export"]["target_height"] == 1280
        assert saved["export"]["preset"] == "custom"

        _post_json(f"{server.url}api/export/preset", {"preset": "youtube_long_1080p"})
        saved = _read_project_json(project_path)
        assert saved["export"]["preset"] == "youtube_long_1080p"

        before_swap = _read_project_json(project_path)
        old_primary_path = before_swap["primary_video"]["path"]
        old_first_source_path = before_swap["merge_sources"][0]["asset"]["path"]
        _post_json(f"{server.url}api/swap", {})
        after_swap = _read_project_json(project_path)
        assert after_swap["primary_video"]["path"] == old_first_source_path
        assert after_swap["secondary_video"]["path"] == old_primary_path

        removable_source_id = after_swap["merge_sources"][-1]["id"]
        _post_json(f"{server.url}api/merge/remove", {"source_id": removable_source_id})
        saved = _read_project_json(project_path)
        assert len(saved["merge_sources"]) == 3
        assert all(source["id"] != removable_source_id for source in saved["merge_sources"])

        export_target = tmp_path / "browser-autosave-export.mp4"

        def fake_export_project(project, output_target, progress_callback=None, log_callback=None):
            Path(output_target).write_bytes(b"ok")
            return Path(output_target)

        monkeypatch.setattr(browser_server_module, "export_project", fake_export_project)

        _post_json(
            f"{server.url}api/export",
            {
                "path": str(export_target),
                "quality": "medium",
                "aspect_ratio": "original",
                "scoring": {
                    "ruleset": "uspsa_minor",
                    "enabled": True,
                    "penalties": 0,
                    "penalty_counts": {},
                },
                "overlay": {
                    "position": "top",
                    "custom_box_enabled": True,
                    "custom_box_text": "Export Summary",
                },
                "merge": {
                    "enabled": True,
                    "layout": "pip",
                    "pip_size_percent": 40,
                    "pip_x": 0.18,
                    "pip_y": 0.72,
                    "sources": [
                        {
                            "source_id": first_source_id,
                            "pip_size_percent": 40,
                            "pip_x": 0.18,
                            "pip_y": 0.72,
                            "sync_offset_ms": 15,
                        }
                    ],
                },
            },
        )
        saved = _read_project_json(project_path)
        assert saved["export"]["output_path"] == str(export_target)
        assert saved["overlay"]["custom_box_text"] == "Export Summary"
        assert saved["merge"]["layout"] == "pip"
        assert _merge_source_from_project_json(saved, first_source_id)["sync_offset_ms"] == 15
    finally:
        server.shutdown()


def test_browser_settings_reset_defaults_restores_project_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "load_settings", lambda: controller_module.AppSettings())
    monkeypatch.setattr(controller_module, "save_settings", lambda settings: None)

    project_path = tmp_path / "settings-reset-autosave.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        _post_json(f"{server.url}api/overlay", {"position": "top", "badge_size": "XL"})
        _post_json(f"{server.url}api/merge", {"layout": "pip", "pip_size": "50%"})
        _post_json(f"{server.url}api/export/settings", {"quality": "low"})
        _post_json(
            f"{server.url}api/analysis/shotml-settings",
            {"settings": {"min_shot_interval_ms": 130, "shot_peak_min_spacing_ms": 230}, "rerun": False},
        )

        reset = _post_json(f"{server.url}api/settings/reset-defaults", {})
        saved = _read_project_json(project_path)

        assert reset["settings"]["overlay_position"] == "bottom"
        assert reset["settings"]["merge_layout"] == "side_by_side"
        assert reset["settings"]["pip_size"] == "35%"
        assert reset["settings"]["export_quality"] == "high"
        assert reset["settings"]["default_match_type"] == "uspsa"
        assert reset["settings"]["badge_size"] == "M"
        assert reset["settings"]["merge_pip_x"] == 1.0
        assert reset["settings"]["merge_pip_y"] == 1.0
        assert reset["settings"]["export_preset"] == "source"
        assert reset["settings"]["export_frame_rate"] == "source"
        assert reset["settings"]["marker_template"]["background_color"] == "#000000"
        assert reset["settings"]["marker_template"]["opacity"] == 0.9
        assert reset["settings"]["shotml_defaults"]["min_shot_interval_ms"] == 100
        assert reset["settings"]["shotml_defaults"]["shot_peak_min_spacing_ms"] == 200

        assert saved["overlay"]["position"] == "bottom"
        assert saved["overlay"]["badge_size"] == "M"
        assert saved["merge"]["layout"] == "side_by_side"
        assert saved["merge"]["pip_size"] == "35%"
        assert saved["merge"]["pip_size_percent"] == 35
        assert saved["merge"]["pip_x"] == 1.0
        assert saved["merge"]["pip_y"] == 1.0
        assert saved["export"]["quality"] == "high"
        assert saved["export"]["preset"] == "source"
        assert saved["export"]["frame_rate"] == "source"
        assert saved["scoring"]["match_type"] == "uspsa"
        assert saved["analysis"]["shotml_settings"]["min_shot_interval_ms"] == 100
        assert saved["analysis"]["shotml_settings"]["shot_peak_min_spacing_ms"] == 200
    finally:
        server.shutdown()


def test_browser_settings_reset_defaults_deletes_folder_settings_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "load_settings", lambda: controller_module.AppSettings())
    monkeypatch.setattr(controller_module, "save_settings", lambda settings: None)

    project_path = tmp_path / "settings-reset-folder.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        _post_json(
            f"{server.url}api/settings",
            {
                "scope": "folder",
                "settings": {
                    "default_tool": "review",
                    "merge_layout": "pip",
                },
            },
        )

        folder_settings_path = project_path / "splitshot.conf"
        assert folder_settings_path.exists()

        _post_json(f"{server.url}api/settings/reset-defaults", {})

        assert not folder_settings_path.exists()
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        assert reopened["settings"]["default_tool"] == "project"
        assert reopened["settings"]["merge_layout"] == "side_by_side"
    finally:
        server.shutdown()


def test_browser_project_open_ignores_invalid_folder_settings(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        controller_module,
        "load_settings",
        lambda: controller_module.AppSettings(default_tool="metrics"),
    )
    monkeypatch.setattr(controller_module, "save_settings", lambda settings: None)

    project_path = tmp_path / "invalid-folder-settings.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))
    (project_path / "splitshot.conf").write_text("not = [valid\n", encoding="utf-8")

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        assert state["settings"]["default_tool"] == "metrics"
        assert state["settings_layers"]["folder"] == {}
        assert "Folder defaults were ignored:" in state["settings_layers"]["project"]["folder_settings_error"]
    finally:
        server.shutdown()


def test_browser_popup_image_assets_are_bundled_and_served(tmp_path: Path) -> None:
    project_path = tmp_path / "popup-images.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))

    marker_image = tmp_path / "marker-image.png"
    marker_image.write_bytes(b"popup-image-bytes")

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        _post_json(
            f"{server.url}api/popups",
            {
                "popups": [
                    {
                        "id": "popup-image",
                        "enabled": True,
                        "text": "",
                        "content_type": "image",
                        "image_path": str(marker_image),
                        "anchor_mode": "time",
                        "time_ms": 1200,
                        "duration_ms": 1000,
                        "quadrant": "middle_middle",
                        "x": 0.5,
                        "y": 0.5,
                    }
                ]
            },
        )

        saved = _read_project_json(project_path)
        assert saved["popups"][0]["image_path"] == "Markers/marker-image.png"

        with urllib.request.urlopen(f"{server.url}media/popup/popup-image", timeout=30) as response:
            assert response.read() == b"popup-image-bytes"
    finally:
        server.shutdown()


def test_browser_state_exposes_settings_layers_and_folder_precedence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(controller_module, "load_settings", lambda: controller_module.AppSettings())
    monkeypatch.setattr(controller_module, "save_settings", lambda settings: None)

    project_path = tmp_path / "settings-layers.ssproj"
    controller = ProjectController()
    controller.save_project(str(project_path))

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        _post_json(
            f"{server.url}api/settings",
            {
                "scope": "app",
                "settings": {
                    "default_tool": "metrics",
                    "merge_layout": "pip",
                },
            },
        )
        _post_json(
            f"{server.url}api/settings",
            {
                "scope": "folder",
                "settings": {
                    "default_tool": "review",
                    "merge_layout": "above_below",
                },
            },
        )

        state = _get_json(f"{server.url}api/state")

        assert state["settings_layers"]["app"]["default_tool"] == "metrics"
        assert state["settings_layers"]["folder"]["default_tool"] == "review"
        assert state["settings"]["default_tool"] == "review"
        assert state["settings_layers"]["app"]["merge_layout"] == "pip"
        assert state["settings_layers"]["folder"]["merge_layout"] == "above_below"
        assert state["settings"]["merge_layout"] == "above_below"
        assert state["settings_layers"]["project"]["path"] == str(project_path)
    finally:
        server.shutdown()


def test_browser_autosave_persists_practiscore_routes_to_project_json(tmp_path: Path) -> None:
    project_path = tmp_path / "practiscore-autosave.ssproj"
    ProjectController().save_project(str(project_path))

    server = BrowserControlServer(controller=ProjectController(), port=0)
    examples_dir = EXAMPLES_DIR / "IDPA"
    server.start_background(open_browser=False)
    try:
        _post_json(f"{server.url}api/project/open", {"path": str(project_path)})

        _post_json(
            f"{server.url}api/project/practiscore",
            {
                "match_type": "idpa",
                "stage_number": 2,
                "competitor_name": "John Klockenkemper",
                "competitor_place": 4,
            },
        )
        saved = _read_project_json(project_path)
        assert saved["scoring"]["match_type"] == "idpa"
        assert saved["scoring"]["stage_number"] == 2
        assert saved["scoring"]["competitor_name"] == "John Klockenkemper"
        assert saved["scoring"]["competitor_place"] == 4

        _post_multipart(
            f"{server.url}api/files/practiscore",
            "file",
            "IDPA.csv",
            (examples_dir / "IDPA.csv").read_bytes(),
        )
        saved = _read_project_json(project_path)
        assert saved["scoring"]["practiscore_source_path"].startswith("CSV/")
        assert saved["scoring"]["practiscore_source_name"] == "IDPA.csv"
        assert saved["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert saved["scoring"]["imported_stage"]["stage_number"] == 2
        assert saved["scoring"]["imported_stage"]["competitor_name"] == "John Klockenkemper"
        assert any(box["source"] == "imported_summary" for box in saved["overlay"]["text_boxes"])
    finally:
        server.shutdown()


def test_browser_project_open_recovers_practiscore_from_project_csv_folder(tmp_path: Path) -> None:
    controller = ProjectController()
    project_path = tmp_path / "recovered-practiscore.ssproj"
    controller.save_project(str(project_path))
    staged_csv = project_path / "CSV" / "IDPA.csv"
    staged_csv.write_bytes((EXAMPLES_DIR / "IDPA" / "IDPA.csv").read_bytes())

    server = BrowserControlServer(controller=ProjectController(), port=0)
    server.start_background(open_browser=False)
    try:
        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path)})
        saved = _read_project_json(project_path)

        assert reopened["project"]["path"] == str(project_path)
        assert reopened["project"]["scoring"]["practiscore_source_path"] == str(staged_csv.resolve())
        assert reopened["project"]["scoring"]["enabled"] is True
        assert reopened["project"]["scoring"]["ruleset"] == "idpa_time_plus"
        assert reopened["project"]["scoring"]["match_type"] == "idpa"
        assert reopened["project"]["scoring"]["stage_number"] == 1
        assert reopened["project"]["scoring"]["competitor_name"] == "Jeff Graff"
        assert reopened["project"]["scoring"]["competitor_place"] == 1
        assert reopened["project"]["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert reopened["project"]["scoring"]["imported_stage"]["match_type"] == "idpa"
        assert reopened["project"]["scoring"]["imported_stage"]["stage_number"] == 1
        assert reopened["project"]["scoring"]["imported_stage"]["competitor_name"] == "Jeff Graff"
        assert reopened["project"]["scoring"]["imported_stage"]["competitor_place"] == 1
        assert reopened["practiscore_options"]["has_source"] is True
        assert reopened["practiscore_options"]["source_name"] == "IDPA.csv"
        assert reopened["practiscore_options"]["detected_match_type"] == "idpa"
        assert reopened["practiscore_options"]["stage_numbers"] == [1, 2, 3, 4]
        assert reopened["project"]["overlay"]["custom_box_mode"] == "imported_summary"
        assert any(box["source"] == "imported_summary" for box in reopened["project"]["overlay"]["text_boxes"])
        assert saved["scoring"]["match_type"] == "idpa"
        assert saved["scoring"]["stage_number"] == 1
        assert saved["scoring"]["competitor_name"] == "Jeff Graff"
        assert saved["scoring"]["competitor_place"] == 1
        assert saved["scoring"]["imported_stage"]["source_name"] == "IDPA.csv"
        assert reopened["status"] == (
            f"Opened project folder {project_path} and restored PractiScore from IDPA.csv."
        )
    finally:
        server.shutdown()


def test_browser_project_save_bundles_imported_media_for_reopen(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        primary_path = Path(synthetic_video_factory(name="primary-upload"))
        secondary_path = Path(synthetic_video_factory(name="secondary-upload"))
        project_path = tmp_path / "uploaded-media.ssproj"

        _post_multipart(
            f"{server.url}api/files/primary",
            "file",
            primary_path.name,
            primary_path.read_bytes(),
        )
        _post_multipart(
            f"{server.url}api/files/merge",
            "file",
            secondary_path.name,
            secondary_path.read_bytes(),
        )
        saved = _post_json(f"{server.url}api/project/save", {"path": str(project_path)})

        bundled_primary = Path(saved["project"]["primary_video"]["path"])
        bundled_secondary = Path(saved["project"]["secondary_video"]["path"])
        assert bundled_primary.parent == project_path / "Input"
        assert bundled_secondary.parent == project_path / "Input"
    finally:
        server.shutdown()

    reopened = ProjectController()
    reopened.open_project(str(project_path))

    assert Path(reopened.project.primary_video.path).exists()
    assert Path(reopened.project.primary_video.path).parent == project_path / "Input"
    assert reopened.project.secondary_video is not None
    assert Path(reopened.project.secondary_video.path).exists()
    assert Path(reopened.project.secondary_video.path).parent == project_path / "Input"


def test_browser_media_endpoint_supports_http_range_requests(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        controller.ingest_primary_video(str(video_path))

        request = urllib.request.Request(
            f"{server.url}media/primary",
            headers={"Range": "bytes=0-31"},
        )
        with urllib.request.urlopen(request, timeout=30) as response:
            assert response.status == 206
            assert response.headers["Content-Range"].startswith("bytes 0-31/")
            assert response.read() == video_path.read_bytes()[:32]
    finally:
        server.shutdown()


def test_browser_media_endpoint_rejects_invalid_ranges(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        controller.ingest_primary_video(str(video_path))
        invalid_start = video_path.stat().st_size + 128
        request = urllib.request.Request(
            f"{server.url}media/primary",
            headers={"Range": f"bytes={invalid_start}-{invalid_start + 32}"},
        )

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            urllib.request.urlopen(request, timeout=30)

        assert exc_info.value.code == 416
    finally:
        server.shutdown()


def test_browser_state_marks_missing_project_media_unavailable(tmp_path: Path) -> None:
    project = Project()
    project.primary_video.path = str(tmp_path / "missing.mp4")

    payload = browser_state(project, "Ready.")

    assert payload["media"]["primary_available"] is False
    assert payload["media"]["primary_url"] is None


def test_browser_media_endpoint_transcodes_pcm_audio_preview_once(monkeypatch, tmp_path: Path) -> None:
    controller = ProjectController()
    source_path = tmp_path / "Stage1.MP4"
    source_path.write_bytes(b"source-media")
    ffprobe_calls: list[Path] = []
    ffmpeg_calls: list[list[str]] = []

    def fake_ingest(path: str, source_name: str | None = None) -> None:
        controller.project.primary_video.path = path
        controller.project.primary_video.width = 1920
        controller.project.primary_video.height = 1080
        controller.project.primary_video.duration_ms = 31_425
        controller.status_message = "Primary analysis complete."

    def fake_ffprobe(path: Path) -> dict:
        ffprobe_calls.append(path)
        return {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "pcm_s16le"},
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
        }

    def fake_ffmpeg(command: list[str]) -> None:
        ffmpeg_calls.append(command)
        Path(command[-1]).write_bytes(b"browser-preview")

    monkeypatch.setattr(controller, "ingest_primary_video", fake_ingest)
    monkeypatch.setattr(browser_server_module, "run_ffprobe_json", fake_ffprobe)
    monkeypatch.setattr(browser_server_module, "run_ffmpeg", fake_ffmpeg)
    monkeypatch.setattr(
        browser_server_module,
        "_validate_browser_preview_timeline",
        lambda source_path, metadata, preview_path: (True, {"codec_name": "h264"}, {"codec_name": "h264"}),
    )

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(f"{server.url}api/import/primary", {"path": str(source_path)})

        assert state["media"]["primary_available"] is True
        assert state["status"] == "Primary analysis complete."
        assert len(ffprobe_calls) == 1
        assert len(ffmpeg_calls) == 1
        assert ["-c:a", "aac"] == ffmpeg_calls[0][8:10]

        with urllib.request.urlopen(f"{server.url}media/primary", timeout=30) as response:
            assert response.read() == b"browser-preview"

        with urllib.request.urlopen(f"{server.url}media/primary", timeout=30) as response:
            assert response.read() == b"browser-preview"

        assert len(ffprobe_calls) == 1
        assert len(ffmpeg_calls) == 1
        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "media.compatibility.created" in log_text
    finally:
        server.shutdown()


def test_browser_media_endpoint_returns_404_when_preview_disappears(tmp_path: Path) -> None:
    controller = ProjectController()
    source_path = tmp_path / "Stage1.MP4"
    source_path.write_bytes(b"source-media")
    controller.project.primary_video.path = str(source_path)
    controller.project.primary_video.width = 1920
    controller.project.primary_video.height = 1080
    controller.project.primary_video.duration_ms = 31_425

    server = BrowserControlServer(controller=controller, port=0)
    server._prepare_browser_media = lambda path: (tmp_path / "missing-browser-preview.mp4", True, "test_missing_preview", "aac")
    server.start_background(open_browser=False)
    try:
        with pytest.raises(urllib.error.HTTPError) as excinfo:
            urllib.request.urlopen(f"{server.url}media/primary", timeout=30)

        assert excinfo.value.code == 404
        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "media.missing" in log_text
        assert "missing-browser-preview.mp4" in log_text
    finally:
        server.shutdown()


def test_browser_preview_timeline_ignores_container_duration_drift_when_other_video_metadata_matches() -> None:
    source_timeline = {
        "codec_name": "h264",
        "width": "1920",
        "height": "1080",
        "start_pts": "0",
        "start_time": "0.000000",
        "time_base": "1/60000",
        "duration_ts": "1885508",
        "avg_frame_rate": "60/1",
        "r_frame_rate": "60/1",
        "nb_frames": "1902",
    }
    preview_timeline = {
        **source_timeline,
        "duration_ts": "1887000",
    }

    assert browser_server_module._browser_preview_matches_source_timeline(source_timeline, preview_timeline) is True


def test_browser_preview_timeline_rejects_frame_count_mismatch() -> None:
    source_timeline = {
        "codec_name": "h264",
        "width": "1920",
        "height": "1080",
        "start_pts": "0",
        "start_time": "0.000000",
        "time_base": "1/60000",
        "duration_ts": "1885508",
        "avg_frame_rate": "60/1",
        "r_frame_rate": "60/1",
        "nb_frames": "1902",
    }
    preview_timeline = {
        **source_timeline,
        "nb_frames": "1901",
    }

    assert browser_server_module._browser_preview_matches_source_timeline(source_timeline, preview_timeline) is False


def test_browser_preview_timeline_requires_exact_packet_match(monkeypatch, tmp_path: Path) -> None:
    source_path = tmp_path / "source.mp4"
    preview_path = tmp_path / "preview.mp4"
    source_path.write_bytes(b"source")
    preview_path.write_bytes(b"preview")

    source_metadata = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "start_pts": 0,
                "start_time": "0.000000",
                "time_base": "1/60000",
                "duration_ts": 1885508,
                "avg_frame_rate": "60/1",
                "r_frame_rate": "60/1",
                "nb_frames": 1902,
            }
        ]
    }
    preview_metadata = {
        "streams": [
            {
                "codec_type": "video",
                "codec_name": "h264",
                "width": 1920,
                "height": 1080,
                "start_pts": 0,
                "start_time": "0.000000",
                "time_base": "1/60000",
                "duration_ts": 1887000,
                "avg_frame_rate": "60/1",
                "r_frame_rate": "60/1",
                "nb_frames": 1902,
            }
        ]
    }

    monkeypatch.setattr(browser_server_module, "run_ffprobe_json", lambda path: preview_metadata)
    packet_outputs = {
        str(source_path): "0,0,1000,K_\n1000,1000,1000,_D_\n",
        str(preview_path): "0,0,1000,K_\n1000,1000,1000,___\n",
    }
    monkeypatch.setattr(browser_server_module, "_ffprobe_video_packet_csv", lambda path: packet_outputs[str(path)])

    timeline_valid, _source_timeline, _preview_timeline = browser_server_module._validate_browser_preview_timeline(
        source_path,
        source_metadata,
        preview_path,
    )
    assert timeline_valid is True

    packet_outputs[str(preview_path)] = "0,0,1000,K_\n1001,1001,1000,__\n"

    timeline_valid, _source_timeline, _preview_timeline = browser_server_module._validate_browser_preview_timeline(
        source_path,
        source_metadata,
        preview_path,
    )
    assert timeline_valid is False


def test_browser_media_endpoint_falls_back_to_source_when_preview_timeline_validation_fails(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    source_path = tmp_path / "Stage1.MP4"
    source_path.write_bytes(b"source-media")
    ffprobe_calls: list[Path] = []
    ffmpeg_calls: list[list[str]] = []

    def fake_ingest(path: str, source_name: str | None = None) -> None:
        controller.project.primary_video.path = path
        controller.project.primary_video.width = 1920
        controller.project.primary_video.height = 1080
        controller.project.primary_video.duration_ms = 31_425
        controller.status_message = "Primary analysis complete."

    def fake_ffprobe(path: Path) -> dict:
        ffprobe_calls.append(path)
        return {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "pcm_s16le"},
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
        }

    def fake_ffmpeg(command: list[str]) -> None:
        ffmpeg_calls.append(command)
        Path(command[-1]).write_bytes(b"browser-preview")

    monkeypatch.setattr(controller, "ingest_primary_video", fake_ingest)
    monkeypatch.setattr(browser_server_module, "run_ffprobe_json", fake_ffprobe)
    monkeypatch.setattr(browser_server_module, "run_ffmpeg", fake_ffmpeg)
    monkeypatch.setattr(
        browser_server_module,
        "_validate_browser_preview_timeline",
        lambda source_path, metadata, preview_path: (False, {"codec_name": "h264"}, {"codec_name": "libx264"}),
    )

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(f"{server.url}api/import/primary", {"path": str(source_path)})

        assert state["media"]["primary_available"] is True
        assert state["status"] == "Primary analysis complete."
        assert len(ffprobe_calls) == 1
        assert len(ffmpeg_calls) == 1

        with urllib.request.urlopen(f"{server.url}media/primary", timeout=30) as response:
            assert response.read() == b"source-media"

        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "media.compatibility.rejected" in log_text
        assert "media.compatibility.created" not in log_text
    finally:
        server.shutdown()


def test_browser_media_endpoint_serves_source_media_when_audio_is_browser_safe(
    monkeypatch,
    tmp_path: Path,
) -> None:
    controller = ProjectController()
    source_path = tmp_path / "Stage1.MP4"
    source_path.write_bytes(b"source-media")
    ffprobe_calls: list[Path] = []
    ffmpeg_calls: list[list[str]] = []

    def fake_ingest(path: str, source_name: str | None = None) -> None:
        controller.project.primary_video.path = path
        controller.project.primary_video.width = 1920
        controller.project.primary_video.height = 1080
        controller.project.primary_video.duration_ms = 31_425
        controller.status_message = "Primary analysis complete."

    def fake_ffprobe(path: Path) -> dict:
        ffprobe_calls.append(path)
        return {
            "streams": [
                {"codec_type": "video", "codec_name": "h264"},
                {"codec_type": "audio", "codec_name": "aac"},
            ],
            "format": {"format_name": "mov,mp4,m4a,3gp,3g2,mj2"},
        }

    def fake_ffmpeg(command: list[str]) -> None:
        ffmpeg_calls.append(command)

    monkeypatch.setattr(controller, "ingest_primary_video", fake_ingest)
    monkeypatch.setattr(browser_server_module, "run_ffprobe_json", fake_ffprobe)
    monkeypatch.setattr(browser_server_module, "run_ffmpeg", fake_ffmpeg)

    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(f"{server.url}api/import/primary", {"path": str(source_path)})

        assert state["media"]["primary_available"] is True
        assert state["media"]["primary_url"] == "/media/primary"
        assert state["status"] == "Primary analysis complete."
        assert len(ffprobe_calls) == 1
        assert ffmpeg_calls == []

        with urllib.request.urlopen(f"{server.url}media/primary", timeout=30) as response:
            assert response.read() == b"source-media"

        log_text = server.activity.path.read_text(encoding="utf-8")
        assert "media.compatibility.created" not in log_text
        assert "media.compatibility.rejected" not in log_text
    finally:
        server.shutdown()


def test_browser_media_cache_token_changes_when_same_primary_path_is_reimported(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())

        first_state = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        second_state = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})

        assert first_state["media"]["primary_url"] == "/media/primary"
        assert first_state["media"]["cache_token"]
        assert second_state["media"]["cache_token"]
        assert second_state["media"]["cache_token"] != first_state["media"]["cache_token"]
    finally:
        server.shutdown()


def test_browser_control_api_updates_overlay_styles_and_scoring_preset(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        state = _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        shot_id = state["project"]["analysis"]["shots"][0]["id"]

        state = _post_json(
            f"{server.url}api/overlay",
            {
                "position": "top",
                "badge_size": "XL",
                "styles": {
                    "timer_badge": {
                        "background_color": "#123456",
                        "text_color": "#abcdef",
                        "opacity": 0.55,
                    }
                },
                "scoring_colors": {"A": "#00ff00", "PE": "#112233"},
                "style_type": "rounded",
                "spacing": 6,
                "margin": 4,
                "max_visible_shots": 6,
                "shot_quadrant": "custom",
                "shot_direction": "down",
                "custom_x": 0.12,
                "custom_y": 0.18,
                "timer_x": 0.2,
                "timer_y": 0.08,
                "draw_x": 0.84,
                "draw_y": 0.1,
                "score_x": 0.82,
                "score_y": 0.2,
                "bubble_width": 96,
                "bubble_height": 42,
                "font_family": "Verdana",
                "font_size": 18,
                "font_bold": False,
                "font_italic": True,
                "show_timer": False,
                "show_draw": True,
                "show_shots": True,
                "show_score": False,
                "custom_box_enabled": True,
                "custom_box_mode": "imported_summary",
                "custom_box_text": "Classifier ready",
                "custom_box_quadrant": "middle_middle",
                "custom_box_x": 0.5,
                "custom_box_y": 0.5,
            },
        )

        assert state["project"]["overlay"]["position"] == "top"
        assert state["project"]["overlay"]["badge_size"] == "XL"
        assert state["project"]["overlay"]["timer_badge"]["background_color"] == "#123456"
        assert state["project"]["overlay"]["timer_badge"]["text_color"] == "#abcdef"
        assert state["project"]["overlay"]["timer_badge"]["opacity"] == 0.55
        assert state["project"]["overlay"]["scoring_colors"]["A"] == "#00ff00"
        assert state["project"]["overlay"]["scoring_colors"]["PE"] == "#112233"
        assert state["project"]["overlay"]["style_type"] == "rounded"
        assert state["project"]["overlay"]["spacing"] == 6
        assert state["project"]["overlay"]["margin"] == 4
        assert state["project"]["overlay"]["max_visible_shots"] == 6
        assert state["project"]["overlay"]["shot_quadrant"] == "custom"
        assert state["project"]["overlay"]["shot_direction"] == "down"
        assert state["project"]["overlay"]["custom_x"] == 0.12
        assert state["project"]["overlay"]["custom_y"] == 0.18
        assert state["project"]["overlay"]["timer_x"] == 0.2
        assert state["project"]["overlay"]["timer_y"] == 0.08
        assert state["project"]["overlay"]["draw_x"] == 0.84
        assert state["project"]["overlay"]["draw_y"] == 0.1
        assert state["project"]["overlay"]["score_x"] == 0.82
        assert state["project"]["overlay"]["score_y"] == 0.2
        assert state["project"]["overlay"]["bubble_width"] == 96
        assert state["project"]["overlay"]["bubble_height"] == 42
        assert state["project"]["overlay"]["font_family"] == "Verdana"
        assert state["project"]["overlay"]["font_size"] == 18
        assert state["project"]["overlay"]["font_bold"] is False
        assert state["project"]["overlay"]["font_italic"] is True
        assert state["project"]["overlay"]["show_timer"] is False
        assert state["project"]["overlay"]["show_score"] is False
        assert state["project"]["overlay"]["custom_box_enabled"] is True
        assert state["project"]["overlay"]["custom_box_mode"] == "imported_summary"
        assert state["project"]["overlay"]["custom_box_text"] == "Classifier ready"
        assert state["project"]["overlay"]["custom_box_quadrant"] == "custom"
        assert state["project"]["overlay"]["custom_box_x"] == 0.5
        assert state["project"]["overlay"]["custom_box_y"] == 0.5

        state = _post_json(f"{server.url}api/scoring/profile", {"ruleset": "uspsa_major"})
        assert state["project"]["scoring"]["ruleset"] == "uspsa_major"
        assert state["project"]["scoring"]["point_map"]["C"] == 4
        assert "penalty_fields" in state["scoring_summary"]
        assert any(item["key"] == "PE" for item in state["scoring_summary"]["scoring_color_options"])
        assert not any("|" in item["key"] for item in state["scoring_summary"]["scoring_color_options"])

        state = _post_json(
            f"{server.url}api/scoring",
            {"penalties": 1.5, "penalty_counts": {"procedural_errors": 2}},
        )
        assert state["project"]["scoring"]["penalty_counts"]["procedural_errors"] == 2
        assert state["project"]["scoring"]["penalties"] == 1.5
        assert state["scoring_summary"]["field_penalties"] == 20

        state = _post_json(f"{server.url}api/scoring/position", {"shot_id": shot_id, "x_norm": 0.2, "y_norm": 0.8})
        assert state["project"]["analysis"]["shots"][0]["score"]["x_norm"] == 0.2
        assert state["project"]["analysis"]["shots"][0]["score"]["y_norm"] == 0.8
    finally:
        server.shutdown()


def test_browser_control_api_rejects_invalid_overlay_badge_name(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                f"{server.url}api/overlay",
                {
                    "styles": {
                        "review_badge": {
                            "background_color": "#000000",
                            "text_color": "#ffffff",
                            "opacity": 0.8,
                        }
                    }
                },
            )

        assert exc_info.value.code == 400
        error_payload = json.loads(exc_info.value.read().decode("utf-8"))
        assert error_payload["error"] == "Unknown badge style: review_badge"
    finally:
        server.shutdown()


def test_browser_control_api_export_requires_output_file_to_exist(
    synthetic_video_factory,
    tmp_path: Path,
    monkeypatch,
) -> None:
    controller = ProjectController()
    missing_output = tmp_path / "missing-export.mp4"

    def fake_export_project(*args, **kwargs):
        return missing_output

    monkeypatch.setattr(browser_server_module, "export_project", fake_export_project)
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory())
        _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})

        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _post_json(
                f"{server.url}api/export",
                {"path": str(tmp_path / "requested-export.mp4"), "preset": "source_mp4"},
            )

        assert exc_info.value.code == 400
        error_payload = json.loads(exc_info.value.read().decode("utf-8"))
        assert error_payload["error"] == "Export did not produce an output file."
    finally:
        server.shutdown()


def test_browser_control_api_updates_export_presets_and_variables() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _get_json(f"{server.url}api/state")
        preset_ids = {preset["id"] for preset in state["export_presets"]}
        assert "universal_vertical" in preset_ids
        assert "youtube_long_4k" in preset_ids

        state = _post_json(f"{server.url}api/export/preset", {"preset": "universal_vertical"})
        assert state["project"]["export"]["preset"] == "universal_vertical"
        assert state["project"]["export"]["target_width"] == 1080
        assert state["project"]["export"]["target_height"] == 1920
        assert state["project"]["export"]["video_bitrate_mbps"] == 20.0

        state = _post_json(
            f"{server.url}api/export/settings",
            {
                "target_width": 720,
                "target_height": 1280,
                "frame_rate": "60",
                "video_codec": "h264",
                "video_bitrate_mbps": 18,
                "audio_codec": "aac",
                "audio_sample_rate": 48000,
                "audio_bitrate_kbps": 320,
                "color_space": "bt709_sdr",
                "two_pass": True,
                "ffmpeg_preset": "slow",
            },
        )
        assert state["project"]["export"]["preset"] == "custom"
        assert state["project"]["export"]["target_width"] == 720
        assert state["project"]["export"]["target_height"] == 1280
        assert state["project"]["export"]["frame_rate"] == "60"
        assert state["project"]["export"]["two_pass"] is True
    finally:
        server.shutdown()


def test_browser_control_api_exports_mp4_and_exposes_ffmpeg_log(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory(resolution=(320, 180)))
        output_path = tmp_path / "browser-export.mp4"

        _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        _post_json(
            f"{server.url}api/export/settings",
            {
                "target_width": 160,
                "target_height": 90,
                "frame_rate": "30",
                "video_codec": "h264",
                "video_bitrate_mbps": 1,
                "audio_codec": "aac",
                "audio_sample_rate": 48000,
                "audio_bitrate_kbps": 128,
                "color_space": "bt709_sdr",
                "two_pass": False,
                "ffmpeg_preset": "ultrafast",
            },
        )
        state = _post_json(f"{server.url}api/export", {"path": str(output_path)})

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert state["project"]["export"]["output_path"] == str(output_path)
        assert "Encoder command:" in state["project"]["export"]["last_log"]
        assert state["project"]["export"]["last_error"] is None
    finally:
        server.shutdown()


def test_browser_control_api_export_uses_request_payload_overrides(synthetic_video_factory, tmp_path: Path) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        video_path = Path(synthetic_video_factory(resolution=(320, 180)))
        output_path = tmp_path / "browser-export-custom.mov"

        _post_json(f"{server.url}api/import/primary", {"path": str(video_path)})
        _post_json(f"{server.url}api/export/preset", {"preset": "youtube_long_4k"})

        state = _post_json(
            f"{server.url}api/export",
            {
                "path": str(output_path),
                "preset": "custom",
                "quality": "medium",
                "aspect_ratio": "1:1",
                "target_width": 120,
                "target_height": 120,
                "frame_rate": "30",
                "video_codec": "hevc",
                "video_bitrate_mbps": 1,
                "audio_codec": "aac",
                "audio_sample_rate": 44100,
                "audio_bitrate_kbps": 96,
                "color_space": "bt709_sdr",
                "two_pass": False,
                "ffmpeg_preset": "ultrafast",
            },
        )

        assert output_path.exists()
        assert output_path.stat().st_size > 0
        assert state["project"]["export"]["preset"] == "custom"
        assert state["project"]["export"]["quality"] == "medium"
        assert state["project"]["export"]["aspect_ratio"] == "1:1"
        assert state["project"]["export"]["target_width"] == 120
        assert state["project"]["export"]["target_height"] == 120
        assert state["project"]["export"]["frame_rate"] == "30"
        assert state["project"]["export"]["video_codec"] == "hevc"
        assert state["project"]["export"]["video_bitrate_mbps"] == 1.0
        assert state["project"]["export"]["audio_sample_rate"] == 44100
        assert state["project"]["export"]["audio_bitrate_kbps"] == 96
        assert state["project"]["export"]["ffmpeg_preset"] == "ultrafast"
        assert "Encoder command:" in state["project"]["export"]["last_log"]
        assert state["project"]["export"]["last_error"] is None
    finally:
        server.shutdown()


def test_browser_control_api_syncs_and_swaps_secondary_video(synthetic_video_factory) -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        primary = Path(synthetic_video_factory(name="primary", beep_ms=400))
        secondary = Path(synthetic_video_factory(name="secondary", beep_ms=650))

        _post_json(f"{server.url}api/import/primary", {"path": str(primary)})
        state = _post_json(f"{server.url}api/import/secondary", {"path": str(secondary)})

        assert state["project"]["merge"]["enabled"] is True
        assert state["project"]["analysis"]["beep_time_ms_secondary"] is not None

        state = _post_json(f"{server.url}api/merge", {"layout": "pip", "pip_size_percent": 50, "pip_x": 0.25, "pip_y": 0.75})
        assert state["project"]["merge"]["layout"] == "pip"
        assert state["project"]["merge"]["pip_size_percent"] == 50
        assert state["project"]["merge"]["pip_x"] == 0.25
        assert state["project"]["merge"]["pip_y"] == 0.75

        merge_source_id = state["project"]["merge_sources"][0]["id"]
        state = _post_json(
            f"{server.url}api/merge/source",
            {"source_id": merge_source_id, "pip_size_percent": 62, "pip_x": 0.1, "pip_y": 0.9},
        )
        assert state["project"]["merge_sources"][0]["pip_size_percent"] == 62
        assert state["project"]["merge_sources"][0]["pip_x"] == 0.1
        assert state["project"]["merge_sources"][0]["pip_y"] == 0.9

        initial_source_offset = state["project"]["merge_sources"][0]["sync_offset_ms"]
        state = _post_json(
            f"{server.url}api/merge/source",
            {"source_id": merge_source_id, "sync_delta_ms": 10},
        )
        assert state["project"]["merge_sources"][0]["sync_offset_ms"] == initial_source_offset + 10
        assert state["project"]["analysis"]["sync_offset_ms"] == initial_source_offset + 10

        state = _post_json(
            f"{server.url}api/merge/source",
            {"source_id": merge_source_id, "sync_offset_ms": -25},
        )
        assert state["project"]["merge_sources"][0]["sync_offset_ms"] == -25
        assert state["project"]["analysis"]["sync_offset_ms"] == -25

        initial_offset = state["project"]["analysis"]["sync_offset_ms"]
        state = _post_json(f"{server.url}api/sync", {"delta_ms": 10})
        assert state["project"]["analysis"]["sync_offset_ms"] == initial_offset + 10

        state = _post_json(f"{server.url}api/swap", {})

        assert state["project"]["primary_video"]["path"] == str(secondary)
        assert state["project"]["secondary_video"]["path"] == str(primary)
    finally:
        server.shutdown()
