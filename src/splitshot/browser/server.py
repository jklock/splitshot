from __future__ import annotations

import json
import mimetypes
import re
import subprocess
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

from splitshot.browser.activity import ActivityLogger
from splitshot.browser.state import browser_state
from splitshot.domain.models import (
    BadgeSize,
    MergeLayout,
    OverlayPosition,
    PipSize,
    Project,
    ScoreLetter,
)
from splitshot.export.pipeline import export_project, prepare_export_runtime
from splitshot.persistence.projects import PROJECT_FILENAME
from splitshot.ui.controller import ProjectController


EXPECTED_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
PathChooser = Callable[[str, str | None], str | None]
COMMON_VIDEO_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.avi *.wmv *.webm *.mkv *.mpg *.mpeg *.mts *.m2ts"
COMMON_EXPORT_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.mkv"


def is_expected_disconnect_error(exc: BaseException | None) -> bool:
    return isinstance(exc, EXPECTED_DISCONNECT_ERRORS)


def choose_local_path(kind: str, current: str | None = None) -> str | None:
    if sys.platform == "darwin":
        return choose_local_path_macos(kind, current)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Native file browser is not available in this Python environment.") from exc

    initial_dir = str(Path(current).expanduser().parent) if current else str(Path.home())
    root = tk.Tk()
    root.withdraw()
    try:
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        if kind in {"primary", "secondary"}:
            return filedialog.askopenfilename(
                title="Choose stage video" if kind == "primary" else "Choose secondary angle video",
                initialdir=initial_dir,
                filetypes=[
                    ("Video files", COMMON_VIDEO_FILE_PATTERNS),
                    ("All files", "*.*"),
                ],
            )
        if kind in {"project", "project_save"}:
            return filedialog.asksaveasfilename(
                title="Choose SplitShot project bundle",
                initialdir=initial_dir,
                defaultextension=".ssproj",
                filetypes=[("SplitShot project", "*.ssproj"), ("All files", "*.*")],
            )
        if kind == "project_open":
            return filedialog.askopenfilename(
                title="Choose SplitShot project.json file",
                initialdir=initial_dir,
                filetypes=[
                    ("SplitShot project file", PROJECT_FILENAME),
                    ("JSON files", "*.json"),
                    ("All files", "*.*"),
                ],
            )
        if kind == "export":
            return filedialog.asksaveasfilename(
                title="Choose video export path",
                initialdir=initial_dir,
                defaultextension=".mp4",
                filetypes=[("Video files", COMMON_EXPORT_FILE_PATTERNS), ("All files", "*.*")],
            )
        raise ValueError(f"Unsupported path chooser kind: {kind}")
    finally:
        root.destroy()


def choose_local_path_macos(kind: str, current: str | None = None) -> str | None:
    current_path = Path(current).expanduser() if current else None
    default_dir = (current_path.parent if current_path else Path.home()).resolve()
    default_name = current_path.name if current_path and current_path.name else (
        "project.ssproj" if kind in {"project", "project_save"} else "output.mp4"
    )
    if kind in {"primary", "secondary"}:
        prompt = "Choose stage video" if kind == "primary" else "Choose secondary angle video"
        script = "\n".join(
            [
                f"set chosenFile to choose file with prompt {_applescript_string(prompt)} "
                f"default location POSIX file {_applescript_string(str(default_dir))}",
                "POSIX path of chosenFile",
            ]
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Native file browser failed.")
    if kind == "project_open":
        script = "\n".join(
            [
                f"set chosenFile to choose file with prompt {_applescript_string('Choose SplitShot project.json file')} "
                f"default location POSIX file {_applescript_string(str(default_dir))}",
                "POSIX path of chosenFile",
            ]
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Native file browser failed.")
    if kind in {"project", "project_save"}:
        prompt = "Choose SplitShot project bundle"
    elif kind == "export":
        prompt = "Choose video export path"
    else:
        raise ValueError(f"Unsupported path chooser kind: {kind}")

    script = "\n".join(
        [
            f"set chosenFile to choose file name with prompt {_applescript_string(prompt)} "
            f"default name {_applescript_string(default_name)} "
            f"default location POSIX file {_applescript_string(str(default_dir))}",
            "POSIX path of chosenFile",
        ]
    )
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
    if result.returncode == 0:
        return result.stdout.strip()
    if "User canceled" in result.stderr:
        return None
    raise RuntimeError(result.stderr.strip() or "Native file browser failed.")


def _applescript_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def display_name_for_path(path: str, fallback: str) -> str:
    if not path:
        return fallback
    return re.sub(r"^[A-Fa-f0-9]{32}_", "", Path(path).name)


def _payload_matches_export_state(project: Project, payload: dict[str, Any]) -> bool:
    export = project.export
    current_values: dict[str, object] = {
        "quality": export.quality.value,
        "aspect_ratio": export.aspect_ratio.value,
        "target_width": export.target_width,
        "target_height": export.target_height,
        "frame_rate": export.frame_rate.value,
        "video_codec": export.video_codec.value,
        "video_bitrate_mbps": export.video_bitrate_mbps,
        "audio_codec": export.audio_codec.value,
        "audio_sample_rate": export.audio_sample_rate,
        "audio_bitrate_kbps": export.audio_bitrate_kbps,
        "color_space": export.color_space.value,
        "two_pass": export.two_pass,
        "ffmpeg_preset": export.ffmpeg_preset,
    }
    for key, current in current_values.items():
        if key not in payload:
            continue
        value = payload[key]
        if key in {"target_width", "target_height"}:
            normalized = None if value in {"", None} else max(2, int(value))
        elif key == "video_bitrate_mbps":
            normalized = max(0.1, float(value))
        elif key == "audio_sample_rate":
            normalized = max(8000, int(value))
        elif key == "audio_bitrate_kbps":
            normalized = max(32, int(value))
        elif key == "two_pass":
            normalized = bool(value)
        else:
            normalized = str(value)
        if normalized != current:
            return False
    return True


def _sync_export_payload(controller: ProjectController, payload: dict[str, Any]) -> None:
    selected_preset = str(payload.get("preset") or controller.project.export.preset.value)
    controller.apply_export_preset(selected_preset)
    if selected_preset == "custom" or not _payload_matches_export_state(controller.project, payload):
        controller.set_export_settings(payload)


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
        log_dir: str | Path | None = None,
        log_level: str = "off",
        path_chooser: PathChooser | None = None,
    ) -> None:
        self.controller = controller or ProjectController()
        self.host = host
        self.port = port
        self.activity = ActivityLogger(log_dir, console_level=log_level)
        self.path_chooser = path_chooser or choose_local_path
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._controller_lock = threading.Lock()
        self._session_dir = TemporaryDirectory(prefix="splitshot-browser-")
        self._session_path = Path(self._session_dir.name)
        self._display_names: dict[str, str] = {}
        prepare_export_runtime()
        self.activity.log("server.initialized", host=host, port=port, log_path=str(self.activity.path))

    @property
    def url(self) -> str:
        if self._httpd is not None:
            host, port = self._httpd.server_address[:2]
            return f"http://{host}:{port}/"
        return f"http://{self.host}:{self.port}/"

    def serve_forever(self, open_browser: bool = True) -> None:
        self._httpd = self._build_httpd()
        self.activity.log("server.serve_forever", url=self.url, open_browser=open_browser)
        if open_browser:
            webbrowser.open(self.url)
        try:
            self._httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nSplitShot browser control stopped.")
        finally:
            self.activity.log("server.stopping", url=self.url)
            self._httpd.server_close()
            self._session_dir.cleanup()

    def start_background(self, open_browser: bool = False) -> None:
        self._httpd = self._build_httpd()
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.activity.log("server.start_background", url=self.url, open_browser=open_browser)
        if open_browser:
            webbrowser.open(self.url)

    def shutdown(self) -> None:
        self.activity.log("server.shutdown", url=self.url)
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
        controller_lock = self._controller_lock
        session_path = self._session_path
        activity = self.activity
        display_names = self._display_names
        path_chooser = self.path_chooser

        class Handler(BaseHTTPRequestHandler):
            server_version = "SplitShotBrowser/1.0"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                request_path = urlparse(self.path).path
                activity.log("http.get", path=request_path, client=self.client_address[0])
                if request_path in {"/", "/index.html"}:
                    self._send_static("index.html", "text/html; charset=utf-8")
                    return
                if request_path.startswith("/static/"):
                    self._send_static(request_path.removeprefix("/static/"))
                    return
                if request_path == "/api/state":
                    self._send_json(self._browser_state())
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
                if request_path.startswith("/media/merge/"):
                    self._send_merge_media(request_path.removeprefix("/media/merge/"))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:  # noqa: N802
                activity.log("http.post", path=self.path, client=self.client_address[0])
                if self.path == "/api/activity":
                    self._record_browser_activity()
                    return
                if self.path == "/api/files/primary":
                    self._import_primary_file()
                    return
                if self.path == "/api/files/secondary":
                    self._import_merge_file()
                    return
                if self.path == "/api/files/merge":
                    self._import_merge_file()
                    return
                if self.path == "/api/files/practiscore":
                    self._import_practiscore_file()
                    return
                if self.path == "/api/dialog/path":
                    self._choose_dialog_path()
                    return
                routes: dict[str, Callable[[dict[str, Any]], None]] = {
                    "/api/project/details": self._set_project_details,
                    "/api/project/practiscore": self._set_practiscore_context,
                    "/api/project/new": self._new_project,
                    "/api/project/open": self._open_project,
                    "/api/project/save": self._save_project,
                    "/api/project/delete": self._delete_project,
                    "/api/import/primary": self._import_primary,
                    "/api/import/secondary": self._import_merge,
                    "/api/import/merge": self._import_merge,
                    "/api/analysis/threshold": self._set_threshold,
                    "/api/beep": self._set_beep,
                    "/api/shots/add": self._add_shot,
                    "/api/shots/move": self._move_shot,
                    "/api/shots/restore": self._restore_shot,
                    "/api/shots/delete": self._delete_shot,
                    "/api/shots/select": self._select_shot,
                    "/api/scoring": self._set_scoring,
                    "/api/scoring/profile": self._set_scoring_profile,
                    "/api/scoring/score": self._assign_score,
                    "/api/scoring/restore": self._restore_score,
                    "/api/scoring/position": self._set_score_position,
                    "/api/events/add": self._add_event,
                    "/api/events/delete": self._delete_event,
                    "/api/merge/remove": self._remove_merge_source,
                    "/api/merge/source": self._set_merge_source,
                    "/api/overlay": self._set_overlay,
                    "/api/merge": self._set_merge,
                    "/api/sync": self._set_sync,
                    "/api/swap": self._swap_videos,
                    "/api/export/settings": self._set_export_settings,
                    "/api/export/preset": self._set_export_preset,
                    "/api/export": self._export_project,
                }
                route = routes.get(self.path)
                if route is None:
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    payload = self._read_json()
                    activity.log("api.start", path=self.path, payload=payload)
                    with controller_lock:
                        route(payload)
                    activity.log("api.success", path=self.path, status=controller.status_message)
                    self._send_json(self._browser_state())
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.error", path=self.path, error=str(exc))
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
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(data)

            def _choose_dialog_path(self) -> None:
                try:
                    payload = self._read_json()
                    kind = str(payload.get("kind", ""))
                    current = None if payload.get("current") in {"", None} else str(payload["current"])
                    activity.log("api.dialog.path.start", kind=kind, current=current)
                    selected_path = path_chooser(kind, current) or ""
                    activity.log("api.dialog.path.success", kind=kind, selected=selected_path)
                    self._send_json({"path": selected_path})
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.dialog.path.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _browser_state(self) -> dict[str, Any]:
                payload = browser_state(controller.project, controller.status_message)
                primary_path = controller.project.primary_video.path
                secondary_path = (
                    ""
                    if controller.project.secondary_video is None
                    else controller.project.secondary_video.path
                )
                payload["media"]["primary_display_name"] = display_names.get(
                    primary_path,
                    display_name_for_path(primary_path, "No video selected"),
                )
                payload["media"]["secondary_display_name"] = display_names.get(
                    secondary_path,
                    display_name_for_path(secondary_path, "None"),
                )
                payload["project"]["path"] = "" if controller.project_path is None else str(controller.project_path)
                return payload

            def _set_project_details(self, payload: dict[str, Any]) -> None:
                controller.set_project_details(
                    name=None if payload.get("name") in {None, ""} else str(payload["name"]),
                    description=None if payload.get("description") is None else str(payload["description"]),
                )

            def _set_practiscore_context(self, payload: dict[str, Any]) -> None:
                controller.set_practiscore_context(
                    match_type=None if payload.get("match_type") is None else str(payload.get("match_type", "")),
                    stage_number=(
                        None if payload.get("stage_number") in {None, ""} else int(payload["stage_number"])
                    ),
                    competitor_name=(
                        None if payload.get("competitor_name") is None else str(payload.get("competitor_name", ""))
                    ),
                    competitor_place=(
                        None
                        if payload.get("competitor_place") in {None, ""}
                        else int(payload["competitor_place"])
                    ),
                )

            def _send_static(self, name: str, content_type: str | None = None) -> None:
                safe_name = name.replace("\\", "/").lstrip("/")
                if ".." in safe_name:
                    self.send_error(HTTPStatus.BAD_REQUEST)
                    return
                package_root = resources.files("splitshot.browser.static")
                target = package_root / safe_name
                if not target.is_file():
                    activity.log("static.missing", name=safe_name)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                data = target.read_bytes()
                guessed = content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", guessed)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")
                self.end_headers()
                self.wfile.write(data)
                activity.log("static.sent", name=safe_name, bytes=len(data))

            def _send_media(self, path: Path) -> None:
                if not path.exists() or not path.is_file():
                    activity.log("media.missing", path=str(path))
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
                    activity.log("media.range_invalid", path=str(path), start=start, end=end)
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
                activity.log(
                    "media.start",
                    path=str(path),
                    status=int(status),
                    start=start,
                    end=end,
                    bytes=content_length,
                )
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
                            activity.log("media.client_disconnect", path=str(path), remaining=remaining)
                            return
                        remaining -= len(chunk)
                activity.log("media.complete", path=str(path), bytes=content_length)

            def _send_merge_media(self, source_id: str) -> None:
                source = next((item for item in controller.project.merge_sources if item.id == source_id), None)
                if source is None or not source.asset.path:
                    activity.log("media.missing", source_id=source_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_media(Path(source.asset.path))

            def _record_browser_activity(self) -> None:
                try:
                    payload = self._read_json()
                except Exception as exc:  # noqa: BLE001
                    activity.log("browser.activity.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                entries = payload.get("entries")
                if isinstance(entries, list):
                    for entry in entries:
                        if not isinstance(entry, dict):
                            continue
                        event = str(entry.get("event", "browser.event"))
                        detail = entry.get("detail", {})
                        activity.log("browser.activity", browser_event=event, detail=detail, browser_ts=entry.get("ts"))
                else:
                    event = str(payload.get("event", "browser.event"))
                    detail = payload.get("detail", {})
                    activity.log("browser.activity", browser_event=event, detail=detail)
                self._send_json({"ok": True})

            def _save_uploaded_file(self) -> Path:
                content_type = self.headers.get("Content-Type", "")
                match = re.search(r"boundary=(?P<boundary>[^;]+)", content_type)
                if match is None:
                    raise ValueError("Multipart boundary is required")
                boundary = match.group("boundary").strip().strip('"').encode("utf-8")
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    raise ValueError("Video file is required")

                remaining = length

                def read_line() -> bytes:
                    nonlocal remaining
                    if remaining <= 0:
                        return b""
                    line = self.rfile.readline(remaining + 1)
                    remaining -= len(line)
                    return line

                def drain_remaining() -> None:
                    nonlocal remaining
                    if remaining > 0:
                        self.rfile.read(remaining)
                        remaining = 0

                part_boundary = b"--" + boundary
                opening_boundary = read_line()
                if not opening_boundary.startswith(part_boundary):
                    drain_remaining()
                    raise ValueError("Malformed multipart body: starting boundary not found")

                disposition = ""
                while True:
                    header_line = read_line()
                    if header_line in {b"", b"\r\n", b"\n"}:
                        break
                    decoded = header_line.decode("utf-8", errors="replace")
                    if decoded.lower().startswith("content-disposition:"):
                        disposition = decoded

                if 'name="file"' not in disposition or "filename=" not in disposition:
                    drain_remaining()
                    raise ValueError("Multipart request must contain a file field named 'file'")

                filename_match = re.search(r'filename="(?P<filename>[^"]*)"', disposition)
                filename = filename_match.group("filename") if filename_match else "video.mp4"
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._")
                if not safe_name:
                    safe_name = "video.mp4"

                target = session_path / f"{uuid4().hex}_{safe_name}"
                boundary_marker = b"\r\n" + part_boundary
                lookbehind = len(boundary_marker) + 4
                buffer = b""
                bytes_written = 0

                with target.open("wb") as output_file:
                    while remaining > 0:
                        chunk = self.rfile.read(min(64 * 1024, remaining))
                        if not chunk:
                            break
                        remaining -= len(chunk)
                        buffer += chunk
                        while True:
                            marker_index = buffer.find(boundary_marker)
                            if marker_index < 0:
                                break
                            marker_end = marker_index + len(boundary_marker)
                            suffix = buffer[marker_end : marker_end + 2]
                            if suffix in {b"--", b"\r\n"}:
                                output_file.write(buffer[:marker_index])
                                bytes_written += marker_index
                                if remaining > 0:
                                    drain_remaining()
                                if bytes_written == 0:
                                    raise ValueError("Video file is required")
                                display_names[str(target)] = Path(filename).name
                                return target
                            if remaining <= 0:
                                break
                            next_chunk = self.rfile.read(min(64 * 1024, remaining))
                            if not next_chunk:
                                break
                            remaining -= len(next_chunk)
                            buffer += next_chunk
                        if len(buffer) > lookbehind:
                            output_file.write(buffer[:-lookbehind])
                            bytes_written += len(buffer[:-lookbehind])
                            buffer = buffer[-lookbehind:]

                drain_remaining()
                if target.exists():
                    target.unlink(missing_ok=True)
                raise ValueError("Malformed multipart body: closing boundary not found")

            def _import_primary_file(self) -> None:
                try:
                    path = self._save_uploaded_file()
                    activity.log("api.files.primary.saved", path=str(path))
                    with controller_lock:
                        controller.ingest_primary_video(str(path))
                    activity.log(
                        "api.files.primary.ingested",
                        path=str(path),
                        shots=len(controller.project.analysis.shots),
                        status=controller.status_message,
                    )
                    self._send_json(self._browser_state())
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.files.primary.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _import_merge_file(self) -> None:
                try:
                    path = self._save_uploaded_file()
                    activity.log("api.files.merge.saved", path=str(path))
                    with controller_lock:
                        controller.add_merge_source(str(path))
                    activity.log(
                        "api.files.merge.ingested",
                        path=str(path),
                        status=controller.status_message,
                    )
                    self._send_json(self._browser_state())
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.files.merge.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _import_practiscore_file(self) -> None:
                try:
                    path = self._save_uploaded_file()
                    activity.log("api.files.practiscore.saved", path=str(path))
                    source_name = display_names.get(str(path), Path(path).name)
                    with controller_lock:
                        controller.import_practiscore_file(str(path), source_name=source_name)
                    activity.log(
                        "api.files.practiscore.imported",
                        path=str(path),
                        stage=controller.project.scoring.stage_number,
                        status=controller.status_message,
                    )
                    self._send_json(self._browser_state())
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.files.practiscore.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _new_project(self, payload: dict[str, Any]) -> None:
                display_names.clear()
                controller.new_project()

            def _open_project(self, payload: dict[str, Any]) -> None:
                display_names.clear()
                controller.open_project(str(payload["path"]))

            def _save_project(self, payload: dict[str, Any]) -> None:
                target = payload.get("path") or (
                    None if controller.project_path is None else str(controller.project_path)
                )
                if not target:
                    raise ValueError("Project path is required")
                controller.save_project(str(target))

            def _delete_project(self, payload: dict[str, Any]) -> None:
                display_names.clear()
                controller.delete_current_project()

            def _import_primary(self, payload: dict[str, Any]) -> None:
                controller.ingest_primary_video(str(payload["path"]))

            def _import_secondary(self, payload: dict[str, Any]) -> None:
                controller.add_merge_source(str(payload["path"]))

            def _import_merge(self, payload: dict[str, Any]) -> None:
                controller.add_merge_source(str(payload["path"]))

            def _remove_merge_source(self, payload: dict[str, Any]) -> None:
                source_id = payload.get("source_id") or payload.get("id")
                if source_id in {None, ""}:
                    raise ValueError("source_id is required")
                controller.remove_merge_source(str(source_id))

            def _set_threshold(self, payload: dict[str, Any]) -> None:
                controller.set_detection_threshold(float(payload["threshold"]))

            def _set_beep(self, payload: dict[str, Any]) -> None:
                controller.set_beep_time(int(payload["time_ms"]))

            def _add_shot(self, payload: dict[str, Any]) -> None:
                controller.add_shot(int(payload["time_ms"]))

            def _move_shot(self, payload: dict[str, Any]) -> None:
                controller.move_shot(str(payload["shot_id"]), int(payload["time_ms"]))

            def _restore_shot(self, payload: dict[str, Any]) -> None:
                controller.restore_original_shot_timing(str(payload["shot_id"]))

            def _delete_shot(self, payload: dict[str, Any]) -> None:
                controller.delete_shot(str(payload["shot_id"]))

            def _select_shot(self, payload: dict[str, Any]) -> None:
                shot_id = payload.get("shot_id")
                controller.select_shot(None if shot_id in {"", None} else str(shot_id))

            def _set_scoring(self, payload: dict[str, Any]) -> None:
                if "enabled" in payload:
                    controller.set_scoring_enabled(bool(payload["enabled"]))
                if "penalties" in payload:
                    controller.set_penalties(float(payload["penalties"]))
                if "penalty_counts" in payload:
                    controller.set_penalty_counts(
                        {
                            str(key): float(value)
                            for key, value in payload["penalty_counts"].items()
                        }
                    )

            def _set_scoring_profile(self, payload: dict[str, Any]) -> None:
                controller.set_scoring_preset(str(payload["ruleset"]))

            def _restore_score(self, payload: dict[str, Any]) -> None:
                controller.restore_original_shot_score(str(payload["shot_id"]))

            def _assign_score(self, payload: dict[str, Any]) -> None:
                letter_value = payload.get("letter")
                penalty_counts = payload.get("penalty_counts")
                if letter_value in {None, ""} and penalty_counts is None:
                    raise ValueError("letter or penalty_counts is required")
                controller.assign_score(
                    str(payload["shot_id"]),
                    None if letter_value in {None, ""} else ScoreLetter(str(letter_value)),
                    None
                    if penalty_counts is None
                    else {
                        str(key): float(value)
                        for key, value in dict(penalty_counts).items()
                    },
                )

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
                controller.set_overlay_badge_layout(
                    str(payload.get("style_type", controller.project.overlay.style_type)),
                    int(payload.get("spacing", controller.project.overlay.spacing)),
                    int(payload.get("margin", controller.project.overlay.margin)),
                )
                controller.set_overlay_display_options(payload)
                styles = payload.get("styles", {})
                if not isinstance(styles, dict):
                    raise ValueError("styles must be an object")
                for badge_name, style in styles.items():
                    if not isinstance(style, dict):
                        raise ValueError(f"Overlay style for {badge_name} must be an object")
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
                if "pip_size_percent" in payload:
                    controller.set_pip_size_percent(int(payload["pip_size_percent"]))
                if "pip_size" in payload:
                    controller.set_pip_size(PipSize(str(payload["pip_size"])))
                if "pip_x" in payload or "pip_y" in payload:
                    controller.set_pip_position(
                        None if payload.get("pip_x") in {None, ""} else float(payload["pip_x"]),
                        None if payload.get("pip_y") in {None, ""} else float(payload["pip_y"]),
                    )

            def _set_merge_source(self, payload: dict[str, Any]) -> None:
                source_id = payload.get("source_id") or payload.get("id")
                if source_id in {None, ""}:
                    raise ValueError("source_id is required")
                if payload.get("sync_delta_ms") not in {None, ""}:
                    controller.adjust_merge_source_sync_offset(str(source_id), int(payload["sync_delta_ms"]))
                    return
                controller.set_merge_source_position(
                    str(source_id),
                    None if payload.get("pip_size_percent") in {None, ""} else int(payload["pip_size_percent"]),
                    None if payload.get("pip_x") in {None, ""} else float(payload["pip_x"]),
                    None if payload.get("pip_y") in {None, ""} else float(payload["pip_y"]),
                )
                if payload.get("sync_offset_ms") not in {None, ""}:
                    controller.set_merge_source_sync_offset(str(source_id), int(payload["sync_offset_ms"]))

            def _add_event(self, payload: dict[str, Any]) -> None:
                controller.add_timing_event(
                    kind=str(payload.get("kind", "reload")),
                    after_shot_id=None if payload.get("after_shot_id") in {None, ""} else str(payload["after_shot_id"]),
                    before_shot_id=None if payload.get("before_shot_id") in {None, ""} else str(payload["before_shot_id"]),
                    label=None if payload.get("label") in {None, ""} else str(payload["label"]),
                    note=str(payload.get("note", "")),
                )

            def _delete_event(self, payload: dict[str, Any]) -> None:
                event_id = payload.get("event_id") or payload.get("id")
                if event_id in {None, ""}:
                    raise ValueError("event_id is required")
                controller.delete_timing_event(str(event_id))

            def _set_sync(self, payload: dict[str, Any]) -> None:
                if "offset_ms" in payload:
                    controller.set_sync_offset(int(payload["offset_ms"]))
                elif "delta_ms" in payload:
                    controller.adjust_sync_offset(int(payload["delta_ms"]))

            def _swap_videos(self, payload: dict[str, Any]) -> None:
                controller.swap_videos()

            def _set_export_settings(self, payload: dict[str, Any]) -> None:
                controller.set_export_settings(payload)

            def _set_export_preset(self, payload: dict[str, Any]) -> None:
                controller.apply_export_preset(str(payload["preset"]))

            def _export_project(self, payload: dict[str, Any]) -> None:
                scoring_payload = payload.get("scoring")
                if isinstance(scoring_payload, dict):
                    if "ruleset" in scoring_payload:
                        self._set_scoring_profile(scoring_payload)
                    self._set_scoring(scoring_payload)
                overlay_payload = payload.get("overlay")
                if isinstance(overlay_payload, dict):
                    self._set_overlay(overlay_payload)
                merge_payload = payload.get("merge")
                if isinstance(merge_payload, dict):
                    self._set_merge(merge_payload)
                    for source_payload in merge_payload.get("sources", []):
                        if isinstance(source_payload, dict):
                            self._set_merge_source(source_payload)
                _sync_export_payload(controller, payload)
                output_path = Path(str(payload["path"]))
                activity.log("api.export.start", path=str(output_path))
                exported_path = export_project(
                    controller.project,
                    output_path,
                    progress_callback=lambda value: activity.log("api.export.progress", progress=value),
                    log_callback=lambda line: activity.log("api.export.log", line=line),
                )
                if not exported_path.exists() or exported_path.stat().st_size <= 0:
                    raise RuntimeError("Export did not produce an output file.")
                controller.project.export.output_path = str(exported_path)
                activity.log(
                    "api.export.complete",
                    path=str(exported_path),
                    bytes=exported_path.stat().st_size if exported_path.exists() else 0,
                )
                controller.project.touch()
                controller.status_message = f"Exported video to {exported_path}."

        return Handler
