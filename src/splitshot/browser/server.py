from __future__ import annotations

import csv
from dataclasses import dataclass
import errno
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
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from splitshot.browser.activity import ActivityLogger
from splitshot.browser.practiscore_session import PractiScoreSessionManager
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
from splitshot.media.ffmpeg import resolve_media_binary, run_ffmpeg, run_ffprobe_json
from splitshot.persistence.projects import (
    PROJECT_FILENAME,
    missing_required_project_dirs,
    normalize_project_path,
    resolve_project_path,
)
from splitshot.ui.controller import ProjectController


EXPECTED_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
EXPECTED_DISCONNECT_ERRNOS = {errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ENOBUFS}
PathChooser = Callable[[str, str | None], str | None]
COMMON_VIDEO_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.avi *.wmv *.webm *.mkv *.mpg *.mpeg *.mts *.m2ts"
COMMON_IMAGE_FILE_PATTERNS = "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.tif *.tiff"
COMMON_EXPORT_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.mkv"
_PCM_BROWSER_PROXY_FORMATS = {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"}
_PCM_BROWSER_PROXY_SUFFIXES = {".mov", ".qt", ".mp4", ".m4v", ".m4a"}
_BROWSER_COPY_SAFE_VIDEO_CODECS = {"av1", "h264", "vp8", "vp9"}
MAX_BROWSER_UPLOAD_BYTES = 8 * 1024 * 1024 * 1024
_BROWSER_CONTENT_SECURITY_POLICY = "; ".join(
    [
        "default-src 'none'",
        "base-uri 'none'",
        "frame-ancestors 'none'",
        "form-action 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data:",
        "media-src 'self' blob:",
        "connect-src 'self'",
        "font-src 'self' data:",
        "object-src 'none'",
    ]
)


@dataclass(slots=True)
class BrowserMediaCacheEntry:
    signature: tuple[int, int]
    preview_path: str | None
    proxy_reason: str | None
    audio_codec: str | None


def _browser_media_signature(path: Path) -> tuple[int, int]:
    stats = path.stat()
    return (stats.st_size, stats.st_mtime_ns)


def _metadata_format_names(metadata: dict[str, Any]) -> set[str]:
    format_name = str(metadata.get("format", {}).get("format_name", ""))
    return {item.strip().lower() for item in format_name.split(",") if item.strip()}


def _browser_audio_proxy_reason(path: Path, metadata: dict[str, Any]) -> tuple[str | None, str | None]:
    streams = metadata.get("streams", [])
    if not isinstance(streams, list):
        return None, None
    audio_stream = next((item for item in streams if item.get("codec_type") == "audio"), None)
    if not isinstance(audio_stream, dict):
        return None, None
    audio_codec = str(audio_stream.get("codec_name", "")).lower() or None
    if not audio_codec or not audio_codec.startswith("pcm_"):
        return None, audio_codec
    format_names = _metadata_format_names(metadata)
    if path.suffix.lower() in _PCM_BROWSER_PROXY_SUFFIXES or format_names.intersection(_PCM_BROWSER_PROXY_FORMATS):
        return "pcm_audio_in_mov_mp4", audio_codec
    return None, audio_codec


def _browser_preview_output_path(session_path: Path, source_path: Path) -> Path:
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", source_path.stem).strip("._") or "preview"
    return session_path / f"{uuid4().hex}_{safe_stem}_browser.mp4"


def _browser_preview_command(source_path: Path, preview_path: Path, metadata: dict[str, Any]) -> list[str]:
    streams = metadata.get("streams", [])
    video_stream = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"),
        None,
    )
    video_codec = str(video_stream.get("codec_name", "")).lower() if isinstance(video_stream, dict) else ""
    video_args = ["-c:v", "copy"] if video_codec in _BROWSER_COPY_SAFE_VIDEO_CODECS else [
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-preset",
        "ultrafast",
    ]
    return [
        "-i",
        str(source_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a:0?",
        *video_args,
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(preview_path),
    ]


def _append_browser_preview_status(message: str, audio_codec: str | None) -> str:
    return message


def _browser_video_timeline_signature(metadata: dict[str, Any]) -> dict[str, str]:
    streams = metadata.get("streams", [])
    video_stream = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"),
        None,
    )
    if not isinstance(video_stream, dict):
        return {}

    def normalized_value(key: str) -> str:
        value = video_stream.get(key)
        return "" if value in {None, ""} else str(value)

    return {
        "codec_name": normalized_value("codec_name").lower(),
        "width": normalized_value("width"),
        "height": normalized_value("height"),
        "start_pts": normalized_value("start_pts"),
        "start_time": normalized_value("start_time"),
        "time_base": normalized_value("time_base"),
        "duration_ts": normalized_value("duration_ts"),
        "avg_frame_rate": normalized_value("avg_frame_rate"),
        "r_frame_rate": normalized_value("r_frame_rate"),
        "nb_frames": normalized_value("nb_frames"),
    }


def _browser_preview_matches_source_timeline(
    source_timeline: dict[str, str],
    preview_timeline: dict[str, str],
) -> bool:
    if not source_timeline or not preview_timeline:
        return False

    required_fields = (
        "codec_name",
        "width",
        "height",
        "start_time",
        "time_base",
        "avg_frame_rate",
        "r_frame_rate",
    )
    for field in required_fields:
        if source_timeline.get(field) != preview_timeline.get(field):
            return False

    start_pts_source = _int_metadata_value(source_timeline.get("start_pts"))
    start_pts_preview = _int_metadata_value(preview_timeline.get("start_pts"))
    if start_pts_source is not None and start_pts_preview is not None and start_pts_source != start_pts_preview:
        return False

    source_frames = _int_metadata_value(source_timeline.get("nb_frames"))
    preview_frames = _int_metadata_value(preview_timeline.get("nb_frames"))
    if source_frames is not None and preview_frames is not None and source_frames != preview_frames:
        return False

    return True


def _int_metadata_value(value: str | None) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return None


def _ffprobe_video_packet_csv(path: Path) -> str:
    command = [
        resolve_media_binary("ffprobe"),
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "packet=pts,dts,duration,flags",
        "-of",
        "csv=p=0",
        str(path),
    ]
    process = subprocess.run(command, check=False, capture_output=True, text=True)
    if process.returncode != 0:
        raise RuntimeError(process.stderr.strip() or "FFprobe packet timeline command failed")
    return process.stdout


def _video_packet_timeline_rows(packet_csv: str) -> tuple[tuple[str, str, str], ...]:
    rows: list[tuple[str, str, str]] = []
    for row in csv.reader(packet_csv.splitlines()):
        if len(row) < 3:
            continue
        rows.append((row[0], row[1], row[2]))
    return tuple(rows)


def _browser_preview_matches_source_packets(source_path: Path, preview_path: Path) -> bool:
    # FFprobe packet flags can change after an audio-only compatibility remux even when
    # the copied video packet timeline remains exact. Compare timing only.
    return _video_packet_timeline_rows(_ffprobe_video_packet_csv(source_path)) == _video_packet_timeline_rows(
        _ffprobe_video_packet_csv(preview_path)
    )


def _validate_browser_preview_timeline(
    source_path: Path,
    source_metadata: dict[str, Any],
    preview_path: Path,
) -> tuple[bool, dict[str, str], dict[str, str]]:
    preview_metadata = run_ffprobe_json(preview_path)
    source_timeline = _browser_video_timeline_signature(source_metadata)
    preview_timeline = _browser_video_timeline_signature(preview_metadata)
    metadata_match = _browser_preview_matches_source_timeline(source_timeline, preview_timeline)
    return (
        metadata_match and _browser_preview_matches_source_packets(source_path, preview_path),
        source_timeline,
        preview_timeline,
    )


def is_expected_disconnect_error(exc: BaseException | None) -> bool:
    if isinstance(exc, EXPECTED_DISCONNECT_ERRORS):
        return True
    return isinstance(exc, OSError) and exc.errno in EXPECTED_DISCONNECT_ERRNOS


def _existing_dialog_directory(current: str | None, *, project_path: bool = False) -> Path:
    if not current:
        return Path.home()

    candidate = resolve_project_path(current) if project_path else Path(current)
    candidate = candidate.expanduser()
    if candidate.exists():
        return candidate.resolve() if candidate.is_dir() else candidate.resolve().parent

    probe = candidate.parent
    while True:
        if probe.exists() and probe.is_dir():
            return probe.resolve()
        if probe.parent == probe:
            break
        probe = probe.parent
    return Path.home()


def choose_local_path(kind: str, current: str | None = None) -> str | None:
    if sys.platform == "darwin":
        return choose_local_path_macos(kind, current)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception as exc:  # noqa: BLE001
        return None

    initial_dir = str(
        _existing_dialog_directory(
            current,
            project_path=kind in {"project", "project_save", "project_open", "project_folder"},
        )
    )
    root = tk.Tk()
    root.withdraw()
    try:
        try:
            root.attributes("-topmost", True)
        except tk.TclError:
            pass
        if kind in {"primary", "secondary", "popup_image"}:
            return filedialog.askopenfilename(
                title=(
                    "Choose stage video"
                    if kind == "primary"
                    else ("Choose secondary angle video" if kind == "secondary" else "Choose marker image")
                ),
                initialdir=initial_dir,
                filetypes=[
                    ("Image files", COMMON_IMAGE_FILE_PATTERNS),
                    ("Video files", COMMON_VIDEO_FILE_PATTERNS),
                    ("All files", "*.*"),
                ],
            )
        if kind in {"project", "project_save", "project_open", "project_folder"}:
            return filedialog.askdirectory(
                title="Choose SplitShot project folder",
                initialdir=initial_dir,
                mustexist=True,
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
    default_dir = _existing_dialog_directory(
        current,
        project_path=kind in {"project", "project_save", "project_open", "project_folder"},
    )
    default_name = "output.mp4"
    if kind in {"primary", "secondary", "popup_image"}:
        prompt = (
            "Choose stage video"
            if kind == "primary"
            else ("Choose secondary angle video" if kind == "secondary" else "Choose marker image")
        )
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
    if kind in {"project", "project_save", "project_open", "project_folder"}:
        script = "\n".join(
            [
                f"set chosenFolder to choose folder with prompt {_applescript_string('Choose SplitShot project folder')} "
                f"default location POSIX file {_applescript_string(str(default_dir))}",
                "POSIX path of chosenFolder",
            ]
        )
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return result.stdout.strip()
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Native file browser failed.")
    if kind == "export":
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
    allow_reuse_address = True

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
        browser_media_proxy_enabled: bool = True,
    ) -> None:
        self.controller = controller or ProjectController()
        self.host = host
        self.port = port
        self.activity = ActivityLogger(log_dir, console_level=log_level)
        self.path_chooser = path_chooser or choose_local_path
        self.browser_media_proxy_enabled = browser_media_proxy_enabled
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._controller_lock = threading.Lock()
        self._session_dir = TemporaryDirectory(prefix="splitshot-browser-")
        self._session_path = Path(self._session_dir.name)
        self._display_names: dict[str, str] = {}
        self._browser_media_cache: dict[str, BrowserMediaCacheEntry] = {}
        self._browser_media_lock = threading.Lock()
        self._media_url_token = uuid4().hex
        self.practiscore_session = PractiScoreSessionManager()
        prepare_export_runtime()
        self.activity.log("server.initialized", host=host, port=port, log_path=str(self.activity.path))

    @property
    def url(self) -> str:
        if self._httpd is not None:
            host, port = self._httpd.server_address[:2]
            return f"http://{host}:{port}/"
        return f"http://{self.host}:{self.port}/"

    def _attempt_open_browser(self) -> bool:
        try:
            success = webbrowser.open(self.url)
        except Exception as exc:  # noqa: BLE001
            self.activity.log("browser.open.error", url=self.url, error=str(exc))
            success = False

        self.activity.log("browser.open", url=self.url, success=success)
        if not success:
            print("Failed to open the local browser automatically.")
            print(f"Open SplitShot manually at {self.url}")
        return success

    def serve_forever(self, open_browser: bool = True) -> None:
        try:
            self._httpd = self._build_httpd()
        except OSError as exc:
            self.activity.log("server.bind.error", host=self.host, port=self.port, error=str(exc))
            print(f"SplitShot could not bind to {self.host}:{self.port}: {exc}")
            print("Use --port to select a different port, or stop the process using this port.")
            raise

        self.activity.log("server.serve_forever", url=self.url, open_browser=open_browser)
        try:
            if open_browser:
                self._thread = threading.Thread(target=self._httpd.serve_forever)
                self._thread.start()
                self._attempt_open_browser()
                try:
                    while self._thread.is_alive():
                        self._thread.join(timeout=0.5)
                except KeyboardInterrupt:
                    print("\nSplitShot browser control stopped.")
            else:
                try:
                    self._httpd.serve_forever()
                except KeyboardInterrupt:
                    print("\nSplitShot browser control stopped.")
        finally:
            self.activity.log("server.stopping", url=self.url)
            self.practiscore_session.shutdown()
            self._httpd.server_close()
            self._session_dir.cleanup()

    def start_background(self, open_browser: bool = False) -> None:
        try:
            self._httpd = self._build_httpd()
        except OSError as exc:
            self.activity.log("server.bind.error", host=self.host, port=self.port, error=str(exc))
            print(f"SplitShot could not bind to {self.host}:{self.port}: {exc}")
            print("Use --port to select a different port, or stop the process using this port.")
            raise

        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.activity.log("server.start_background", url=self.url, open_browser=open_browser)
        if open_browser:
            self._attempt_open_browser()

    def shutdown(self) -> None:
        self.activity.log("server.shutdown", url=self.url)
        self.practiscore_session.shutdown()
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._session_dir.cleanup()

    def _build_httpd(self) -> ThreadingHTTPServer:
        return QuietThreadingHTTPServer((self.host, self.port), self._handler())

    def _bump_media_url_token(self) -> None:
        self._media_url_token = uuid4().hex

    def _prepare_browser_media(self, path: Path) -> tuple[Path, bool, str | None, str | None]:
        if not path.exists() or not path.is_file():
            return path, False, None, None
        guessed_type = mimetypes.guess_type(path.name)[0] or ""
        if not guessed_type.startswith("video/"):
            return path, False, None, None
        if not self.browser_media_proxy_enabled:
            return path, False, None, None

        source_key = str(path.resolve())
        signature = _browser_media_signature(path)
        with self._browser_media_lock:
            cached = self._browser_media_cache.get(source_key)
            if cached and cached.signature == signature:
                if cached.preview_path:
                    preview_path = Path(cached.preview_path)
                    if preview_path.exists() and preview_path.is_file():
                        return preview_path, True, cached.proxy_reason, cached.audio_codec
                else:
                    return path, False, cached.proxy_reason, cached.audio_codec

        metadata = run_ffprobe_json(path)
        proxy_reason, audio_codec = _browser_audio_proxy_reason(path, metadata)
        if proxy_reason is None:
            with self._browser_media_lock:
                self._browser_media_cache[source_key] = BrowserMediaCacheEntry(
                    signature=signature,
                    preview_path=None,
                    proxy_reason=None,
                    audio_codec=audio_codec,
                )
            return path, False, None, audio_codec

        preview_path = _browser_preview_output_path(self._session_path, path)
        run_ffmpeg(_browser_preview_command(path, preview_path, metadata))
        timeline_valid, source_timeline, preview_timeline = _validate_browser_preview_timeline(path, metadata, preview_path)
        if not timeline_valid:
            preview_path.unlink(missing_ok=True)
            with self._browser_media_lock:
                self._browser_media_cache[source_key] = BrowserMediaCacheEntry(
                    signature=signature,
                    preview_path=None,
                    proxy_reason="timeline_validation_failed",
                    audio_codec=audio_codec,
                )
            self.activity.log(
                "media.compatibility.rejected",
                source_path=str(path),
                preview_path=str(preview_path),
                proxy_reason=proxy_reason,
                audio_codec=audio_codec,
                source_timeline=source_timeline,
                preview_timeline=preview_timeline,
            )
            return path, False, None, audio_codec

        with self._browser_media_lock:
            previous = self._browser_media_cache.get(source_key)
            self._browser_media_cache[source_key] = BrowserMediaCacheEntry(
                signature=signature,
                preview_path=str(preview_path),
                proxy_reason=proxy_reason,
                audio_codec=audio_codec,
            )
        if previous and previous.preview_path and previous.preview_path != str(preview_path):
            Path(previous.preview_path).unlink(missing_ok=True)
        self.activity.log(
            "media.compatibility.created",
            source_path=str(path),
            preview_path=str(preview_path),
            proxy_reason=proxy_reason,
            audio_codec=audio_codec,
            timeline_validated=True,
        )
        return preview_path, True, proxy_reason, audio_codec

    def _clear_browser_media_cache(self) -> None:
        with self._browser_media_lock:
            cached_paths = [entry.preview_path for entry in self._browser_media_cache.values() if entry.preview_path]
            self._browser_media_cache.clear()
        for preview_path in cached_paths:
            Path(preview_path).unlink(missing_ok=True)

    def _handler(self) -> type[BaseHTTPRequestHandler]:
        server = self
        controller = self.controller
        controller_lock = self._controller_lock
        session_path = self._session_path
        activity = self.activity
        display_names = self._display_names
        path_chooser = self.path_chooser
        practiscore_session = self.practiscore_session

        class Handler(BaseHTTPRequestHandler):
            server_version = "SplitShotBrowser/1.0"

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
                return

            def do_GET(self) -> None:  # noqa: N802
                parsed_url = urlparse(self.path)
                request_path = parsed_url.path
                activity.log("http.get", path=request_path, client=self.client_address[0])
                if request_path in {"/", "/index.html"}:
                    self._send_static("index.html", "text/html; charset=utf-8")
                    return
                if request_path.startswith("/static/"):
                    self._send_static(request_path.removeprefix("/static/"))
                    return
                if request_path == "/api/activity/poll":
                    self._poll_activity(parsed_url.query)
                    return
                if request_path == "/api/state":
                    self._send_json(self._browser_state())
                    return
                if request_path == "/api/practiscore/session/status":
                    self._send_json(practiscore_session.serialize_status())
                    return
                if request_path == "/api/practiscore/matches":
                    self._list_practiscore_matches()
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
                if request_path.startswith("/media/popup/"):
                    self._send_popup_media(request_path.removeprefix("/media/popup/"))
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
                if self.path == "/api/practiscore/dashboard/open":
                    self._open_practiscore_dashboard()
                    return
                if self.path == "/api/practiscore/session/start":
                    self._start_practiscore_session()
                    return
                if self.path == "/api/practiscore/session/clear":
                    self._clear_practiscore_session()
                    return
                if self.path == "/api/practiscore/sync/start":
                    self._start_practiscore_sync()
                    return
                if self.path == "/api/dialog/path":
                    self._choose_dialog_path()
                    return
                if self.path == "/api/project/probe":
                    self._probe_project()
                    return
                routes: dict[str, Callable[[dict[str, Any]], None]] = {
                    "/api/project/details": self._set_project_details,
                    "/api/project/practiscore": self._set_practiscore_context,
                    "/api/project/ui-state": self._set_project_ui_state,
                    "/api/project/new": self._new_project,
                    "/api/project/open": self._open_project,
                    "/api/project/save": self._save_project,
                    "/api/project/delete": self._delete_project,
                    "/api/import/primary": self._import_primary,
                    "/api/import/secondary": self._import_merge,
                    "/api/import/merge": self._import_merge,
                    "/api/analysis/threshold": self._set_threshold,
                    "/api/analysis/shotml-settings": self._set_shotml_settings,
                    "/api/analysis/shotml/proposals": self._generate_shotml_proposals,
                    "/api/analysis/shotml/apply-proposal": self._apply_shotml_proposal,
                    "/api/analysis/shotml/discard-proposal": self._discard_shotml_proposal,
                    "/api/analysis/shotml/reset-defaults": self._reset_shotml_defaults,
                    "/api/settings": self._set_settings_defaults,
                    "/api/settings/reset-defaults": self._reset_settings_defaults,
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
                    "/api/merge/reset-defaults": self._reset_merge_defaults,
                    "/api/merge/source": self._set_merge_source,
                    "/api/overlay": self._set_overlay,
                    "/api/popups": self._set_popups,
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
                        controller.autosave_project_if_needed()
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

            def _send_security_headers(self, *, include_csp: bool = False) -> None:
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("X-Frame-Options", "DENY")
                self.send_header("Referrer-Policy", "no-referrer")
                if include_csp:
                    self.send_header("Content-Security-Policy", _BROWSER_CONTENT_SECURITY_POLICY)

            def _send_no_cache_headers(self) -> None:
                self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
                self.send_header("Pragma", "no-cache")
                self.send_header("Expires", "0")

            def _send_json(self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self._send_security_headers(include_csp=True)
                self._send_no_cache_headers()
                self.end_headers()
                self.wfile.write(data)

            def _send_structured_error(
                self,
                *,
                code: str,
                message: str,
                status: HTTPStatus,
                details: dict[str, Any] | None = None,
            ) -> None:
                payload: dict[str, Any] = {
                    "error": {
                        "code": code,
                        "message": message,
                    }
                }
                if details:
                    payload["error"]["details"] = details
                self._send_json(payload, status=status)

            def _send_task_b_unavailable(self, route: str, hook_name: str) -> None:
                self._send_structured_error(
                    code="practiscore_task_b_unavailable",
                    message=(
                        f"{route} is not available until Task B implements controller.{hook_name}()."
                    ),
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                    details={
                        "route": route,
                        "required_hook": hook_name,
                    },
                )

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

            def _probe_project(self) -> None:
                try:
                    payload = self._read_json()
                    target = str(payload.get("path", "")).strip()
                    if not target:
                        raise ValueError("Project path is required")
                    normalized_target = str(controller.normalize_project_folder_path(target))
                    activity.log("api.project.probe.start", path=target, normalized_path=normalized_target)
                    has_project_file = controller.project_folder_has_project_file(normalized_target)
                    missing_dirs = missing_required_project_dirs(normalized_target)
                    activity.log(
                        "api.project.probe.success",
                        path=target,
                        normalized_path=normalized_target,
                        has_project_file=has_project_file,
                        missing_dirs=missing_dirs,
                    )
                    self._send_json({
                        "path": target,
                        "normalized_path": str(normalize_project_path(normalized_target)),
                        "has_project_file": has_project_file,
                        "missing_required_dirs": missing_dirs,
                    })
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.project.probe.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _poll_activity(self, query_string: str) -> None:
                params = parse_qs(query_string or "", keep_blank_values=False)
                raw_after = params.get("after", ["0"])[0]
                try:
                    after_seq = max(0, int(raw_after))
                except ValueError:
                    after_seq = 0
                self._send_json(activity.snapshot(after_seq=after_seq))

            def _browser_state(self) -> dict[str, Any]:
                payload = browser_state(
                    controller.project,
                    controller.status_message,
                    settings=controller.effective_settings().to_dict(),
                    settings_layers=controller.settings_layers(),
                    practiscore_options=controller.practiscore_browser_state(),
                    media_cache_token=server._media_url_token,
                )
                primary_path = controller.project.primary_video.path
                secondary_path = (
                    ""
                    if controller.project.secondary_video is None
                    else controller.project.secondary_video.path
                )
                payload["media"]["primary_display_name"] = display_names.get(
                    primary_path,
                    display_name_for_path(primary_path, "No Video Selected"),
                )
                payload["media"]["secondary_display_name"] = display_names.get(
                    secondary_path,
                    display_name_for_path(secondary_path, "None"),
                )
                payload["project"]["path"] = "" if controller.project_path is None else str(controller.project_path)
                return payload

            def _start_practiscore_session(self) -> None:
                try:
                    with controller_lock:
                        status = practiscore_session.start_login_flow()
                    activity.log("api.practiscore.session.start", state=status.state)
                    self._send_json(status.to_dict())
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.practiscore.session.start.error", error=str(exc))
                    self._send_structured_error(
                        code="practiscore_session_start_failed",
                        message="Unable to prepare the PractiScore browser session.",
                        status=HTTPStatus.INTERNAL_SERVER_ERROR,
                        details={
                            "route": "/api/practiscore/session/start",
                            "reason": str(exc),
                        },
                    )

            def _open_practiscore_dashboard(self) -> None:
                dashboard_url = "https://practiscore.com/dashboard/home"
                try:
                    opened = bool(webbrowser.open(dashboard_url, new=2))
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.practiscore.dashboard.open.error", error=str(exc))
                    self._send_structured_error(
                        code="practiscore_dashboard_open_failed",
                        message="Unable to open the PractiScore dashboard in your browser.",
                        status=HTTPStatus.INTERNAL_SERVER_ERROR,
                        details={
                            "route": "/api/practiscore/dashboard/open",
                            "reason": str(exc),
                            "url": dashboard_url,
                        },
                    )
                    return
                if not opened:
                    activity.log("api.practiscore.dashboard.open.error", error="browser open returned false")
                    self._send_structured_error(
                        code="practiscore_dashboard_open_failed",
                        message="Unable to open the PractiScore dashboard in your browser.",
                        status=HTTPStatus.INTERNAL_SERVER_ERROR,
                        details={
                            "route": "/api/practiscore/dashboard/open",
                            "url": dashboard_url,
                        },
                    )
                    return
                activity.log("api.practiscore.dashboard.open", url=dashboard_url)
                self._send_json({
                    "status": "Opened PractiScore dashboard in your browser.",
                    "url": dashboard_url,
                })

            def _clear_practiscore_session(self) -> None:
                with controller_lock:
                    status = practiscore_session.clear_session()
                activity.log("api.practiscore.session.clear", state=status.state)
                self._send_json(status.to_dict())

            def _list_practiscore_matches(self) -> None:
                hook_name = "list_practiscore_matches"
                hook = getattr(controller, hook_name, None)
                if not callable(hook):
                    self._send_task_b_unavailable("/api/practiscore/matches", hook_name)
                    return
                try:
                    with controller_lock:
                        payload = hook(practiscore_session)
                    self._send_json(payload if isinstance(payload, dict) else {"matches": payload})
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.practiscore.matches.error", error=str(exc))
                    self._send_structured_error(
                        code="practiscore_matches_failed",
                        message=str(exc),
                        status=HTTPStatus.BAD_REQUEST,
                        details={
                            "route": "/api/practiscore/matches",
                            "hook": hook_name,
                        },
                    )

            def _start_practiscore_sync(self) -> None:
                hook_name = "start_practiscore_sync"
                hook = getattr(controller, hook_name, None)
                if not callable(hook):
                    self._send_task_b_unavailable("/api/practiscore/sync/start", hook_name)
                    return
                try:
                    payload = self._read_json()
                    activity.log("api.practiscore.sync.start", payload=payload)
                    with controller_lock:
                        result = hook(payload, practiscore_session)
                        controller.autosave_project_if_needed()
                    self._send_json(result if isinstance(result, dict) else {"sync": result})
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.practiscore.sync.start.error", error=str(exc))
                    self._send_structured_error(
                        code="practiscore_sync_failed",
                        message=str(exc),
                        status=HTTPStatus.BAD_REQUEST,
                        details={
                            "route": "/api/practiscore/sync/start",
                            "hook": hook_name,
                        },
                    )

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

            def _set_project_ui_state(self, payload: dict[str, Any]) -> None:
                controller.set_ui_state(payload)

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
                self._send_security_headers(include_csp=True)
                self._send_no_cache_headers()
                self.end_headers()
                self.wfile.write(data)
                activity.log("static.sent", name=safe_name, bytes=len(data))

            def _send_file_response(
                self,
                requested_path: Path,
                served_path: Path,
                *,
                proxied: bool = False,
                proxy_reason: str | None = None,
                event_prefix: str = "media",
                content_type: str | None = None,
            ) -> None:
                try:
                    media_file = served_path.open("rb")
                except FileNotFoundError:
                    activity.log(
                        f"{event_prefix}.missing",
                        path=str(requested_path),
                        served_path=str(served_path),
                        proxied=proxied,
                        proxy_reason=proxy_reason,
                    )
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                with media_file:
                    media_file.seek(0, 2)
                    size = media_file.tell()
                    media_file.seek(0)
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
                        activity.log("media.range_invalid", path=str(requested_path), start=start, end=end)
                        self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                        return
                    content_length = end - start + 1
                    guessed_content_type = mimetypes.guess_type(served_path.name)[0]
                    if content_type and guessed_content_type in {None, "audio/x-wav"}:
                        resolved_content_type = content_type
                    else:
                        resolved_content_type = guessed_content_type or content_type or "application/octet-stream"
                    self.send_response(status)
                    self.send_header("Content-Type", resolved_content_type)
                    self.send_header("Accept-Ranges", "bytes")
                    self.send_header("Content-Length", str(content_length))
                    self._send_security_headers()
                    self._send_no_cache_headers()
                    if status == HTTPStatus.PARTIAL_CONTENT:
                        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
                    self.end_headers()
                    activity.log(
                        f"{event_prefix}.start",
                        path=str(requested_path),
                        served_path=str(served_path),
                        proxied=proxied,
                        proxy_reason=proxy_reason,
                        status=int(status),
                        start=start,
                        end=end,
                        bytes=content_length,
                    )
                    media_file.seek(start)
                    remaining = content_length
                    while remaining > 0:
                        chunk = media_file.read(min(1024 * 1024, remaining))
                        if not chunk:
                            break
                        try:
                            self.wfile.write(chunk)
                        except OSError as exc:
                            if not is_expected_disconnect_error(exc):
                                raise
                            activity.log(
                                f"{event_prefix}.client_disconnect",
                                path=str(served_path),
                                remaining=remaining,
                                errno=exc.errno,
                                error=str(exc),
                            )
                            return
                        remaining -= len(chunk)
                activity.log(f"{event_prefix}.complete", path=str(served_path), bytes=content_length, proxied=proxied)

            def _send_media(self, path: Path) -> None:
                if not path.exists() or not path.is_file():
                    activity.log("media.missing", path=str(path))
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                served_path = path
                proxied = False
                proxy_reason = None
                try:
                    served_path, proxied, proxy_reason, _audio_codec = server._prepare_browser_media(path)
                except Exception as exc:  # noqa: BLE001
                    activity.log("media.compatibility.error", source_path=str(path), error=str(exc))
                    served_path = path
                    proxied = False
                    proxy_reason = None
                self._send_file_response(path, served_path, proxied=proxied, proxy_reason=proxy_reason, event_prefix="media", content_type="video/mp4")

            def _send_merge_media(self, source_id: str) -> None:
                source = next((item for item in controller.project.merge_sources if item.id == source_id), None)
                if source is None or not source.asset.path:
                    activity.log("media.missing", source_id=source_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_media(Path(source.asset.path))

            def _send_popup_media(self, popup_id: str) -> None:
                popup = next((item for item in controller.project.popups if item.id == popup_id), None)
                if popup is None or not popup.image_path:
                    activity.log("popup_media.missing", popup_id=popup_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                path = Path(popup.image_path)
                if not path.exists() or not path.is_file():
                    activity.log("popup_media.missing", popup_id=popup_id, path=str(path))
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_file_response(path, path, event_prefix="popup_media")

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
                if length > MAX_BROWSER_UPLOAD_BYTES:
                    max_gib = MAX_BROWSER_UPLOAD_BYTES // (1024 * 1024 * 1024)
                    raise ValueError(
                        f"Browser upload exceeds the {max_gib} GiB limit. Use the path import field for larger local media files."
                    )

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
                        server._bump_media_url_token()
                        controller.ingest_primary_video(
                            str(path),
                            source_name=display_names.get(str(path), Path(path).name),
                        )
                        _preview_path, proxied, _reason, audio_codec = server._prepare_browser_media(
                            Path(controller.project.primary_video.path)
                        )
                        if proxied:
                            controller.status_message = _append_browser_preview_status(
                                controller.status_message,
                                audio_codec,
                            )
                        controller.autosave_project_if_needed()
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
                        server._bump_media_url_token()
                        controller.add_merge_source(
                            str(path),
                            source_name=display_names.get(str(path), Path(path).name),
                        )
                        controller.autosave_project_if_needed()
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
                        controller.autosave_project_if_needed()
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
                server._clear_browser_media_cache()
                server._bump_media_url_token()
                controller.new_project()

            def _open_project(self, payload: dict[str, Any]) -> None:
                display_names.clear()
                server._clear_browser_media_cache()
                server._bump_media_url_token()
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
                server._clear_browser_media_cache()
                server._bump_media_url_token()
                controller.delete_current_project()

            def _import_primary(self, payload: dict[str, Any]) -> None:
                server._bump_media_url_token()
                controller.ingest_primary_video(str(payload["path"]))
                _preview_path, proxied, _reason, audio_codec = server._prepare_browser_media(
                    Path(controller.project.primary_video.path)
                )
                if proxied:
                    controller.status_message = _append_browser_preview_status(
                        controller.status_message,
                        audio_codec,
                    )

            def _import_secondary(self, payload: dict[str, Any]) -> None:
                server._bump_media_url_token()
                controller.add_merge_source(str(payload["path"]))

            def _import_merge(self, payload: dict[str, Any]) -> None:
                server._bump_media_url_token()
                controller.add_merge_source(str(payload["path"]))

            def _remove_merge_source(self, payload: dict[str, Any]) -> None:
                source_id = payload.get("source_id") or payload.get("id")
                if source_id in {None, ""}:
                    raise ValueError("source_id is required")
                server._bump_media_url_token()
                controller.remove_merge_source(str(source_id))

            def _set_threshold(self, payload: dict[str, Any]) -> None:
                controller.set_detection_threshold(float(payload["threshold"]))

            def _set_shotml_settings(self, payload: dict[str, Any]) -> None:
                settings = payload.get("settings", payload)
                if not isinstance(settings, dict):
                    raise ValueError("settings object is required")
                controller.set_shotml_settings(
                    settings,
                    rerun=bool(payload.get("rerun", False)),
                    update_app_defaults=bool(payload.get("update_app_defaults", False)),
                )

            def _generate_shotml_proposals(self, payload: dict[str, Any]) -> None:
                controller.generate_timing_change_proposals()

            def _apply_shotml_proposal(self, payload: dict[str, Any]) -> None:
                controller.apply_timing_change_proposal(str(payload["proposal_id"]))

            def _discard_shotml_proposal(self, payload: dict[str, Any]) -> None:
                controller.discard_timing_change_proposal(str(payload["proposal_id"]))

            def _reset_shotml_defaults(self, payload: dict[str, Any]) -> None:
                controller.reset_shotml_settings()

            def _reset_settings_defaults(self, payload: dict[str, Any]) -> None:
                controller.restore_defaults()

            def _set_settings_defaults(self, payload: dict[str, Any]) -> None:
                controller.set_settings_defaults(
                    payload.get("settings", payload) if isinstance(payload.get("settings", payload), dict) else {},
                    scope=str(payload.get("scope", "app") or "app"),
                )

            def _set_beep(self, payload: dict[str, Any]) -> None:
                controller.set_beep_time(int(payload["time_ms"]))

            def _add_shot(self, payload: dict[str, Any]) -> None:
                controller.add_shot(int(payload["time_ms"]))

            def _move_shot(self, payload: dict[str, Any]) -> None:
                controller.move_shot(
                    str(payload["shot_id"]),
                    int(payload["time_ms"]),
                    preserve_following_splits=bool(payload.get("preserve_following_splits")),
                )

            def _restore_shot(self, payload: dict[str, Any]) -> None:
                controller.restore_original_shot_timing(
                    str(payload["shot_id"]),
                    preserve_following_splits=bool(payload.get("preserve_following_splits")),
                )

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
                    controller.set_scoring_color(str(letter), str(color))

            def _set_popups(self, payload: dict[str, Any]) -> None:
                controller.set_popups(payload)

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
                    None if payload.get("opacity") in {None, ""} else float(payload["opacity"]),
                )
                if payload.get("sync_offset_ms") not in {None, ""}:
                    controller.set_merge_source_sync_offset(str(source_id), int(payload["sync_offset_ms"]))

            def _reset_merge_defaults(self, payload: dict[str, Any]) -> None:
                controller.reset_merge_defaults()

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
