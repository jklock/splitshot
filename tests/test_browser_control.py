from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import urllib.request
from pathlib import Path

from splitshot.browser.server import (
    BrowserControlServer,
    QuietThreadingHTTPServer,
    is_expected_disconnect_error,
)
from splitshot.browser.state import browser_state
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
        assert "http.get" in log_text
        assert "browser.activity" in log_text
        assert "test.click" in log_text
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
    assert len(payload["split_rows"]) == 3
    assert len(payload["timing_segments"]) == 3
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
            {"shot_id": first_shot_id, "letter": "C"},
        )
        assert state["project"]["analysis"]["shots"][0]["score"]["letter"] == "C"

        state = _get_json(f"{server.url}api/state")
        assert state["metrics"]["total_shots"] == 3
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
                "scoring_colors": {"A": "#00ff00"},
            },
        )

        assert state["project"]["overlay"]["position"] == "top"
        assert state["project"]["overlay"]["badge_size"] == "XL"
        assert state["project"]["overlay"]["timer_badge"]["background_color"] == "#123456"
        assert state["project"]["overlay"]["timer_badge"]["text_color"] == "#abcdef"
        assert state["project"]["overlay"]["timer_badge"]["opacity"] == 0.55
        assert state["project"]["overlay"]["scoring_colors"]["A"] == "#00ff00"

        state = _post_json(f"{server.url}api/scoring/profile", {"ruleset": "uspsa_major"})
        assert state["project"]["scoring"]["ruleset"] == "uspsa_major"
        assert state["project"]["scoring"]["point_map"]["C"] == 4

        state = _post_json(f"{server.url}api/scoring/position", {"shot_id": shot_id, "x_norm": 0.2, "y_norm": 0.8})
        assert state["project"]["analysis"]["shots"][0]["score"]["x_norm"] == 0.2
        assert state["project"]["analysis"]["shots"][0]["score"]["y_norm"] == 0.8
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

        initial_offset = state["project"]["analysis"]["sync_offset_ms"]
        state = _post_json(f"{server.url}api/sync", {"delta_ms": 10})
        assert state["project"]["analysis"]["sync_offset_ms"] == initial_offset + 10

        state = _post_json(f"{server.url}api/swap", {})

        assert state["project"]["primary_video"]["path"] == str(secondary)
        assert state["project"]["secondary_video"]["path"] == str(primary)
    finally:
        server.shutdown()
