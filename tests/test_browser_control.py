from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.error
import urllib.request
from pathlib import Path

import pytest
import splitshot.browser.server as browser_server_module

from splitshot.browser.activity import ActivityLogger
from splitshot.browser.server import (
    BrowserControlServer,
    QuietThreadingHTTPServer,
    display_name_for_path,
    is_expected_disconnect_error,
)
from splitshot.browser.state import browser_state
from splitshot.domain.models import OverlayPosition, Project
from splitshot.ui.controller import ProjectController


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


def test_browser_overlay_api_supports_repeatable_text_boxes() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    server.start_background(open_browser=False)
    try:
        state = _post_json(
            f"{server.url}api/overlay",
            {
                "text_boxes": [
                    {
                        "id": "manual-box",
                        "enabled": True,
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
        assert len(boxes) == 2
        assert boxes[0]["text"] == "Session summary"
        assert boxes[0]["quadrant"] == "top_left"
        assert boxes[1]["source"] == "imported_summary"
        assert boxes[1]["quadrant"] == "custom"
        assert boxes[1]["x"] == pytest.approx(0.5)
        assert boxes[1]["y"] == pytest.approx(0.4)
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
    assert payload["split_rows"][0]["row_type"] == "interval"
    assert payload["split_rows"][0]["label"] == "Start -> Shot 1"
    assert payload["split_rows"][0]["actions"][0]["label"] == "Draw"
    assert payload["split_rows"][1]["split_ms"] is not None
    assert payload["timing_segments"][0]["label"] == "Draw"
    assert payload["timing_segments"][0]["segment_ms"] == payload["metrics"]["draw_ms"]
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
    examples_dir = Path(__file__).resolve().parent.parent / "example_data" / "USPSA"
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
        assert state["scoring_summary"]["imported_overlay_text"] == "Official\nRaw 23.24\nPoints 101\nHF 4.3460"
        assert state["scoring_summary"]["hit_factor"] == pytest.approx(101.0 / 23.24)
        assert state["scoring_summary"]["display_value"] == "4.35"
    finally:
        server.shutdown()


def test_browser_control_api_infers_practiscore_results_without_manual_context() -> None:
    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0)
    examples_dir = Path(__file__).resolve().parent.parent / "example_data" / "USPSA"
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
    examples_dir = Path(__file__).resolve().parent.parent / "example_data" / "IDPA"
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
        assert state["status"] == "Deleted the saved project bundle."
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

    def fake_ingest(path: str) -> None:
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


def test_browser_path_dialog_endpoint_supports_project_open_and_save(tmp_path) -> None:
    open_path = tmp_path / "existing.ssproj" / "project.json"
    save_path = tmp_path / "new.ssproj"
    calls: list[tuple[str, str | None]] = []

    def fake_path_chooser(kind: str, current: str | None) -> str:
        calls.append((kind, current))
        return str(open_path if kind == "project_open" else save_path)

    controller = ProjectController()
    server = BrowserControlServer(controller=controller, port=0, path_chooser=fake_path_chooser)
    server.start_background(open_browser=False)
    try:
        assert _post_json(
            f"{server.url}api/dialog/path",
            {"kind": "project_open", "current": "/tmp/current.ssproj"},
        ) == {"path": str(open_path)}
        assert _post_json(
            f"{server.url}api/dialog/path",
            {"kind": "project_save", "current": ""},
        ) == {"path": str(save_path)}
        assert calls == [("project_open", "/tmp/current.ssproj"), ("project_save", None)]
    finally:
        server.shutdown()


def test_choose_local_path_macos_prompts_for_project_open_file(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        captured["script"] = command[2]

        class Result:
            returncode = 0
            stdout = "/Users/klock/splitshot/review.ssproj/project.json\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(browser_server_module.subprocess, "run", fake_run)

    chosen = browser_server_module.choose_local_path_macos("project_open")

    assert chosen == "/Users/klock/splitshot/review.ssproj/project.json"
    assert captured["command"] == ["osascript", "-e", captured["script"]]
    script = str(captured["script"])
    assert "choose file with prompt" in script
    assert "Choose SplitShot project.json file" in script
    assert "choose folder" not in script


def test_choose_local_path_macos_defaults_new_project_save_name(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        captured["script"] = command[2]

        class Result:
            returncode = 0
            stdout = "/Users/klock/splitshot/project.ssproj\n"
            stderr = ""

        return Result()

    monkeypatch.setattr(browser_server_module.subprocess, "run", fake_run)

    chosen = browser_server_module.choose_local_path_macos("project_save")

    assert chosen == "/Users/klock/splitshot/project.ssproj"
    assert captured["command"] == ["osascript", "-e", captured["script"]]
    script = str(captured["script"])
    assert 'Choose SplitShot project bundle' in script
    assert 'default name "project.ssproj"' in script
    assert 'output.mp4' not in script


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

        reopened = _post_json(f"{server.url}api/project/open", {"path": str(project_path / "project.json")})
        assert reopened["project"]["path"] == str(project_path)
        assert reopened["media"]["primary_available"] is True
        assert reopened["project"]["primary_video"]["path"] == str(video_path)
        assert controller.project_path == project_path
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
        assert bundled_primary.parent == project_path / "media"
        assert bundled_secondary.parent == project_path / "media"
    finally:
        server.shutdown()

    reopened = ProjectController()
    reopened.open_project(str(project_path))

    assert Path(reopened.project.primary_video.path).exists()
    assert Path(reopened.project.primary_video.path).parent == project_path / "media"
    assert reopened.project.secondary_video is not None
    assert Path(reopened.project.secondary_video.path).exists()
    assert Path(reopened.project.secondary_video.path).parent == project_path / "media"


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

    def fake_ingest(path: str) -> None:
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
