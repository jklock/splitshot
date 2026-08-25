"""Browser HTTP server, route handlers, and file/session plumbing for SplitShot."""

from __future__ import annotations

import csv
import errno
import json
import mimetypes
import re
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import closing
from copy import deepcopy
from dataclasses import dataclass
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
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
    _shot_from_dict,
    _timing_event_from_dict,
)
from splitshot.media.ffmpeg import resolve_media_binary, run_ffmpeg, run_ffprobe_json
from splitshot.persistence.projects import (
    missing_required_project_dirs,
    normalize_project_path,
    resolve_project_path,
)
from splitshot.ui.controller import VALID_OVERLAY_BADGE_NAMES, ProjectController

EXPECTED_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
EXPECTED_DISCONNECT_ERRNOS = {errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ENOBUFS}
PathChooser = Callable[..., str | None]
COMMON_VIDEO_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.avi *.wmv *.webm *.mkv *.mpg *.mpeg *.mts *.m2ts"
COMMON_IMAGE_FILE_PATTERNS = "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.tif *.tiff"
COMMON_EXPORT_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.mkv"
_PCM_BROWSER_PROXY_FORMATS = {"mov", "mp4", "m4a", "3gp", "3g2", "mj2"}
_PCM_BROWSER_PROXY_SUFFIXES = {".mov", ".qt", ".mp4", ".m4v", ".m4a"}
_BROWSER_COPY_SAFE_VIDEO_CODECS = {"av1", "h264", "vp8", "vp9"}
MAX_BROWSER_UPLOAD_BYTES = 8 * 1024 * 1024 * 1024
_BROWSER_CONTENT_SECURITY_POLICY = (
    "default-src 'none'; "
    "base-uri 'none'; "
    "frame-ancestors 'none'; "
    "form-action 'self'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; "
    "media-src 'self' blob:; "
    "connect-src 'self'; "
    "font-src 'self' data:; "
    "object-src 'none'"
)


def prepare_export_runtime() -> None:
    from splitshot.export.pipeline import prepare_export_runtime as _prepare_export_runtime

    _prepare_export_runtime()


def export_project(*args: Any, **kwargs: Any) -> Any:
    from splitshot.export.pipeline import export_project as _export_project

    return _export_project(*args, **kwargs)


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


def _browser_audio_proxy_reason(
    path: Path, metadata: dict[str, Any]
) -> tuple[str | None, str | None]:
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
    if path.suffix.lower() in _PCM_BROWSER_PROXY_SUFFIXES or format_names.intersection(
        _PCM_BROWSER_PROXY_FORMATS
    ):
        return "pcm_audio_in_mov_mp4", audio_codec
    return None, audio_codec


def _browser_preview_output_path(session_path: Path, source_path: Path) -> Path:
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", source_path.stem).strip("._") or "preview"
    return session_path / f"{uuid4().hex}_{safe_stem}_browser.mp4"


def _browser_preview_command(
    source_path: Path, preview_path: Path, metadata: dict[str, Any]
) -> list[str]:
    streams = metadata.get("streams", [])
    video_stream = next(
        (item for item in streams if isinstance(item, dict) and item.get("codec_type") == "video"),
        None,
    )
    video_codec = (
        str(video_stream.get("codec_name", "")).lower() if isinstance(video_stream, dict) else ""
    )
    video_args = (
        ["-c:v", "copy"]
        if video_codec in _BROWSER_COPY_SAFE_VIDEO_CODECS
        else [
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-preset",
            "ultrafast",
        ]
    )
    return [
        "-i",
        str(source_path),
        "-map",
        "0:v:0",
        *video_args,
        "-an",
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
    if (
        start_pts_source is not None
        and start_pts_preview is not None
        and start_pts_source != start_pts_preview
    ):
        return False

    source_frames = _int_metadata_value(source_timeline.get("nb_frames"))
    preview_frames = _int_metadata_value(preview_timeline.get("nb_frames"))
    return source_frames is None or preview_frames is None or source_frames == preview_frames


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
    # FFprobe packet flags can change after a browser-compatibility remux even when
    # the copied video packet timeline remains exact. Compare timing only.
    return _video_packet_timeline_rows(
        _ffprobe_video_packet_csv(source_path)
    ) == _video_packet_timeline_rows(_ffprobe_video_packet_csv(preview_path))


def _validate_browser_preview_timeline(
    source_path: Path,
    source_metadata: dict[str, Any],
    preview_path: Path,
) -> tuple[bool, dict[str, str], dict[str, str]]:
    preview_metadata = run_ffprobe_json(preview_path)
    source_timeline = _browser_video_timeline_signature(source_metadata)
    preview_timeline = _browser_video_timeline_signature(preview_metadata)
    metadata_match = _browser_preview_matches_source_timeline(source_timeline, preview_timeline)
    source_codec = source_timeline.get("codec_name", "").lower()
    preview_codec = preview_timeline.get("codec_name", "").lower()
    if metadata_match and source_codec in _BROWSER_COPY_SAFE_VIDEO_CODECS:
        return (
            preview_codec == source_codec,
            source_timeline,
            preview_timeline,
        )
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


def choose_local_path(
    kind: str, current: str | None = None, default_root: str | None = None
) -> str | None:
    if sys.platform == "darwin":
        return choose_local_path_macos(kind, current, default_root)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:  # noqa: BLE001
        return None

    initial_dir = str(
        _existing_dialog_directory(
            default_root or current,
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
        if kind in {
            "primary",
            "secondary",
            "queue_media",
            "in_out_media",
            "popup_image",
            "practiscore",
        }:
            return filedialog.askopenfilename(
                title=(
                    "Choose stage video"
                    if kind == "primary"
                    else (
                        "Choose Intro / Outro video"
                        if kind in {"queue_media", "in_out_media"}
                        else (
                            "Choose secondary angle video"
                            if kind == "secondary"
                            else (
                                "Choose marker image"
                                if kind == "popup_image"
                                else "Choose PractiScore results"
                            )
                        )
                    )
                ),
                initialdir=initial_dir,
                filetypes=(
                    [("PractiScore results", "*.csv *.txt"), ("All files", "*.*")]
                    if kind == "practiscore"
                    else [
                        ("Image files", COMMON_IMAGE_FILE_PATTERNS),
                        ("Video files", COMMON_VIDEO_FILE_PATTERNS),
                        ("All files", "*.*"),
                    ]
                ),
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


def choose_local_path_macos(
    kind: str, current: str | None = None, default_root: str | None = None
) -> str | None:
    default_dir = _existing_dialog_directory(
        default_root or current,
        project_path=kind in {"project", "project_save", "project_open", "project_folder"},
    )
    default_name = "output.mp4"
    if kind in {
        "primary",
        "secondary",
        "queue_media",
        "in_out_media",
        "popup_image",
        "practiscore",
    }:
        prompt = (
            "Choose stage video"
            if kind == "primary"
            else (
                "Choose Intro / Outro video"
                if kind in {"queue_media", "in_out_media"}
                else (
                    "Choose secondary angle video"
                    if kind == "secondary"
                    else (
                        "Choose marker image"
                        if kind == "popup_image"
                        else "Choose PractiScore results"
                    )
                )
            )
        )
        script = "\n".join(
            [
                (
                    f"set chosenFile to choose file with prompt {_applescript_string(prompt)} "
                    f"default location POSIX file {_applescript_string(str(default_dir))}"
                ),
                "POSIX path of chosenFile",
            ]
        )
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=False
        )
        if result.returncode == 0:
            return result.stdout.strip()
        if "User canceled" in result.stderr:
            return None
        raise RuntimeError(result.stderr.strip() or "Native file browser failed.")
    if kind in {"project", "project_save", "project_open", "project_folder"}:
        script = "\n".join(
            [
                (
                    "set chosenFolder to choose folder with prompt "
                    f"{_applescript_string('Choose SplitShot project folder')} "
                    f"default location POSIX file {_applescript_string(str(default_dir))}"
                ),
                "POSIX path of chosenFolder",
            ]
        )
        result = subprocess.run(
            ["osascript", "-e", script], capture_output=True, text=True, check=False
        )
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
            (
                f"set chosenFile to choose file name with prompt {_applescript_string(prompt)} "
                f"default name {_applescript_string(default_name)} "
                f"default location POSIX file {_applescript_string(str(default_dir))}"
            ),
            "POSIX path of chosenFile",
        ]
    )
    result = subprocess.run(
        ["osascript", "-e", script], capture_output=True, text=True, check=False
    )
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


def reveal_local_folder(path: str | Path) -> None:
    folder = Path(path).expanduser().resolve()
    if not folder.is_dir():
        raise ValueError(f"Project folder does not exist: {folder}")
    command = (
        ["open", str(folder)]
        if sys.platform == "darwin"
        else (["explorer", str(folder)] if sys.platform == "win32" else ["xdg-open", str(folder)])
    )
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Could not open the project folder.")


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
        "audio_output_level_percent": export.audio_output_level_percent,
        "color_space": export.color_space.value,
        "two_pass": export.two_pass,
        "multi_track": export.multi_track,
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
        elif key == "audio_output_level_percent":
            normalized = max(0, min(300, int(value)))
        elif key in {"two_pass", "multi_track"}:
            normalized = bool(value)
        else:
            normalized = str(value)
        if normalized != current:
            return False
    return True


def _sync_export_payload(controller: ProjectController, payload: dict[str, Any]) -> None:
    selected_preset = str(payload.get("preset") or controller.project.export.preset.value)
    if selected_preset == "custom":
        if not _payload_matches_export_state(controller.project, payload):
            controller.set_export_settings(payload)
        return
    controller.apply_export_preset(selected_preset)
    if not _payload_matches_export_state(controller.project, payload):
        controller.set_export_settings(payload)


def find_free_port(host: str = "127.0.0.1", desired: int = 8765, max_attempts: int = 10) -> int:
    for attempt in range(max_attempts):
        port = desired + attempt
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No free port found on {host} in range {desired}-{desired + max_attempts - 1}")


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
        self._processing_lock = threading.Lock()
        self._processing_job: dict[str, Any] = {}
        self._processing_activity_last_at = 0.0
        self._processing_activity_last_phase = ""
        self._session_dir = TemporaryDirectory(prefix="splitshot-browser-")
        self._session_path = Path(self._session_dir.name)
        self._display_names: dict[str, str] = {}
        self._browser_media_cache: dict[str, BrowserMediaCacheEntry] = {}
        self._browser_media_lock = threading.Lock()
        self._media_url_token = uuid4().hex
        self.practiscore_session = PractiScoreSessionManager()
        prepare_export_runtime()
        self.activity.log(
            "server.initialized", host=host, port=port, log_path=str(self.activity.path)
        )

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

    def _begin_processing_job(self, path: str, mode: str) -> None:
        with self._processing_lock:
            self._processing_activity_last_at = 0.0
            self._processing_activity_last_phase = ""
            self._processing_job = {
                "id": uuid4().hex,
                "path": path,
                "mode": mode,
                "active": True,
                "status": "processing",
                "message": "Processing combined queue..."
                if mode == "combined"
                else "Processing queue...",
                "detail": "Rendering queued stages locally",
                "progress": 0.0,
                "stage_label": "",
                "stage_index": 0,
                "stage_count": 0,
                "phase": "render",
                "log_seq": 0,
                "logs": [],
                "error": "",
            }

    def _update_processing_job(self, detail: dict[str, Any]) -> bool:
        with self._processing_lock:
            if not self._processing_job:
                return False
            self._processing_job.update(
                {
                    key: detail[key]
                    for key in (
                        "progress",
                        "stage_label",
                        "stage_index",
                        "stage_count",
                        "phase",
                    )
                    if key in detail
                }
            )
            phase = str(detail.get("phase") or "render")
            label = str(detail.get("stage_label") or "queue")
            if phase == "combine":
                self._processing_job["message"] = "Finalizing combined output..."
                self._processing_job["detail"] = "Concatenating, fading, and validating"
            else:
                self._processing_job["message"] = f"Processing {label}..."
                self._processing_job["detail"] = (
                    f"Stage {detail.get('stage_index', 0)} of {detail.get('stage_count', 0)}"
                )
            now = time.monotonic()
            should_log = (
                phase != self._processing_activity_last_phase
                or phase in {"complete", "failed"}
                or now - self._processing_activity_last_at >= 0.25
            )
            if should_log:
                self._processing_activity_last_at = now
                self._processing_activity_last_phase = phase
            return should_log

    def _append_processing_log(self, line: str) -> None:
        normalized = str(line or "").rstrip()
        if not normalized:
            return
        with self._processing_lock:
            if not self._processing_job:
                return
            self._processing_job["log_seq"] = int(self._processing_job["log_seq"]) + 1
            logs = self._processing_job["logs"]
            logs.append({"seq": self._processing_job["log_seq"], "line": normalized})
            if len(logs) > 20000:
                del logs[:-20000]

    def _finish_processing_job(self, *, status: str, error: str = "") -> None:
        with self._processing_lock:
            if not self._processing_job:
                return
            self._processing_job["active"] = False
            self._processing_job["status"] = "failed" if error else "complete"
            self._processing_job["progress"] = (
                1.0 if not error else self._processing_job.get("progress", 0.0)
            )
            self._processing_job["message"] = status
            self._processing_job["detail"] = "Ready" if not error else "Processing failed"
            self._processing_job["error"] = error

    def _processing_snapshot(self, after_log: int = 0) -> dict[str, Any]:
        with self._processing_lock:
            if not self._processing_job:
                return {}
            job = self._processing_job
            return {
                key: deepcopy(job[key])
                for key in (
                    "id",
                    "path",
                    "mode",
                    "active",
                    "status",
                    "message",
                    "detail",
                    "progress",
                    "stage_label",
                    "stage_index",
                    "stage_count",
                    "phase",
                    "log_seq",
                    "error",
                )
            } | {
                "logs": [
                    deepcopy(item) for item in job["logs"] if int(item.get("seq", 0)) > after_log
                ]
            }

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
        timeline_valid, source_timeline, preview_timeline = _validate_browser_preview_timeline(
            path, metadata, preview_path
        )
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
            cached_paths = [
                entry.preview_path
                for entry in self._browser_media_cache.values()
                if entry.preview_path
            ]
            self._browser_media_cache.clear()
        for preview_path in cached_paths:
            Path(preview_path).unlink(missing_ok=True)

    def _active_browser_media_paths(self) -> tuple[Path, ...]:
        candidates: list[Path] = []
        primary_path = self.controller.effective_primary_media_path()
        if primary_path:
            candidates.append(Path(primary_path))
        secondary_path = (
            ""
            if self.controller.project.secondary_video is None
            else self.controller.project.secondary_video.path
        )
        if secondary_path:
            candidates.append(Path(secondary_path))
        for source in self.controller.project.merge_sources:
            active_path = self.controller.effective_merge_source_media_path(source.id)
            if active_path:
                candidates.append(Path(active_path))
        unique: list[Path] = []
        seen: set[str] = set()
        for path in candidates:
            try:
                resolved = str(path.expanduser().resolve())
            except FileNotFoundError:
                resolved = str(path)
            if resolved in seen:
                continue
            seen.add(resolved)
            unique.append(path)
        return tuple(unique)

    def _primary_browser_media_paths(self) -> tuple[Path, ...]:
        primary_path = self.controller.effective_primary_media_path()
        if not primary_path:
            return ()
        path = Path(primary_path)
        return (path,) if path.exists() and path.is_file() else ()

    def _prewarm_media_paths(self, paths: tuple[Path, ...]) -> None:
        if not self.browser_media_proxy_enabled:
            return
        if not paths:
            return

        max_workers = min(4, len(paths))

        def prepare(path: Path) -> tuple[Path, str | None]:
            if not path.exists() or not path.is_file():
                return path, None
            try:
                self._prepare_browser_media(path)
            except Exception as exc:  # noqa: BLE001
                return path, str(exc)
            return path, None

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(prepare, path) for path in paths]
            for future in as_completed(futures):
                path, error = future.result()
                if error:
                    self.activity.log("media.prewarm.error", path=str(path), error=error)

    def prewarm_primary_media(self) -> None:
        self._prewarm_media_paths(self._primary_browser_media_paths())

    def prewarm_active_media(self) -> None:
        self._prewarm_media_paths(self._active_browser_media_paths())

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

            def log_message(self, format: str, *args: Any) -> None:
                return

            def do_GET(self) -> None:
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
                    active_primary_path = controller.effective_primary_media_path()
                    if not active_primary_path:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._send_media(Path(active_primary_path))
                    return
                if request_path == "/media/secondary":
                    active_path = controller.effective_merge_source_media_path(
                        controller.project.analysis.analyzed_secondary_source_id
                    )
                    fallback_path = (
                        ""
                        if controller.project.secondary_video is None
                        else controller.project.secondary_video.path
                    )
                    if not active_path and not fallback_path:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._send_media(Path(active_path or fallback_path))
                    return
                if request_path in {"/media/intro", "/media/outro"}:
                    kind = request_path.removeprefix("/media/")
                    boundary_path = getattr(controller.project, f"{kind}_clip").asset.path
                    if not boundary_path:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._send_media(Path(boundary_path))
                    return
                if request_path.startswith("/media/merge/"):
                    self._send_merge_media(request_path.removeprefix("/media/merge/"))
                    return
                if request_path.startswith("/media/popup/"):
                    self._send_popup_media(request_path.removeprefix("/media/popup/"))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def do_POST(self) -> None:
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
                primary_media_prewarm_routes = {
                    "/api/project/open",
                    "/api/project/select-stage",
                    "/api/project/stage/import-primary",
                    "/api/project/stage/set-primary",
                    "/api/project/stage/clear-primary",
                    "/api/import/primary",
                }
                active_media_prewarm_routes = {
                    "/api/project/stage/import-added",
                    "/api/project/stage/remove-added",
                    "/api/import/secondary",
                    "/api/import/merge",
                    "/api/merge/remove",
                    "/api/primary/trim",
                    "/api/merge/source/trim",
                    "/api/merge/source/trim-all",
                    "/api/swap",
                }
                routes: dict[str, Callable[[dict[str, Any]], None]] = {
                    "/api/project/details": self._set_project_details,
                    "/api/project/practiscore": self._set_practiscore_context,
                    "/api/project/ui-state": self._set_project_ui_state,
                    "/api/project/new": self._new_project,
                    "/api/project/open": self._open_project,
                    "/api/project/save": self._save_project,
                    "/api/project/delete": self._delete_project,
                    "/api/project/reveal": self._reveal_project,
                    "/api/project/output/reveal": self._reveal_output,
                    "/api/import/practiscore": self._import_practiscore,
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
                    "/api/merge/source/analyze": self._analyze_merge_source,
                    "/api/primary/trim": self._trim_primary_video,
                    "/api/merge/source/trim": self._trim_merge_source,
                    "/api/merge/source/trim-all": self._trim_all_merge_sources,
                    "/api/output-profiles/list": self._list_output_profiles,
                    "/api/output-profiles/create": self._create_output_profile,
                    "/api/output-profiles/update": self._update_output_profile,
                    "/api/output-profiles/apply": self._apply_output_profile,
                    "/api/output-profiles/delete": self._delete_output_profile,
                    "/api/output-profiles/render": self._render_output_profile,
                    "/api/overlay": self._set_overlay,
                    "/api/popups": self._set_popups,
                    "/api/merge": self._set_merge,
                    "/api/sync": self._set_sync,
                    "/api/swap": self._swap_videos,
                    "/api/export/settings": self._set_export_settings,
                    "/api/export/preset": self._set_export_preset,
                    "/api/export": self._export_project,
                    "/api/project/select-stage": self._select_stage,
                    "/api/project/stage/create": self._create_stage,
                    "/api/project/stage/delete": self._delete_stage,
                    "/api/project/stage/update": self._update_stage_metadata,
                    "/api/project/stage/import-primary": self._import_stage_primary,
                    "/api/project/stage/import-added": self._import_stage_added,
                    "/api/project/stage/set-primary": self._set_stage_primary,
                    "/api/project/stage/clear-primary": self._clear_stage_primary,
                    "/api/project/stage/remove-added": self._remove_stage_added,
                    "/api/project/stage/global-settings-primary": self._set_global_settings_primary,
                    "/api/project/stage/ignore-global-settings": self._ignore_global_settings,
                    "/api/project/queue/add": self._add_to_queue,
                    "/api/project/queue/add-all": self._add_all_to_queue,
                    "/api/project/queue/remove": self._remove_from_queue,
                    "/api/project/queue/apply-all": self._apply_settings_to_all,
                    "/api/project/queue/settings": self._set_queue_settings,
                    "/api/project/in-out/media": self._set_in_out_media,
                    "/api/project/queue/media": self._set_in_out_media,
                    "/api/project/intro-outro/fades": self._set_intro_outro_fades,
                    "/api/project/intro-outro/overlay": self._set_intro_outro_overlay,
                    "/api/project/queue/process": self._process_queue,
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
                    if self.path in active_media_prewarm_routes:
                        server.prewarm_active_media()
                    elif self.path in primary_media_prewarm_routes:
                        server.prewarm_primary_media()
                    if "/api/settings/reset-defaults" in self.path:
                        import sys as _sys

                        _merge_layout = (
                            controller.project.merge.layout
                            if hasattr(controller, "project") and controller.project
                            else "NO_PROJECT"
                        )
                        print(
                            f"[DEBUG] reset-defaults: project.merge.layout = {_merge_layout}",
                            file=_sys.stderr,
                        )
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

            def _send_json(
                self, payload: dict[str, Any], status: HTTPStatus = HTTPStatus.OK
            ) -> None:
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
                    current = (
                        None if payload.get("current") in {"", None} else str(payload["current"])
                    )
                    activity.log("api.dialog.path.start", kind=kind, current=current)
                    default_root = (
                        None
                        if payload.get("default_root") in {None, ""}
                        else str(payload["default_root"])
                    )
                    try:
                        selected_path = path_chooser(kind, current, default_root) or ""
                    except TypeError:
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
                    activity.log(
                        "api.project.probe.start", path=target, normalized_path=normalized_target
                    )
                    has_project_file = controller.project_folder_has_project_file(normalized_target)
                    missing_dirs = missing_required_project_dirs(normalized_target)
                    activity.log(
                        "api.project.probe.success",
                        path=target,
                        normalized_path=normalized_target,
                        has_project_file=has_project_file,
                        missing_dirs=missing_dirs,
                    )
                    self._send_json(
                        {
                            "path": target,
                            "normalized_path": str(normalize_project_path(normalized_target)),
                            "has_project_file": has_project_file,
                            "missing_required_dirs": missing_dirs,
                        }
                    )
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.project.probe.error", error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def _poll_activity(self, query_string: str) -> None:
                params = parse_qs(query_string or "", keep_blank_values=False)
                raw_after = params.get("after", ["0"])[0]
                raw_limit = params.get("limit", ["400"])[0]
                try:
                    after_seq = max(0, int(raw_after))
                except ValueError:
                    after_seq = 0
                try:
                    limit = max(0, int(raw_limit))
                except ValueError:
                    limit = 400
                raw_job_after = params.get("job_after", ["0"])[0]
                try:
                    job_after = max(0, int(raw_job_after))
                except ValueError:
                    job_after = 0
                payload = activity.snapshot(after_seq=after_seq, limit=limit)
                payload["processing"] = server._processing_snapshot(after_log=job_after)
                self._send_json(payload)

            def _browser_state(self) -> dict[str, Any]:
                controller._sync_project_to_active_stage()
                payload = browser_state(
                    controller.project,
                    controller.status_message,
                    settings=controller.effective_settings().to_dict(),
                    settings_layers=controller.settings_layers(),
                    practiscore_options=controller.practiscore_browser_state(),
                    media_cache_token=server._media_url_token,
                    output_profiles=controller.list_output_profiles(),
                )
                primary_path = controller.effective_primary_media_path()
                secondary_path = (
                    ""
                    if controller.project.secondary_video is None
                    else controller.project.secondary_video.path
                )
                payload["media"]["primary_display_name"] = display_names.get(
                    primary_path,
                    display_name_for_path(primary_path, "No Video Selected"),
                )
                payload["media"]["primary_original_display_name"] = display_names.get(
                    controller.project.primary_video.path,
                    display_name_for_path(
                        controller.project.primary_video.path, "No Video Selected"
                    ),
                )
                payload["media"]["secondary_display_name"] = display_names.get(
                    secondary_path,
                    display_name_for_path(secondary_path, "None"),
                )
                payload["project"]["path"] = (
                    "" if controller.project_path is None else str(controller.project_path)
                )
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
                    activity.log(
                        "api.practiscore.dashboard.open.error", error="browser open returned false"
                    )
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
                self._send_json(
                    {
                        "status": "Opened PractiScore dashboard in your browser.",
                        "url": dashboard_url,
                    }
                )

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
                    description=None
                    if payload.get("description") in {None, ""}
                    else str(payload["description"]),
                    output_root=None
                    if payload.get("output_root") in {None, ""}
                    else str(payload.get("output_root", "")),
                )

            def _set_practiscore_context(self, payload: dict[str, Any]) -> None:
                controller.set_practiscore_context(
                    match_type=None
                    if "match_type" not in payload
                    else str(payload.get("match_type", "")),
                    stage_number=(
                        None
                        if "stage_number" not in payload
                        else 0
                        if payload.get("stage_number") in {None, ""}
                        else int(payload["stage_number"])
                    ),
                    competitor_name=(
                        str(payload.get("competitor_name", ""))
                        if "competitor_name" in payload
                        else None
                    ),
                    competitor_place=(
                        None
                        if "competitor_place" not in payload
                        else 0
                        if payload.get("competitor_place") in {None, ""}
                        else int(payload["competitor_place"])
                    ),
                    classification=(
                        str(payload.get("classification", ""))
                        if "classification" in payload
                        else None
                    ),
                    division=(str(payload.get("division", "")) if "division" in payload else None),
                )

            def _update_stage_metadata(self, payload: dict[str, Any]) -> None:
                raw_competitor_place = payload.get("competitor_place")
                controller.update_stage_metadata(
                    str(payload.get("stage_id", "")),
                    label=None
                    if payload.get("label") in {None, ""}
                    else str(payload.get("label", "")),
                    stage_number=(
                        ""
                        if payload.get("stage_number") == ""
                        else None
                        if payload.get("stage_number") is None
                        else int(payload["stage_number"])
                    ),
                    competitor_name=(
                        None
                        if payload.get("competitor_name") in {None, ""}
                        else str(payload.get("competitor_name", ""))
                    ),
                    competitor_place=(
                        ""
                        if raw_competitor_place == ""
                        else None
                        if raw_competitor_place in {None, ""}
                        else int(raw_competitor_place)
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
                guessed = (
                    content_type or mimetypes.guess_type(safe_name)[0] or "application/octet-stream"
                )
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
                        activity.log(
                            "media.range_invalid", path=str(requested_path), start=start, end=end
                        )
                        self.send_error(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                        return
                    content_length = end - start + 1
                    guessed_content_type = mimetypes.guess_type(served_path.name)[0]
                    if content_type and guessed_content_type in {None, "audio/x-wav"}:
                        resolved_content_type = content_type
                    else:
                        resolved_content_type = (
                            guessed_content_type or content_type or "application/octet-stream"
                        )
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
                activity.log(
                    f"{event_prefix}.complete",
                    path=str(served_path),
                    bytes=content_length,
                    proxied=proxied,
                )

            def _send_media(self, path: Path) -> None:
                if not path.exists() or not path.is_file():
                    activity.log("media.missing", path=str(path))
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                served_path = path
                proxied = False
                proxy_reason = None
                try:
                    served_path, proxied, proxy_reason, _audio_codec = (
                        server._prepare_browser_media(path)
                    )
                except Exception as exc:  # noqa: BLE001
                    activity.log("media.compatibility.error", source_path=str(path), error=str(exc))
                    served_path = path
                    proxied = False
                    proxy_reason = None
                self._send_file_response(
                    path,
                    served_path,
                    proxied=proxied,
                    proxy_reason=proxy_reason,
                    event_prefix="media",
                    content_type="video/mp4",
                )

            def _send_merge_media(self, source_id: str) -> None:
                active_path = controller.effective_merge_source_media_path(source_id)
                if not active_path:
                    activity.log("media.missing", source_id=source_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_media(Path(active_path))

            def _send_popup_media(self, popup_id: str) -> None:
                popup = next(
                    (item for item in controller.project.popups if item.id == popup_id), None
                )
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
                        activity.log(
                            "browser.activity",
                            browser_event=event,
                            detail=detail,
                            browser_ts=entry.get("ts"),
                        )
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
                        _preview_path, proxied, _reason, audio_codec = (
                            server._prepare_browser_media(
                                Path(controller.project.primary_video.path)
                            )
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

            def _reveal_project(self, payload: dict[str, Any]) -> None:
                if controller.project_path is None:
                    raise ValueError("Project path is required")
                reveal_local_folder(controller.project_path)
                controller.status_message = f"Opened project folder {controller.project_path}."

            def _reveal_output(self, payload: dict[str, Any]) -> None:
                output_dir = controller.output_dir()
                reveal_local_folder(output_dir)
                controller.status_message = f"Opened output folder {output_dir}."

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

            def _import_practiscore(self, payload: dict[str, Any]) -> None:
                path = str(payload.get("path", "")).strip()
                if not path:
                    raise ValueError("PractiScore results path is required")
                controller.import_practiscore_file(path, source_name=Path(path).name)

            def _import_secondary(self, payload: dict[str, Any]) -> None:
                server._bump_media_url_token()
                controller.add_merge_source(str(payload["path"]))
                controller.set_merge_enabled(True)

            def _import_merge(self, payload: dict[str, Any]) -> None:
                server._bump_media_url_token()
                controller.add_merge_source(str(payload["path"]))
                controller.set_merge_enabled(True)

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
                    raise ValueError("settings object is required")  # noqa: TRY004
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
                controller.reset_settings_defaults(
                    scope=str(payload.get("scope", "app") or "app"),
                    section=(str(payload.get("section") or "").strip() or None),
                )

            def _set_settings_defaults(self, payload: dict[str, Any]) -> None:
                controller.set_settings_defaults(
                    payload.get("settings", payload)
                    if isinstance(payload.get("settings", payload), dict)
                    else {},
                    scope=str(payload.get("scope", "app") or "app"),
                    section=(str(payload.get("section") or "").strip() or None),
                    capture_current_project=bool(payload.get("project_defaults", False)),
                )

            def _set_beep(self, payload: dict[str, Any]) -> None:
                time_ms = payload.get("time_ms")
                controller.set_beep_time(int(time_ms) if time_ms is not None else None)

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
                        {str(key): float(value) for key, value in payload["penalty_counts"].items()}
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
                    else {str(key): float(value) for key, value in dict(penalty_counts).items()},
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
                    str(
                        payload.get("style_type")
                        if payload.get("style_type") not in {None, ""}
                        else controller.project.overlay.style_type
                    ),
                    int(
                        payload.get("spacing")
                        if payload.get("spacing") not in {None, ""}
                        else controller.project.overlay.spacing
                    ),
                    int(
                        payload.get("margin")
                        if payload.get("margin") not in {None, ""}
                        else controller.project.overlay.margin
                    ),
                )
                styles = payload.get("styles")
                if isinstance(styles, dict):
                    for badge_name in styles:
                        if badge_name not in VALID_OVERLAY_BADGE_NAMES:
                            raise ValueError(f"Unknown badge style: {badge_name}")
                scoring_colors = payload.get("scoring_colors")
                if isinstance(scoring_colors, dict):
                    for score_key in scoring_colors:
                        if "|" in str(score_key):
                            raise ValueError("score color keys must be individual tokens")
                controller.set_overlay_display_options(payload)

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
                    controller.adjust_merge_source_sync_offset(
                        str(source_id), int(payload["sync_delta_ms"])
                    )
                    return
                controller.set_merge_source_position(
                    str(source_id),
                    None
                    if payload.get("pip_size_percent") in {None, ""}
                    else int(payload["pip_size_percent"]),
                    None if payload.get("pip_x") in {None, ""} else float(payload["pip_x"]),
                    None if payload.get("pip_y") in {None, ""} else float(payload["pip_y"]),
                    None if payload.get("opacity") in {None, ""} else float(payload["opacity"]),
                    None
                    if payload.get("camera_role") in {None, ""}
                    else str(payload["camera_role"]),
                    None
                    if (
                        payload.get("placement_mode") in {None, ""}
                        and not isinstance(payload.get("placement"), dict)
                    )
                    else str(
                        payload.get("placement_mode")
                        or (payload.get("placement") or {}).get("mode")
                        or ""
                    ),
                )
                if payload.get("sync_offset_ms") not in {None, ""}:
                    controller.set_merge_source_sync_offset(
                        str(source_id), int(payload["sync_offset_ms"])
                    )

            def _analyze_merge_source(self, payload: dict[str, Any]) -> None:
                source_id = payload.get("source_id") or payload.get("id")
                if source_id in {None, ""}:
                    raise ValueError("source_id is required")
                controller.rerun_merge_source_analysis(str(source_id))

            def _trim_merge_source(self, payload: dict[str, Any]) -> None:
                source_id = payload.get("source_id") or payload.get("id")
                if source_id in {None, ""}:
                    raise ValueError("source_id is required")
                clear = bool(payload.get("clear", False))
                start_s = payload.get("start_s")
                end_s = payload.get("end_s")
                controller.trim_merge_source(
                    str(source_id),
                    start_s=float(start_s) if start_s not in {None, ""} else None,
                    end_s=float(end_s) if end_s not in {None, ""} else None,
                    clear=clear,
                )
                server._clear_browser_media_cache()
                server._bump_media_url_token()

            def _trim_primary_video(self, payload: dict[str, Any]) -> None:
                clear = bool(payload.get("clear", False))
                start_s = payload.get("start_s")
                end_s = payload.get("end_s")
                controller.trim_primary_video(
                    start_s=float(start_s) if start_s not in {None, ""} else None,
                    end_s=float(end_s) if end_s not in {None, ""} else None,
                    clear=clear,
                )
                server._clear_browser_media_cache()
                server._bump_media_url_token()

            def _trim_all_merge_sources(self, payload: dict[str, Any]) -> None:
                clear = bool(payload.get("clear", False))
                start_s = payload.get("start_s")
                end_s = payload.get("end_s")
                keep_before_beep_s = payload.get("keep_before_beep_s")
                keep_after_last_shot_s = payload.get("keep_after_last_shot_s")
                normalized_start_s = float(start_s) if start_s not in {None, ""} else None
                normalized_end_s = float(end_s) if end_s not in {None, ""} else None
                normalized_keep_before_s = (
                    float(keep_before_beep_s) if keep_before_beep_s not in {None, ""} else None
                )
                normalized_keep_after_s = (
                    float(keep_after_last_shot_s)
                    if keep_after_last_shot_s not in {None, ""}
                    else None
                )
                stage_ids = payload.get("stage_ids")
                if isinstance(stage_ids, list):
                    controller.trim_selected_stages(
                        [str(stage_id) for stage_id in stage_ids],
                        start_s=normalized_start_s,
                        end_s=normalized_end_s,
                        keep_before_beep_s=normalized_keep_before_s,
                        keep_after_last_shot_s=normalized_keep_after_s,
                        clear=clear,
                        progress_callback=lambda detail: activity.log(
                            "api.trim.progress", **detail
                        ),
                        log_callback=lambda line: activity.log("api.process.log", line=line),
                    )
                else:
                    controller.trim_all_merge_sources(
                        start_s=normalized_start_s,
                        end_s=normalized_end_s,
                        keep_before_beep_s=normalized_keep_before_s,
                        keep_after_last_shot_s=normalized_keep_after_s,
                        clear=clear,
                        progress_callback=lambda detail: activity.log(
                            "api.trim.progress", **detail
                        ),
                        log_callback=lambda line: activity.log("api.process.log", line=line),
                    )
                server._clear_browser_media_cache()
                server._bump_media_url_token()

            def _list_output_profiles(self, payload: dict[str, Any]) -> None:
                pass

            def _create_output_profile(self, payload: dict[str, Any]) -> None:
                profile_name = str(payload.get("profile_name", "New Profile"))
                profile_kind = str(payload.get("profile_kind", "stage_output"))
                export_settings = payload.get("export_settings")
                controller.create_output_profile(
                    profile_name,
                    profile_kind,
                    export_settings if isinstance(export_settings, dict) else None,
                )

            def _update_output_profile(self, payload: dict[str, Any]) -> None:
                output_id = payload.get("output_id")
                if output_id in {None, ""}:
                    raise ValueError("output_id is required")
                updates = {k: v for k, v in payload.items() if k != "output_id"}
                result = controller.update_output_profile(str(output_id), **updates)
                if result is None:
                    raise ValueError(f"Output profile {output_id} not found")

            def _apply_output_profile(self, payload: dict[str, Any]) -> None:
                output_id = payload.get("output_id")
                if output_id in {None, ""}:
                    raise ValueError("output_id is required")
                controller.apply_output_profile(str(output_id))

            def _delete_output_profile(self, payload: dict[str, Any]) -> None:
                output_id = payload.get("output_id")
                if output_id in {None, ""}:
                    raise ValueError("output_id is required")
                if not controller.delete_output_profile(str(output_id)):
                    raise ValueError(f"Output profile {output_id} not found")

            def _render_output_profile(self, payload: dict[str, Any]) -> None:
                output_id = payload.get("output_id")
                if output_id in {None, ""}:
                    raise ValueError("output_id is required")
                controller.render_output_profile(str(output_id))

            def _reset_merge_defaults(self, payload: dict[str, Any]) -> None:
                controller.reset_merge_defaults()

            def _add_event(self, payload: dict[str, Any]) -> None:
                controller.add_timing_event(
                    kind=str(payload.get("kind", "reload")),
                    after_shot_id=None
                    if payload.get("after_shot_id") in {None, ""}
                    else str(payload["after_shot_id"]),
                    before_shot_id=None
                    if payload.get("before_shot_id") in {None, ""}
                    else str(payload["before_shot_id"]),
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
                popups_payload = payload.get("popups")
                popup_template_payload = payload.get("popup_template")
                if isinstance(popups_payload, list) or isinstance(popup_template_payload, dict):
                    next_popups_payload: dict[str, Any] = {}
                    if isinstance(popups_payload, list):
                        next_popups_payload["popups"] = popups_payload
                    if isinstance(popup_template_payload, dict):
                        next_popups_payload["popup_template"] = popup_template_payload
                    self._set_popups(next_popups_payload)
                merge_payload = payload.get("merge")
                if isinstance(merge_payload, dict):
                    self._set_merge(merge_payload)
                    for source_payload in merge_payload.get("sources", []):
                        if isinstance(source_payload, dict):
                            self._set_merge_source(source_payload)
                analysis_payload = payload.get("analysis")
                if isinstance(analysis_payload, dict):
                    shots_payload = analysis_payload.get("shots")
                    if isinstance(shots_payload, list):
                        controller.project.analysis.shots = [
                            _shot_from_dict(item)
                            for item in shots_payload
                            if isinstance(item, dict)
                        ]
                    events_payload = analysis_payload.get("events")
                    if isinstance(events_payload, list):
                        controller.project.analysis.events = [
                            _timing_event_from_dict(item)
                            for item in events_payload
                            if isinstance(item, dict)
                        ]
                    beep_ms = analysis_payload.get("beep_time_ms_primary")
                    if beep_ms is not None:
                        controller.project.analysis.beep_time_ms_primary = int(beep_ms)
                _sync_export_payload(controller, payload)
                output_path = (
                    Path(str(payload["path"]))
                    if payload.get("path") not in {None, ""}
                    else controller.stage_output_path()
                )
                activity.log("api.export.start", path=str(output_path))
                prepare_export_runtime()
                exported_path = export_project(
                    controller.project,
                    output_path,
                    progress_callback=lambda value: activity.log(
                        "api.export.progress", progress=value
                    ),
                    log_callback=lambda line: activity.log("api.export.log", line=line),
                )
                if not exported_path.exists() or exported_path.stat().st_size <= 0:
                    raise RuntimeError("Export did not produce an output file.")
                activity.log(
                    "api.export.complete",
                    path=str(exported_path),
                    bytes=exported_path.stat().st_size if exported_path.exists() else 0,
                )
                controller.project.touch()
                controller.status_message = f"Exported video to {exported_path}."

            def _select_stage(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or payload.get("active_stage_id") or "")
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.select_stage(stage_id)

            def _create_stage(self, payload: dict[str, Any]) -> None:
                controller.create_stage(
                    None if payload.get("label") in {None, ""} else str(payload["label"])
                )

            def _delete_stage(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.delete_stage(stage_id)

            def _import_stage_primary(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                paths = payload.get("paths", [])
                path = (
                    str(paths[0])
                    if isinstance(paths, list) and paths
                    else str(payload.get("path") or "")
                )
                if not stage_id or not path:
                    raise ValueError("stage_id and path are required")
                server._bump_media_url_token()
                controller.import_stage_primary(stage_id, path)

            def _import_stage_added(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                paths = payload.get("paths", [])
                path = (
                    str(paths[0])
                    if isinstance(paths, list) and paths
                    else str(payload.get("path") or "")
                )
                if not stage_id or not path:
                    raise ValueError("stage_id and path are required")
                server._bump_media_url_token()
                controller.import_stage_added(stage_id, path)

            def _clear_stage_primary(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                if not stage_id:
                    raise ValueError("stage_id is required")
                server._bump_media_url_token()
                controller.clear_stage_primary(stage_id)

            def _set_stage_primary(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                source_id = str(payload.get("source_id") or payload.get("id") or "")
                if not stage_id or not source_id:
                    raise ValueError("stage_id and source_id are required")
                server._bump_media_url_token()
                controller.set_stage_primary_from_existing(stage_id, source_id)

            def _remove_stage_added(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                source_id = str(payload.get("source_id") or payload.get("id") or "")
                if not stage_id or not source_id:
                    raise ValueError("stage_id and source_id are required")
                server._bump_media_url_token()
                controller.remove_stage_added_media(stage_id, source_id)

            def _set_global_settings_primary(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or controller.project.active_stage_id)
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.set_global_settings_primary(
                    stage_id, enabled=bool(payload.get("enabled", True))
                )

            def _ignore_global_settings(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or controller.project.active_stage_id)
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.ignore_global_settings(
                    stage_id, enabled=bool(payload.get("enabled", True))
                )

            def _add_to_queue(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                if not stage_id:
                    stage_id = controller.project.active_stage_id
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.add_stage_to_queue(stage_id)

            def _remove_from_queue(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.get("stage_id") or "")
                if not stage_id:
                    raise ValueError("stage_id is required")
                controller.remove_stage_from_queue(stage_id)

            def _add_all_to_queue(self, _payload: dict[str, Any]) -> None:
                controller.add_all_stages_to_queue()

            def _apply_settings_to_all(self, _payload: dict[str, Any]) -> None:
                controller.apply_settings_to_all_stages()

            def _set_queue_settings(self, payload: dict[str, Any]) -> None:
                controller.set_queue_settings(
                    fade_in_s=float(payload.get("fade_in_s", 0.5)),
                    fade_out_s=float(payload.get("fade_out_s", 0.5)),
                    include_intro=(
                        None if "include_intro" not in payload else bool(payload["include_intro"])
                    ),
                    include_outro=(
                        None if "include_outro" not in payload else bool(payload["include_outro"])
                    ),
                )

            def _set_in_out_media(self, payload: dict[str, Any]) -> None:
                controller.set_in_out_media(
                    str(payload.get("kind", "")),
                    str(payload.get("path", "")),
                )
                server._bump_media_url_token()

            def _set_intro_outro_overlay(self, payload: dict[str, Any]) -> None:
                controller.set_intro_outro_overlay(
                    str(payload.get("kind", "")),
                    payload,
                )

            def _set_intro_outro_fades(self, payload: dict[str, Any]) -> None:
                controller.set_intro_outro_fades(
                    str(payload.get("kind", "")),
                    fade_in_s=float(payload.get("fade_in_s", 0.5)),
                    fade_out_s=float(payload.get("fade_out_s", 0.5)),
                )

            def _process_queue(self, payload: dict[str, Any]) -> None:
                mode = str(payload.get("mode", "individual")).strip().lower()
                server._begin_processing_job("/api/project/queue/process", mode)

                def progress(detail: dict[str, Any]) -> None:
                    if server._update_processing_job(detail):
                        activity.log("api.queue.progress", **detail)

                def log(line: str) -> None:
                    server._append_processing_log(line)
                    activity.log("api.export.log", line=line)

                try:
                    controller.process_queue(
                        mode,
                        progress_callback=progress,
                        log_callback=log,
                    )
                except Exception as exc:
                    controller.project.export.last_error = str(exc)
                    if controller.project.active_stage is not None:
                        controller.project.active_stage.export.last_error = str(exc)
                    server._finish_processing_job(status=str(exc), error=str(exc))
                    raise
                completed_job = server._processing_snapshot()
                completed_log = "\n".join(
                    str(item.get("line") or "") for item in completed_job.get("logs", [])
                )
                controller.project.export.last_log = completed_log
                controller.project.export.last_error = None
                if controller.project.active_stage is not None:
                    controller.project.active_stage.export.last_log = completed_log
                    controller.project.active_stage.export.last_error = None
                server._finish_processing_job(status=controller.status_message)

        return Handler
