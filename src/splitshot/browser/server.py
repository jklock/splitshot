from __future__ import annotations

import json
import mimetypes
import re
import sys
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable
from urllib.parse import urlparse
from uuid import uuid4

from splitshot.browser.state import browser_state
from splitshot.domain.models import (
    AspectRatio,
    BadgeSize,
    ExportQuality,
    MergeLayout,
    OverlayPosition,
    PipSize,
    ScoreLetter,
)
from splitshot.export.pipeline import export_project
from splitshot.ui.controller import ProjectController


EXPECTED_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)


def is_expected_disconnect_error(exc: BaseException | None) -> bool:
    return isinstance(exc, EXPECTED_DISCONNECT_ERRORS)


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    def handle_error(self, request: Any, client_address: tuple[str, int]) -> None:
        if is_expected_disconnect_error(sys.exc_info()[1]):
            return
        super().handle_error(request, client_address)


class BrowserControlServer:
    def __init__(
        self,
        controller: ProjectController | None = None,
        host: str = "127.0.0.1",
        port: int = 8765,
    ) -> None:
        self.controller = controller or ProjectController()
        self.host = host
        self.port = port
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._session_dir = TemporaryDirectory(prefix="splitshot-browser-")
        self._session_path = Path(self._session_dir.name)

    @property
    def url(self) -> str:
        if self._httpd is not None:
            host, port = self._httpd.server_address[:2]
            return f"http://{host}:{port}/"
        return f"http://{self.host}:{self.port}/"

    def serve_forever(self, open_browser: bool = True) -> None:
        self._httpd = self._build_httpd()
        if open_browser:
            webbrowser.open(self.url)
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nSplitShot browser control stopped.")
        finally:
            self._httpd.server_close()
            self._session_dir.cleanup()

    def start_background(self, open_browser: bool = False) -> None:
        self._httpd = self._build_httpd()
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        if open_browser:
            webbrowser.open(self.url)

    def shutdown(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._session_dir.cleanup()

    def _build_httpd(self) -> ThreadingHTTPServer:
        return QuietThreadingHTTPServer((self.host, self.port), self._handler())

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        controller = self.controller
        session_path = self._session_path

        class Handler(BaseHTTPRequestHandler):
            server_version = "SplitShotBrowser/1.0"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                request_path = urlparse(self.path).path
                if request_path in {"/", "/index.html"}:
                    self._send_static("index.html", "text/html; charset=utf-8")
                    return
                if request_path.startswith("/static/"):
                    self._send_static(request_path.removeprefix("/static/"))
                    return
                if request_path == "/api/state":
                    self._send_json(browser_state(controller.project, controller.status_message))
                    return
                if request_path == "/media/primary":
                    self._send_media(Path(controller.project.primary_video.path))
                    return
                if request_path == "/media/secondary":
                    if controller.project.secondary_video is None:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._send_media(Path(controller.project.secondary_video.path))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802
                if self.path == "/api/files/primary":
                    self._import_primary_file()
                    return
                if self.path == "/api/files/secondary":
                    self._import_secondary_file()
                    return
                routes: dict[str, Callable[[dict[str, Any]], None]] = {
                    "/api/project/new": self._new_project,
                    "/api/project/open": self._open_project,
                    "/api/project/save": self._save_project,
                    "/api/project/delete": self._delete_project,
                    "/api/import/primary": self._import_primary,
                    "/api/import/secondary": self._import_secondary,
                    "/api/analysis/threshold": self._set_threshold,
                    "/api/beep": self._set_beep,
                    "/api/shots/add": self._add_shot,
                    "/api/shots/move": self._move_shot,
                    "/api/shots/delete": self._delete_shot,
                    "/api/shots/select": self._select_shot,
                    "/api/scoring": self._set_scoring,
                    "/api/scoring/profile": self._set_scoring_profile,
                    "/api/scoring/score": self._assign_score,
                    "/api/scoring/position": self._set_score_position,
                    "/api/overlay": self._set_overlay,
                    "/api/merge": self._set_merge,
                    "/api/sync": self._set_sync,
                    "/api/swap": self._swap_videos,
                    "/api/layout": self._set_layout,
                    "/api/export": self._export_project,
                }
                route = routes.get(self.path)
                if route is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    payload = self._read_json()
                    route(payload)
                    self._send_json(browser_state(controller.project, controller.status_message))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _read_json(self) -> dict[str, Any]:
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length == 0:
                    return {}
                body = self.rfile.read(length).decode("utf-8")
                return json.loads(body)

            def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_static(self, name: str, content_type: str | None = None) -> None:
                safe_name = name.replace("\\", "/").lstrip("/")
                if ".." in safe_name:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                package_root = resources.files("splitshot.browser.static")
                target = package_root / safe_name
                if not target.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = target.read_bytes()
                guessed = content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", guessed)
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def _send_media(self, path: Path) -> None:
                if not path.exists() or not path.is_file():
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                size = path.stat().st_size
                start = 0
                end = size - 1
                status = HTTPStatus.OK
                range_header = self.headers.get("Range")
                if range_header:
                    match = re.match(r"bytes=(\d*)-(\d*)", range_header)
                    if match:
                        if match.group(1):
                            start = int(match.group(1))
                        if match.group(2):
                            end = int(match.group(2))
                        end = min(end, size - 1)
                        status = HTTPStatus.PARTIAL_CONTENT
                if start > end:
                    self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                    return
                content_length = end - start + 1
                self.send_response(status)
                self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "video/mp4")
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Content-Length", str(content_length))
                if status == HTTPStatus.PARTIAL_CONTENT:
                    self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                self.end_headers()
                with path.open("rb") as media_file:
                    media_file.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = media_file.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except EXPECTED_DISCONNECT_ERRORS:
                            return
                        remaining -= len(chunk)

            def _save_uploaded_file(self) -> Path:
                content_type = self.headers.get("Content-Type", "")
                match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
                if match is None:
                    raise ValueError("Multipart boundary is required")
                boundary = match.group("boundary").strip().strip('"').encode("utf-8")
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    raise ValueError("Video file is required")
                body = self.rfile.read(length)
                part_boundary = b"--" + boundary
                for raw_part in body.split(part_boundary):
                    part = raw_part.strip(b"\r\n")
                    if not part or part == b"--":
                        continue
                    headers_blob, separator, file_bytes = part.partition(b"\r\n\r\n")
                    if not separator:
                        continue
                    disposition = next(
                        (
                            line.decode("utf-8", errors="replace")
                            for line in headers_blob.split(b"\r\n")
                            if line.lower().startswith(b"content-disposition:")
                        ),
                        "",
                    )
                    if 'name="file"' not in disposition or "filename=" not in disposition:
                        continue
                    filename_match = re.search(r'filename="(?P<filename>[^"]*)"', disposition)
                    filename = filename_match.group("filename") if filename_match else "video.mp4"
                    safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._")
                    if not safe_name:
                        safe_name = "video.mp4"
                    if file_bytes.endswith(b"\r\n"):
                        file_bytes = file_bytes[:-2]
                    if file_bytes.endswith(b"--"):
                        file_bytes = file_bytes[:-2]
                    target = session_path / f"{uuid4().hex}_{safe_name}"
                    target.write_bytes(file_bytes)
                    return target
                raise ValueError("Multipart request must contain a file field named 'file'")

            def _import_primary_file(self) -> None:
                try:
                    path = self._save_uploaded_file()
                    controller.ingest_primary_video(str(path))
                    self._send_json(browser_state(controller.project, controller.status_message))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _import_secondary_file(self) -> None:
                try:
                    path = self._save_uploaded_file()
                    controller.ingest_secondary_video(str(path))
                    self._send_json(browser_state(controller.project, controller.status_message))
                except Exception as exc:  # noqa: BLE001
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _new_project(self, payload: dict[str, Any]) -> None:
                controller.new_project()

            def _open_project(self, payload: dict[str, Any]) -> None:
                controller.open_project(str(payload["path"]))

            def _save_project(self, payload: dict[str, Any]) -> None:
                target = payload.get("path") or (
                    None if controller.project_path is None else str(controller.project_path)
                )
                if not target:
                    raise ValueError("Project path is required")
                controller.save_project(str(target))

            def _delete_project(self, payload: dict[str, Any]) -> None:
                controller.delete_current_project()

            def _import_primary(self, payload: dict[str, Any]) -> None:
                controller.ingest_primary_video(str(payload["path"]))

            def _import_secondary(self, payload: dict[str, Any]) -> None:
                controller.ingest_secondary_video(str(payload["path"]))

            def _set_threshold(self, payload: dict[str, Any]) -> None:
                controller.set_detection_threshold(float(payload["threshold"]))

            def _set_beep(self, payload: dict[str, Any]) -> None:
                controller.set_beep_time(int(payload["time_ms"]))

            def _add_shot(self, payload: dict[str, Any]) -> None:
                controller.add_shot(int(payload["time_ms"]))

            def _move_shot(self, payload: dict[str, Any]) -> None:
                controller.move_shot(str(payload["shot_id"]), int(payload["time_ms"]))

            def _delete_shot(self, payload: dict[str, Any]) -> None:
                controller.delete_shot(str(payload["shot_id"]))

            def _select_shot(self, payload: dict[str, Any]) -> None:
                shot_id = payload.get("shot_id")
                controller.select_shot(None if shot_id in {"", None} else str(shot_id))

            def _set_scoring(self, payload: dict[str, Any]) -> None:
                if "enabled" in payload:
                    controller.set_scoring_enabled(bool(payload["enabled"]))
                if "penalties" in payload:
                    controller.set_penalties(int(payload["penalties"]))

            def _set_scoring_profile(self, payload: dict[str, Any]) -> None:
                controller.set_scoring_preset(str(payload["ruleset"]))

            def _assign_score(self, payload: dict[str, Any]) -> None:
                controller.assign_score(str(payload["shot_id"]), ScoreLetter(str(payload["letter"])))

            def _set_score_position(self, payload: dict[str, Any]) -> None:
                controller.set_score_position(
                    str(payload["shot_id"]),
                    float(payload["x_norm"]),
                    float(payload["y_norm"]),
                )

            def _set_overlay(self, payload: dict[str, Any]) -> None:
                if "position" in payload:
                    controller.set_overlay_position(OverlayPosition(str(payload["position"])))
                if "badge_size" in payload:
                    controller.set_badge_size(BadgeSize(str(payload["badge_size"])))
                styles = payload.get("styles", {})
                for badge_name, style in styles.items():
                    controller.set_overlay_badge_style(
                        str(badge_name),
                        background_color=style.get("background_color"),
                        text_color=style.get("text_color"),
                        opacity=None if style.get("opacity") is None else float(style["opacity"]),
                    )
                for letter, color in payload.get("scoring_colors", {}).items():
                    controller.set_scoring_color(ScoreLetter(str(letter)), str(color))

            def _set_merge(self, payload: dict[str, Any]) -> None:
                if "enabled" in payload:
                    controller.set_merge_enabled(bool(payload["enabled"]))
                if "layout" in payload:
                    controller.set_merge_layout(MergeLayout(str(payload["layout"])))
                if "pip_size" in payload:
                    controller.set_pip_size(PipSize(str(payload["pip_size"])))

            def _set_sync(self, payload: dict[str, Any]) -> None:
                if "offset_ms" in payload:
                    controller.set_sync_offset(int(payload["offset_ms"]))
                elif "delta_ms" in payload:
                    controller.adjust_sync_offset(int(payload["delta_ms"]))

            def _swap_videos(self, payload: dict[str, Any]) -> None:
                controller.swap_videos()

            def _set_layout(self, payload: dict[str, Any]) -> None:
                project = controller.project
                if "aspect_ratio" in payload:
                    project.export.aspect_ratio = AspectRatio(str(payload["aspect_ratio"]))
                if "quality" in payload:
                    controller.set_export_quality(ExportQuality(str(payload["quality"])))
                if "crop_center_x" in payload:
                    project.export.crop_center_x = float(payload["crop_center_x"])
                if "crop_center_y" in payload:
                    project.export.crop_center_y = float(payload["crop_center_y"])
                project.touch()
                controller.project_changed.emit()

            def _export_project(self, payload: dict[str, Any]) -> None:
                output_path = Path(str(payload["path"]))
                controller.project.export.output_path = str(output_path)
                export_project(controller.project, output_path)
                controller.project.touch()
                controller.status_message = f"Exported MP4 to {output_path}."

        return Handler
