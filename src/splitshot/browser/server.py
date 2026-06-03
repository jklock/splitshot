"""Browser HTTP server, route handlers, and file/session plumbing for SplitShot."""

from __future__ import annotations

import base64
import cgi
import csv
from dataclasses import dataclass, field
from datetime import UTC, datetime
import errno
from http.cookies import SimpleCookie
import json
import mimetypes
import re
from secrets import token_urlsafe
import shutil
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from contextlib import closing
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib import resources
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, Callable
from urllib.parse import parse_qs, unquote, urlparse
from uuid import uuid4

from splitshot.browser.activity import ActivityLogger
from splitshot.browser.practiscore_session import PractiScoreSessionManager
from splitshot.browser.state import browser_state, reset_browser_state_caches
from splitshot import __version__ as SPLITSHOT_VERSION
from splitshot.analysis.detection import prewarm_analysis_runtime
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
from splitshot.export.presets import (
    EXPORT_SETTINGS_SYNC_COMPARISON_FIELDS,
    export_settings_payload_matches,
)
from splitshot.export.pipeline import export_project, prepare_export_runtime
from splitshot.media.ffmpeg import resolve_media_binary, run_ffmpeg, run_ffprobe_json
from splitshot.persistence.projects import (
    load_project,
    missing_required_project_dirs,
    normalize_project_path,
    resolve_project_path,
)
from splitshot.ui.controller import ProjectController
from splitshot.ui.services import practiscore_sync as practiscore_sync_service


EXPECTED_DISCONNECT_ERRORS = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
EXPECTED_DISCONNECT_ERRNOS = {errno.EPIPE, errno.ECONNABORTED, errno.ECONNRESET, errno.ENOBUFS}
PathChooser = Callable[[str, str | None], str | None]
COMMON_VIDEO_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.avi *.wmv *.webm *.mkv *.mpg *.mpeg *.mts *.m2ts"
COMMON_IMAGE_FILE_PATTERNS = "*.png *.jpg *.jpeg *.gif *.webp *.bmp *.tif *.tiff"
COMMON_EXPORT_FILE_PATTERNS = "*.mp4 *.m4v *.mov *.mkv"
_PROJECT_FOLDER_DIALOG_KINDS = frozenset(
    {"project", "project_save", "project_open", "project_folder"}
)
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
_PRACTISCORE_ELECTRON_HOST_HEADER = "X-SplitShot-PractiScore-Electron-Host"
_PRACTISCORE_ELECTRON_SESSION_HEADER = "X-SplitShot-PractiScore-Session-Payload"
_PRACTISCORE_ELECTRON_MATCHES_HEADER = "X-SplitShot-PractiScore-Matches"


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
    for required_field in required_fields:
        if source_timeline.get(required_field) != preview_timeline.get(required_field):
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
    return (
        metadata_match and _browser_preview_matches_source_packets(source_path, preview_path),
        source_timeline,
        preview_timeline,
    )


def is_expected_disconnect_error(exc: BaseException | None) -> bool:
    if isinstance(exc, EXPECTED_DISCONNECT_ERRORS):
        return True
    return isinstance(exc, OSError) and exc.errno in EXPECTED_DISCONNECT_ERRNOS


def _existing_dialog_directory_or_none(
    current: str | None, *, project_path: bool = False
) -> Path | None:
    if not current:
        return None

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
    return None


def _existing_dialog_directory(current: str | None, *, project_path: bool = False) -> Path:
    return _existing_dialog_directory_or_none(current, project_path=project_path) or Path.home()


def _dialog_chooser_current(
    kind: str,
    current: str | None,
    home: str | None,
    active_project_path: str | None,
) -> str | None:
    project_path_kind = kind in _PROJECT_FOLDER_DIALOG_KINDS
    if _existing_dialog_directory_or_none(current, project_path=project_path_kind) is not None:
        return current

    project_home = home or active_project_path
    if _existing_dialog_directory_or_none(project_home, project_path=project_path_kind) is not None:
        return project_home

    return current or project_home


def choose_local_path(kind: str, current: str | None = None) -> str | None:
    if sys.platform == "darwin":
        return choose_local_path_macos(kind, current)

    try:
        import tkinter as tk
        from tkinter import filedialog
    except Exception:  # noqa: BLE001
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
        if kind in {"primary", "secondary"}:
            return filedialog.askopenfilename(
                title=("Choose stage video" if kind == "primary" else "Choose added media"),
                initialdir=initial_dir,
                filetypes=[
                    ("Image files", COMMON_IMAGE_FILE_PATTERNS),
                    ("Video files", COMMON_VIDEO_FILE_PATTERNS),
                    ("All files", "*.*"),
                ],
            )
        if kind == "popup_image":
            return filedialog.askopenfilename(
                title="Choose local image asset",
                initialdir=initial_dir,
                filetypes=[
                    ("Image files", COMMON_IMAGE_FILE_PATTERNS),
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
    if kind in {"primary", "secondary"}:
        prompt = "Choose stage video" if kind == "primary" else "Choose added media"
        script = "\n".join(
            [
                f"set chosenFile to choose file with prompt {_applescript_string(prompt)} "
                f"default location POSIX file {_applescript_string(str(default_dir))}",
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
    if kind == "popup_image":
        script = "\n".join(
            [
                f"set chosenFile to choose file with prompt {_applescript_string('Choose local image asset')} "
                f"of type {{'public.image'}} default location POSIX file {_applescript_string(str(default_dir))}",
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
                f"set chosenFolder to choose folder with prompt {_applescript_string('Choose SplitShot project folder')} "
                f"default location POSIX file {_applescript_string(str(default_dir))}",
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
            f"set chosenFile to choose file name with prompt {_applescript_string(prompt)} "
            f"default name {_applescript_string(default_name)} "
            f"default location POSIX file {_applescript_string(str(default_dir))}",
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


def _payload_matches_export_state(project: Project, payload: dict[str, Any]) -> bool:
    return export_settings_payload_matches(
        project.export,
        payload,
        comparison_fields=EXPORT_SETTINGS_SYNC_COMPARISON_FIELDS,
    )


def _sync_export_payload(controller: ProjectController, payload: dict[str, Any]) -> None:
    selected_preset = str(payload.get("preset") or controller.project.export.preset.value)
    controller.apply_export_preset(selected_preset)
    if selected_preset == "custom" or not _payload_matches_export_state(
        controller.project, payload
    ):
        controller.set_export_settings(payload)


def _trim_export_settings_from_payload(controller: ProjectController, payload: dict[str, Any]):
    # SC-305 must keep trim requests on the shared export-settings contract:
    # export preset ids and field names stay identical to the export pane, and
    # trim-only keys (for example start/end timing) live alongside or around it.
    return controller.trim_export_settings_from_payload(payload)


def _merge_source_payload_from_browser_state(
    state_payload: dict[str, Any],
    source_id: str,
) -> dict[str, Any] | None:
    project_payload = state_payload.get("project")
    if not isinstance(project_payload, dict):
        return None
    merge_sources_payload = project_payload.get("merge_sources")
    if not isinstance(merge_sources_payload, list):
        return None
    return next(
        (
            item
            for item in merge_sources_payload
            if isinstance(item, dict) and str(item.get("id") or "") == source_id
        ),
        None,
    )


def _payload_alias_value(payload: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in payload:
            return payload[key]
    return None


def _normalize_merge_source_update_payload(payload: dict[str, Any]) -> dict[str, Any]:
    placement_payload = payload.get("placement")
    if not isinstance(placement_payload, dict):
        placement_payload = {}

    def resolve_position_value(*keys: str) -> Any:
        value = _payload_alias_value(placement_payload, *keys)
        if value is not None or any(key in placement_payload for key in keys):
            return value
        return _payload_alias_value(payload, *keys)

    target_source_id = resolve_position_value("target_source_id", "base_source_id")
    target_kind = resolve_position_value("target_kind")
    if target_kind in {None, ""} and target_source_id not in {None, ""}:
        target_kind = "merge_source"

    return {
        "angle_role": _payload_alias_value(payload, "camera_role", "angle_role"),
        "placement_mode": resolve_position_value("mode", "placement_mode", "composition_mode"),
        "placement_slot": resolve_position_value("slot", "placement_slot"),
        "target_kind": target_kind,
        "target_source_id": target_source_id,
    }


def _normalize_merge_source_trim_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_payload = dict(payload)
    trim_payload = normalized_payload.get("trim")
    if not isinstance(trim_payload, dict):
        return normalized_payload

    normalized_trim_payload = dict(trim_payload)
    if "start_ms" not in normalized_trim_payload and "trim_start_ms" in normalized_trim_payload:
        normalized_trim_payload["start_ms"] = normalized_trim_payload["trim_start_ms"]
    if "end_ms" not in normalized_trim_payload and "trim_end_ms" in normalized_trim_payload:
        normalized_trim_payload["end_ms"] = normalized_trim_payload["trim_end_ms"]
    normalized_payload["trim"] = normalized_trim_payload
    return normalized_payload


def find_free_port(host: str = "127.0.0.1", desired: int = 8765, max_attempts: int = 10) -> int:
    if desired == 0:
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.bind((host, 0))
            return int(sock.getsockname()[1])
    for attempt in range(max_attempts):
        port = desired + attempt
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No free port found on {host} in range {desired}-{desired + max_attempts - 1}")


class QuietThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True

    def server_bind(self) -> None:
        if self.allow_reuse_address and hasattr(self.socket, "setsockopt"):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(self.server_address)
        host, port = self.socket.getsockname()[:2]
        self.server_name = host
        self.server_port = port
        self.server_address = (host, port)

    def handle_error(self, request: Any, client_address: tuple[str, int]) -> None:
        if is_expected_disconnect_error(sys.exc_info()[1]):
            return
        super().handle_error(request, client_address)


_WORKSPACE_ELIGIBLE_KEYS = frozenset(
    {
        "shot_data_overlay",
        "video_shape",
        "opening_title",
        "your_logo",
        "overlay_visibility",
        "overlay_position",
        "marker_visibility",
        "export_quality",
        "frame_profile",
        "metric_caption_preset",
        "lead_in_card",
        "brand_mark",
        "subject_track_crop",
        "visibility_recipe",
        "aspect_ratio",
        "export_preset",
        "frame_rate",
        "video_codec",
        "audio_codec",
    }
)


def _stage_effective_settings(entry, shared_defaults, eligible_keys):
    """Compute effective settings for a stage (shared + overrides)."""
    effective = {}
    for key in eligible_keys:
        if key in entry.override_values:
            effective[key] = entry.override_values[key]
        elif key in shared_defaults:
            effective[key] = shared_defaults[key]
    return effective


def _runtime_timestamp() -> str:
    return datetime.now(UTC).isoformat(timespec="milliseconds")


def _normalize_scope_id(value: object) -> str | None:
    if value in {None, ""}:
        return None
    return str(value)


def _clamp_progress_percent(value: object | None) -> int | None:
    if value in {None, ""}:
        return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    return max(0, min(100, int(round(numeric))))


@dataclass(slots=True)
class BackgroundJobRecord:
    job_id: str
    job_type: str
    scope_type: str
    scope_id: str | None
    status: str
    submitted_at: str
    started_at: str | None = None
    finished_at: str | None = None
    progress_percent: int | None = None
    message: str = ""
    detail: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    cancel_supported: bool = False
    cancel_requested: bool = False
    created_from_route: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "job_type": self.job_type,
            "scope_type": self.scope_type,
            "scope_id": self.scope_id,
            "status": self.status,
            "submitted_at": self.submitted_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "progress_percent": self.progress_percent,
            "message": self.message,
            "detail": dict(self.detail),
            "result": self.result,
            "error": self.error,
            "cancel_supported": self.cancel_supported,
            "created_from_route": self.created_from_route,
        }


class JobCanceledError(RuntimeError):
    """Raised when a cancelable background job is canceled."""


class BackgroundJobHandle:
    def __init__(self, registry: "BackgroundJobRegistry", job_id: str) -> None:
        self._registry = registry
        self.job_id = job_id

    def snapshot(self) -> dict[str, Any] | None:
        return self._registry.get_job(self.job_id)

    def started(self, message: str, *, detail: dict[str, Any] | None = None) -> None:
        self._registry.mark_started(self.job_id, message=message, detail=detail)

    def progress(
        self,
        progress_percent: object | None,
        *,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._registry.mark_progress(
            self.job_id,
            progress_percent=progress_percent,
            message=message,
            detail=detail,
        )

    def log(self, line: str, *, detail: dict[str, Any] | None = None) -> None:
        self._registry.append_log(self.job_id, line=line, detail=detail)

    def completed(
        self,
        *,
        result: dict[str, Any] | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._registry.mark_completed(
            self.job_id,
            result=result,
            message=message,
            detail=detail,
        )

    def failed(
        self,
        message: str,
        *,
        detail: dict[str, Any] | None = None,
    ) -> None:
        self._registry.mark_failed(self.job_id, message=message, detail=detail)

    def ensure_not_canceled(self) -> None:
        self._registry.ensure_not_canceled(self.job_id)


class BackgroundJobRegistry:
    def __init__(
        self,
        activity: ActivityLogger,
        *,
        on_job_failed: Callable[[str, dict[str, Any]], None] | None = None,
    ) -> None:
        self._activity = activity
        self._on_job_failed = on_job_failed
        self._lock = threading.RLock()
        self._jobs: dict[str, BackgroundJobRecord] = {}
        self._threads: dict[str, threading.Thread] = {}

    def create_job(
        self,
        *,
        job_type: str,
        scope_type: str,
        scope_id: str | None,
        message: str,
        detail: dict[str, Any] | None = None,
        cancel_supported: bool = False,
        created_from_route: str | None = None,
    ) -> BackgroundJobHandle:
        with self._lock:
            record = BackgroundJobRecord(
                job_id=uuid4().hex,
                job_type=str(job_type),
                scope_type=str(scope_type),
                scope_id=_normalize_scope_id(scope_id),
                status="queued",
                submitted_at=_runtime_timestamp(),
                progress_percent=0,
                message=str(message),
                detail=dict(detail or {}),
                cancel_supported=bool(cancel_supported),
                created_from_route=created_from_route,
            )
            self._jobs[record.job_id] = record
            self._emit_locked(record, "job.queued", payload=record.detail)
            return BackgroundJobHandle(self, record.job_id)

    def run_inline(
        self,
        *,
        job_type: str,
        scope_type: str,
        scope_id: str | None,
        queued_message: str,
        started_message: str,
        completed_message: str,
        runner: Callable[[BackgroundJobHandle], dict[str, Any] | None],
        detail: dict[str, Any] | None = None,
        created_from_route: str | None = None,
    ) -> dict[str, Any] | None:
        handle = self.create_job(
            job_type=job_type,
            scope_type=scope_type,
            scope_id=scope_id,
            message=queued_message,
            detail=detail,
            created_from_route=created_from_route,
        )
        handle.started(started_message, detail=detail)
        try:
            result = runner(handle)
        except JobCanceledError:
            self.mark_canceled(handle.job_id, message="Job canceled.")
            raise
        except Exception as exc:  # noqa: BLE001
            self.mark_failed(
                handle.job_id,
                message=str(exc),
                detail={"exception_type": exc.__class__.__name__},
            )
            raise
        handle.completed(result=result, message=completed_message, detail=detail)
        return result

    def submit_background(
        self,
        *,
        job_type: str,
        scope_type: str,
        scope_id: str | None,
        queued_message: str,
        started_message: str,
        completed_message: str,
        runner: Callable[[BackgroundJobHandle], dict[str, Any] | None],
        detail: dict[str, Any] | None = None,
        cancel_supported: bool = False,
        created_from_route: str | None = None,
    ) -> dict[str, Any]:
        handle = self.create_job(
            job_type=job_type,
            scope_type=scope_type,
            scope_id=scope_id,
            message=queued_message,
            detail=detail,
            cancel_supported=cancel_supported,
            created_from_route=created_from_route,
        )

        def _run() -> None:
            handle.started(started_message, detail=detail)
            try:
                result = runner(handle)
            except JobCanceledError:
                self.mark_canceled(handle.job_id, message="Job canceled.")
                return
            except Exception as exc:  # noqa: BLE001
                self.mark_failed(
                    handle.job_id,
                    message=str(exc),
                    detail={"exception_type": exc.__class__.__name__},
                )
                return
            handle.completed(result=result, message=completed_message, detail=detail)

        thread = threading.Thread(target=_run, daemon=True)
        with self._lock:
            self._threads[handle.job_id] = thread
        thread.start()
        snapshot = handle.snapshot()
        if snapshot is None:
            raise RuntimeError("Background job snapshot is unavailable.")
        return snapshot

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._jobs.get(str(job_id))
            return None if record is None else record.to_dict()

    def list_jobs(self) -> list[dict[str, Any]]:
        with self._lock:
            return [record.to_dict() for record in self._jobs.values()]

    def request_cancel(self, job_id: str) -> tuple[dict[str, Any] | None, bool]:
        with self._lock:
            record = self._jobs.get(str(job_id))
            if record is None:
                return None, False
            if not record.cancel_supported:
                return record.to_dict(), False
            record.cancel_requested = True
            if record.status == "queued":
                record.status = "canceled"
                record.finished_at = _runtime_timestamp()
                record.message = "Job canceled before start."
                self._emit_locked(record, "job.canceled", payload={"reason": "cancel_requested"})
            return record.to_dict(), True

    def ensure_not_canceled(self, job_id: str) -> None:
        with self._lock:
            record = self._jobs.get(str(job_id))
            if record is not None and record.cancel_requested:
                raise JobCanceledError("Job canceled.")

    def mark_started(
        self,
        job_id: str,
        *,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            if record.status == "canceled":
                raise JobCanceledError("Job canceled.")
            record.status = "running"
            record.started_at = _runtime_timestamp()
            record.message = str(message)
            if detail is not None:
                record.detail = dict(detail)
            self._emit_locked(record, "job.started", payload=record.detail)

    def mark_progress(
        self,
        job_id: str,
        *,
        progress_percent: object | None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            record.status = "running"
            normalized_progress = _clamp_progress_percent(progress_percent)
            if normalized_progress is not None:
                record.progress_percent = normalized_progress
            if message is not None:
                record.message = str(message)
            payload = dict(detail or record.detail)
            self._emit_locked(record, "job.progress", payload=payload)

    def append_log(
        self,
        job_id: str,
        *,
        line: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            payload = dict(detail or {})
            payload["line"] = str(line)
            self._emit_locked(record, "job.log", payload=payload, message=str(line))

    def mark_completed(
        self,
        job_id: str,
        *,
        result: dict[str, Any] | None = None,
        message: str | None = None,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            record.status = "completed"
            record.finished_at = _runtime_timestamp()
            record.progress_percent = 100
            if message is not None:
                record.message = str(message)
            record.result = result
            payload = dict(detail or record.detail)
            if result is not None:
                payload.setdefault("result", result)
            self._emit_locked(record, "job.completed", payload=payload)

    def mark_failed(
        self,
        job_id: str,
        *,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            record.status = "failed"
            record.finished_at = _runtime_timestamp()
            record.message = str(message)
            record.error = {
                "message": str(message),
                "detail": dict(detail or {}),
            }
            payload = dict(detail or {})
            payload.setdefault("error", record.error)
            self._emit_locked(record, "job.failed", payload=payload)
            if callable(self._on_job_failed):
                self._on_job_failed(record.message, payload)

    def mark_canceled(
        self,
        job_id: str,
        *,
        message: str,
        detail: dict[str, Any] | None = None,
    ) -> None:
        with self._lock:
            record = self._jobs[str(job_id)]
            record.status = "canceled"
            record.finished_at = _runtime_timestamp()
            record.message = str(message)
            self._emit_locked(record, "job.canceled", payload=dict(detail or {}))

    def summary(self) -> dict[str, Any]:
        with self._lock:
            counts = {
                "queued": 0,
                "running": 0,
                "completed": 0,
                "failed": 0,
                "canceled": 0,
            }
            active_job_ids: list[str] = []
            for record in self._jobs.values():
                counts.setdefault(record.status, 0)
                counts[record.status] += 1
                if record.status in {"queued", "running"}:
                    active_job_ids.append(record.job_id)
            return {
                "total": len(self._jobs),
                "by_status": counts,
                "active_job_ids": active_job_ids,
            }

    def _emit_locked(
        self,
        record: BackgroundJobRecord,
        event_type: str,
        *,
        payload: dict[str, Any] | None = None,
        message: str | None = None,
    ) -> None:
        event_payload = dict(payload or {})
        self._activity.log(
            event_type,
            event_type=event_type,
            event_id=uuid4().hex,
            job_id=record.job_id,
            job_type=record.job_type,
            scope_type=record.scope_type,
            scope_id=record.scope_id,
            status=record.status,
            message=str(message if message is not None else record.message),
            progress_percent=record.progress_percent,
            payload=event_payload,
        )


class BrowserControlServer:
    _thread_fairness_lock = threading.Lock()
    _thread_fairness_users = 0
    _thread_fairness_previous_interval: float | None = None
    _thread_fairness_interval = 0.001

    def __init__(
        self,
        controller: ProjectController | None = None,
        host: str = "127.0.0.1",
        port: int = 8765,
        log_dir: str | Path | None = None,
        log_level: str = "off",
        path_chooser: PathChooser | None = None,
        browser_media_proxy_enabled: bool = True,
        require_session_claim: bool = False,
    ) -> None:
        self.controller = controller or ProjectController()
        reset_browser_state_caches()
        self.host = host
        self.port = port
        self.activity = ActivityLogger(log_dir, console_level=log_level)
        self.path_chooser = path_chooser or choose_local_path
        self.browser_media_proxy_enabled = browser_media_proxy_enabled
        self.require_session_claim = require_session_claim
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._controller_lock = threading.RLock()
        self._shutdown_event = threading.Event()
        self._session_dir = TemporaryDirectory(prefix="splitshot-browser-")
        self._session_path = Path(self._session_dir.name)
        self._app_data_root = self._session_path / "app-data"
        self._cache_root = self._session_path / "cache"
        self._app_data_root.mkdir(parents=True, exist_ok=True)
        self._cache_root.mkdir(parents=True, exist_ok=True)
        self._display_names: dict[str, str] = {}
        self._browser_media_cache: dict[str, BrowserMediaCacheEntry] = {}
        self._browser_media_lock = threading.Lock()
        self._media_url_token = uuid4().hex
        self._startup_protocol_version = "1"
        self._session_cookie_name = "splitshot_session"
        self._session_id = uuid4().hex
        self._bootstrap_token = token_urlsafe(32)
        self._bootstrap_token_claimed = False
        self._session_cookie_value: str | None = None
        self._started_at_monotonic = time.monotonic()
        self._runtime_state = "starting"
        self._runtime_detail = "Binding local backend."
        self._fatal_error: str | None = None
        self._last_error: dict[str, Any] | None = None
        self._jobs = BackgroundJobRegistry(self.activity, on_job_failed=self._record_runtime_error)
        self.practiscore_session = PractiScoreSessionManager()
        prepare_export_runtime()
        try:
            prewarm_analysis_runtime()
        except Exception as exc:  # noqa: BLE001
            self.activity.log("analysis.prewarm.error", error=str(exc))
        self.activity.log(
            "server.initialized",
            host=host,
            port=port,
            log_path=str(self.activity.path),
            require_session_claim=require_session_claim,
        )

    @classmethod
    def _acquire_thread_fairness_override(cls) -> None:
        with cls._thread_fairness_lock:
            if cls._thread_fairness_users == 0:
                cls._thread_fairness_previous_interval = sys.getswitchinterval()
                if cls._thread_fairness_previous_interval > cls._thread_fairness_interval:
                    sys.setswitchinterval(cls._thread_fairness_interval)
            cls._thread_fairness_users += 1

    @classmethod
    def _release_thread_fairness_override(cls) -> None:
        with cls._thread_fairness_lock:
            if cls._thread_fairness_users <= 0:
                return
            cls._thread_fairness_users -= 1
            if cls._thread_fairness_users != 0:
                return
            previous_interval = cls._thread_fairness_previous_interval
            cls._thread_fairness_previous_interval = None
            if previous_interval is not None:
                sys.setswitchinterval(previous_interval)

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
            self._set_runtime_state(
                "fatal",
                detail=f"Failed to bind local backend on {self.host}:{self.port}.",
                fatal_error=str(exc),
            )
            self.activity.log("server.bind.error", host=self.host, port=self.port, error=str(exc))
            print(f"SplitShot could not bind to {self.host}:{self.port}: {exc}")
            print("Use --port to select a different port, or stop the process using this port.")
            raise

        self._acquire_thread_fairness_override()
        self._set_runtime_state("ready", detail=f"Listening on {self.url}")
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
            self._set_runtime_state("shutting_down", detail="Shutting down local backend.")
            self._shutdown_event.set()
            self.activity.log("server.stopping", url=self.url)
            self.practiscore_session.shutdown()
            self._httpd.server_close()
            self._session_dir.cleanup()
            self._release_thread_fairness_override()

    def start_background(self, open_browser: bool = False) -> None:
        try:
            self._httpd = self._build_httpd()
        except OSError as exc:
            self._set_runtime_state(
                "fatal",
                detail=f"Failed to bind local backend on {self.host}:{self.port}.",
                fatal_error=str(exc),
            )
            self.activity.log("server.bind.error", host=self.host, port=self.port, error=str(exc))
            print(f"SplitShot could not bind to {self.host}:{self.port}: {exc}")
            print("Use --port to select a different port, or stop the process using this port.")
            raise

        self._acquire_thread_fairness_override()
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self._set_runtime_state("ready", detail=f"Listening on {self.url}")
        self.activity.log("server.start_background", url=self.url, open_browser=open_browser)
        if open_browser:
            self._attempt_open_browser()

    def shutdown(self) -> None:
        self._set_runtime_state("shutting_down", detail="Shutting down local backend.")
        self._shutdown_event.set()
        self.activity.log("server.shutdown", url=self.url)
        self.practiscore_session.shutdown()
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
        if self._thread is not None:
            self._thread.join(timeout=2)
        self._session_dir.cleanup()
        self._release_thread_fairness_override()

    def _build_httpd(self) -> ThreadingHTTPServer:
        return QuietThreadingHTTPServer((self.host, self.port), self._handler())

    def ready_line_payload(self) -> dict[str, Any]:
        payload = self._session_metadata_payload(include_secret=True)
        payload["startup_status_path"] = "/api/startup/status"
        payload["claim_path"] = "/api/startup/claim"
        return payload

    def session_metadata(self) -> dict[str, Any] | None:
        if self.require_session_claim and self._session_cookie_value is None:
            return None
        payload = self._session_metadata_payload(include_secret=False)
        payload["startup_status_path"] = "/api/startup/status"
        payload["claim_path"] = "/api/startup/claim"
        return payload

    def startup_status_payload(self) -> dict[str, Any]:
        return {
            "state": self._runtime_state,
            "backend_version": SPLITSHOT_VERSION,
            "project_schema_version": str(self.controller.project.schema_version),
            "fatal_error": self._fatal_error,
            "detail": {
                "base_url": self.url.rstrip("/"),
                "require_session_claim": self.require_session_claim,
                "log_root": str(self.activity.path.parent),
            },
            "timestamp": _runtime_timestamp(),
        }

    def health_payload(self) -> dict[str, Any]:
        state = self._runtime_state
        if state == "ready" and self._last_error is not None:
            state = "degraded"
        return {
            "state": state,
            "session_id": self._session_id,
            "uptime_seconds": max(0.0, round(time.monotonic() - self._started_at_monotonic, 3)),
            "job_summary": self._jobs.summary(),
            "last_error": self._last_error,
            "timestamp": _runtime_timestamp(),
        }

    def structured_events_after(
        self, after_seq: int = 0, *, limit: int = 1000
    ) -> list[dict[str, Any]]:
        records = self.activity.records_after(
            after_seq,
            limit=limit,
            predicate=lambda record: bool(record.get("event_type")),
        )
        return [self._structured_event_payload(record) for record in records]

    def wait_for_structured_events(self, after_seq: int = 0, timeout: float | None = None) -> bool:
        return self.activity.wait_for_records(after_seq, timeout=timeout)

    def claim_session(self, bootstrap_token: str) -> tuple[dict[str, Any], str]:
        expected = str(self._bootstrap_token)
        if str(bootstrap_token or "") != expected:
            raise PermissionError("The startup bootstrap token is invalid.")
        if self._bootstrap_token_claimed:
            raise PermissionError("The startup bootstrap token has already been used.")
        self._bootstrap_token_claimed = True
        self._session_cookie_value = token_urlsafe(32)
        return (
            self._session_metadata_payload(include_secret=False),
            self._session_cookie_header(self._session_cookie_value),
        )

    def request_is_authorized(self, headers: dict[str, str] | Any) -> bool:
        if not self.require_session_claim:
            return True
        if self._session_cookie_value is None:
            return False
        raw_cookie = str(headers.get("Cookie", "") or "")
        if not raw_cookie:
            return False
        cookies = SimpleCookie()
        try:
            cookies.load(raw_cookie)
        except Exception:  # noqa: BLE001
            return False
        morsel = cookies.get(self._session_cookie_name)
        if morsel is None:
            return False
        return morsel.value == self._session_cookie_value

    def route_requires_claim(self, path: str) -> bool:
        normalized_path = str(path or "")
        if not self.require_session_claim:
            return False
        if normalized_path in {"/", "/index.html", "/api/startup/status", "/api/startup/claim"}:
            return False
        if normalized_path.startswith("/static/"):
            return False
        return normalized_path.startswith("/api/") or normalized_path.startswith("/media/")

    def _session_metadata_payload(self, *, include_secret: bool) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "protocol_version": self._startup_protocol_version,
            "session_id": self._session_id,
            "host": str(self.host),
            "port": int(self._httpd.server_address[1] if self._httpd is not None else self.port),
            "base_url": self.url.rstrip("/"),
            "health_path": "/api/health",
            "events_path": "/api/events",
            "backend_version": SPLITSHOT_VERSION,
            "project_schema_version": str(self.controller.project.schema_version),
            "app_data_root": str(self._app_data_root),
            "cache_root": str(self._cache_root),
            "log_root": str(self.activity.path.parent),
        }
        launch_intent = self._launch_intent_payload()
        if launch_intent is not None:
            payload["launch_intent"] = launch_intent
        if include_secret:
            payload["bootstrap_token"] = self._bootstrap_token
        return payload

    def _launch_intent_payload(self) -> dict[str, Any] | None:
        if self.controller.project_path is None:
            return None
        return {
            "kind": "open-project",
            "project_path": str(self.controller.project_path),
            "source": "startup-project",
        }

    def _session_cookie_header(self, cookie_value: str) -> str:
        return f"{self._session_cookie_name}={cookie_value}; HttpOnly; Path=/; SameSite=Strict"

    def _structured_event_payload(self, record: dict[str, object]) -> dict[str, Any]:
        detail_payload = record.get("payload")
        detail = dict(detail_payload) if isinstance(detail_payload, dict) else {}
        return {
            "event_id": str(record.get("event_id") or record.get("seq") or uuid4().hex),
            "seq": int(record.get("seq", 0) or 0),
            "event_type": str(record.get("event_type") or record.get("event") or ""),
            "job_id": _normalize_scope_id(record.get("job_id")),
            "timestamp": str(record.get("ts") or _runtime_timestamp()),
            "scope_type": _normalize_scope_id(record.get("scope_type")),
            "scope_id": _normalize_scope_id(record.get("scope_id")),
            "status": _normalize_scope_id(record.get("status")),
            "message": _normalize_scope_id(record.get("message")),
            "progress_percent": _clamp_progress_percent(record.get("progress_percent")),
            "detail": detail,
            "payload": detail,
        }

    def _set_runtime_state(
        self,
        state: str,
        *,
        detail: str,
        fatal_error: str | None = None,
    ) -> None:
        self._runtime_state = str(state)
        self._runtime_detail = str(detail)
        self._fatal_error = fatal_error
        payload = {
            "state": self._runtime_state,
            "detail": self._runtime_detail,
            "fatal_error": self._fatal_error,
        }
        self.activity.log(
            "runtime.health",
            event_type="runtime.health",
            event_id=uuid4().hex,
            scope_type="runtime",
            scope_id=self._session_id,
            status=self._runtime_state,
            message=self._runtime_detail,
            payload=payload,
        )

    def _record_runtime_error(self, message: str, detail: dict[str, Any]) -> None:
        self._last_error = {
            "message": str(message),
            "detail": dict(detail),
            "timestamp": _runtime_timestamp(),
        }
        if self._runtime_state == "ready":
            self._set_runtime_state("degraded", detail=str(message))

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
                if request_path == "/api/startup/status":
                    self._send_json(server.startup_status_payload())
                    return
                if request_path == "/api/health":
                    if not self._ensure_authorized(request_path):
                        return
                    self._send_json(server.health_payload())
                    return
                if request_path == "/api/jobs":
                    if not self._ensure_authorized(request_path):
                        return
                    self._send_jobs_list()
                    return
                if request_path.startswith("/api/jobs/"):
                    if not self._ensure_authorized(request_path):
                        return
                    job_id = self._job_id_from_path()
                    if job_id is None:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._send_job_detail(job_id)
                    return
                if request_path == "/api/events":
                    if not self._ensure_authorized(request_path):
                        return
                    self._stream_events(parsed_url.query)
                    return
                if not self._ensure_authorized(request_path):
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
                if request_path.startswith("/media/workspace-stage/"):
                    self._send_workspace_stage_media(
                        request_path.removeprefix("/media/workspace-stage/")
                    )
                    return
                if request_path.startswith("/media/merge/"):
                    self._send_merge_media(request_path.removeprefix("/media/merge/"))
                    return
                if request_path.startswith("/media/popup/"):
                    self._send_popup_media(request_path.removeprefix("/media/popup/"))
                    return
                self.send_error(HTTPStatus.NOT_FOUND)

            def _mutating_post_route_groups(
                self,
            ) -> dict[str, dict[str, Callable[[dict[str, Any]], None]]]:
                return {
                    "project": {
                        "/api/project/details": self._set_project_details,
                        "/api/project/practiscore": self._set_practiscore_context,
                        "/api/project/ui-state": self._set_project_ui_state,
                        "/api/project/new": self._new_project,
                        "/api/project/open": self._open_project,
                        "/api/project/save": self._save_project,
                        "/api/project/delete": self._delete_project,
                    },
                    "workspace": {
                        "/api/workspace/new": self._new_workspace,
                        "/api/workspace/open": self._open_workspace,
                        "/api/workspace/save": self._save_workspace,
                        "/api/workspace/stage/add": self._workspace_add_stage,
                        "/api/workspace/stage/remove": self._workspace_remove_stage,
                        "/api/workspace/stage/open": self._workspace_open_stage,
                        "/api/workspace/stage/return": self._workspace_return_to_workspace,
                        "/api/workspace/defaults": self._workspace_set_defaults,
                        "/api/workspace/stage/override": self._workspace_set_stage_override,
                        "/api/workspace/stage/override/reset": self._workspace_reset_stage_override,
                    },
                    "imports": {
                        "/api/import/primary": self._import_primary,
                        "/api/import/secondary": self._import_merge,
                        "/api/import/merge": self._import_merge,
                    },
                    "analysis": {
                        "/api/analysis/threshold": self._set_threshold,
                        "/api/analysis/shotml-settings": self._set_shotml_settings,
                        "/api/analysis/shotml/proposals": self._generate_shotml_proposals,
                        "/api/analysis/shotml/apply-proposal": self._apply_shotml_proposal,
                        "/api/analysis/shotml/discard-proposal": self._discard_shotml_proposal,
                        "/api/analysis/shotml/reset-defaults": self._reset_shotml_defaults,
                        "/api/beep": self._set_beep,
                        "/api/shots/add": self._add_shot,
                        "/api/shots/move": self._move_shot,
                        "/api/shots/restore": self._restore_shot,
                        "/api/shots/delete": self._delete_shot,
                        "/api/shots/select": self._select_shot,
                        "/api/events/add": self._add_event,
                        "/api/events/delete": self._delete_event,
                    },
                    "scoring": {
                        "/api/scoring": self._set_scoring,
                        "/api/scoring/profile": self._set_scoring_profile,
                        "/api/scoring/score": self._assign_score,
                        "/api/scoring/restore": self._restore_score,
                        "/api/scoring/position": self._set_score_position,
                    },
                    "shell_and_export": {
                        "/api/settings": self._set_settings_defaults,
                        "/api/settings/reset-defaults": self._reset_settings_defaults,
                        "/api/merge/remove": self._remove_merge_source,
                        "/api/merge/reset-defaults": self._reset_merge_defaults,
                        "/api/merge/source": self._set_merge_source,
                        "/api/merge/source/analyze": self._analyze_merge_source,
                        "/api/overlay": self._set_overlay,
                        "/api/popups": self._set_popups,
                        "/api/merge": self._set_merge,
                        "/api/sync": self._set_sync,
                        "/api/swap": self._swap_videos,
                        "/api/export/settings": self._set_export_settings,
                        "/api/export/preset": self._set_export_preset,
                        "/api/export": self._export_project,
                    },
                }

            def _structured_post_route_groups(
                self,
            ) -> dict[str, dict[str, tuple[str, tuple[str, ...]]]]:
                return {
                    "trim_backend": {
                        "/api/merge/source/trim": ("_handle_merge_source_trim", ()),
                    },
                    "library_records": {
                        "/api/library/list": ("_handle_library_list", ("_no_body",)),
                        "/api/library/filter": ("_handle_library_filter", ()),
                        "/api/library/stage/open": ("_handle_library_stage_open", ()),
                        "/api/library/match/open": ("_handle_library_match_open", ()),
                        "/api/proxy/status": ("_handle_proxy_status", ()),
                        "/api/library/proxy/refresh": ("_handle_proxy_refresh", ()),
                        "/api/proxy/refresh": ("_handle_proxy_refresh", ()),
                        "/api/library/proxy/open": ("_handle_library_proxy_open", ()),
                    },
                    "output_profiles": {
                        "/api/output-profiles/list": ("_handle_output_profile_list", ()),
                        "/api/output-profiles/create": ("_handle_output_profile_create", ()),
                        "/api/output-profiles/update": ("_handle_output_profile_update", ()),
                        "/api/output-profiles/delete": ("_handle_output_profile_delete", ()),
                        "/api/output-profiles/render": ("_handle_output_profile_render", ()),
                    },
                    "workspace_stage_support": {
                        "/api/workspace/stage/clip/list": ("_handle_workspace_stage_clip_list", ()),
                        "/api/workspace/stage/clip/add": ("_handle_workspace_stage_clip_add", ()),
                        "/api/workspace/stage/clip/update": (
                            "_handle_workspace_stage_clip_update",
                            (),
                        ),
                        "/api/workspace/stage/clip/reorder": (
                            "_handle_workspace_stage_clip_reorder",
                            (),
                        ),
                        "/api/workspace/stage/clip/remove": (
                            "_handle_workspace_stage_clip_remove",
                            (),
                        ),
                        "/api/angle/align": ("_handle_angle_align", ()),
                        "/api/angle/director/plan": ("_handle_angle_director_plan", ()),
                        "/api/angle/director/generate": ("_handle_angle_director_generate", ()),
                        "/api/angle/director/override": ("_handle_angle_director_override", ()),
                        "/api/angle/director/override/clear": (
                            "_handle_angle_director_override_clear",
                            (),
                        ),
                        "/api/audio/mix": ("_handle_audio_mix", ()),
                        "/api/result-cards/resolve": ("_handle_result_cards_resolve", ()),
                    },
                    "landing_and_workspace": {
                        "/api/landing/recent": ("_handle_landing_recent", ("_no_body",)),
                        "/api/workspace/apply-from-first": (
                            "_handle_workspace_apply_from_first",
                            (),
                        ),
                        "/api/workspace/apply-from-first/preview": (
                            "_handle_workspace_apply_from_first_preview",
                            (),
                        ),
                        "/api/workspace/export": ("_handle_workspace_export", ()),
                        "/api/workspace/recap/render": ("_handle_workspace_recap_render", ()),
                        "/api/workspace/defaults/reset": ("_handle_workspace_defaults_reset", ()),
                    },
                    "library_management": {
                        "/api/library/analytics/trend": ("_handle_library_analytics_trend", ()),
                        "/api/library/analytics/compare": ("_handle_library_analytics_compare", ()),
                        "/api/library/archive/create": ("_handle_library_archive_create", ()),
                        "/api/library/backup/create": (
                            "_handle_library_backup_create",
                            ("_no_body",),
                        ),
                        "/api/library/backup/restore": ("_handle_library_backup_restore", ()),
                        "/api/library/export/json": ("_handle_library_export_json", ("_no_body",)),
                        "/api/library/export/csv": ("_handle_library_export_csv", ("_no_body",)),
                        "/api/library/notes/update": ("_handle_library_notes_update", ()),
                        "/api/library/tags/update": ("_handle_library_tags_update", ()),
                    },
                }

            def _dispatch_structured_post_route(
                self,
                method_name: str,
                flags: tuple[str, ...],
            ) -> None:
                handler = getattr(self, method_name)
                payload = {}
                if "_no_body" not in flags:
                    payload = self._read_json()
                activity.log("api.start", path=self.path, payload=payload)
                try:
                    response = handler(
                        **{
                            k: v
                            for k, v in [("body", payload)]
                            if "body" in handler.__code__.co_varnames
                        }
                    )
                    activity.log("api.success", path=self.path)
                    self._send_json(response)
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.error", path=self.path, error=str(exc))
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)

            def do_POST(self) -> None:  # noqa: N802
                activity.log("http.post", path=self.path, client=self.client_address[0])
                if self.path == "/api/startup/claim":
                    self._claim_backend_session()
                    return
                if self.path == "/api/jobs":
                    if not self._ensure_authorized(self.path):
                        return
                    self._submit_job()
                    return
                if self.path.startswith("/api/jobs/") and self.path.endswith("/cancel"):
                    if not self._ensure_authorized(self.path):
                        return
                    job_id = self._job_id_from_path(suffix="/cancel")
                    if job_id is None:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._cancel_job(job_id)
                    return
                if not self._ensure_authorized(self.path):
                    return
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
                mutating_routes: dict[str, Callable[[dict[str, Any]], None]] = {}
                for owner_family_routes in self._mutating_post_route_groups().values():
                    mutating_routes.update(owner_family_routes)
                entry = mutating_routes.get(self.path)
                if entry is None:
                    structured_routes: dict[str, tuple[str, tuple[str, ...]]] = {}
                    for owner_family_routes in self._structured_post_route_groups().values():
                        structured_routes.update(owner_family_routes)
                    structured_entry = structured_routes.get(self.path)
                    if structured_entry is None:
                        self.send_error(HTTPStatus.NOT_FOUND)
                        return
                    self._dispatch_structured_post_route(*structured_entry)
                    return
                try:
                    payload = self._read_json()
                    activity.log("api.start", path=self.path, payload=payload)
                    with controller_lock:
                        entry(payload)
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

            def _read_json_header(self, header_name: str) -> object | None:
                encoded_value = str(self.headers.get(header_name, "") or "").strip()
                if not encoded_value:
                    return None
                padded_value = encoded_value + "=" * (-len(encoded_value) % 4)
                decoded = base64.urlsafe_b64decode(padded_value.encode("ascii"))
                return json.loads(decoded.decode("utf-8"))

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
                self,
                payload: dict[str, Any],
                status: HTTPStatus = HTTPStatus.OK,
                extra_headers: dict[str, str] | None = None,
            ) -> None:
                data = json.dumps(payload).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self._send_security_headers(include_csp=True)
                self._send_no_cache_headers()
                for header_name, header_value in (extra_headers or {}).items():
                    self.send_header(header_name, header_value)
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

            def _ensure_authorized(self, route: str) -> bool:
                if not server.route_requires_claim(route):
                    return True
                if server.request_is_authorized(self.headers):
                    return True
                self._send_structured_error(
                    code="backend_session_required",
                    message="Claim the backend session before calling this route.",
                    status=HTTPStatus.UNAUTHORIZED,
                    details={"route": route},
                )
                return False

            def _job_id_from_path(self, *, suffix: str = "") -> str | None:
                route = str(self.path or "")
                prefix = "/api/jobs/"
                if not route.startswith(prefix):
                    return None
                tail = route[len(prefix) :]
                if suffix:
                    if not tail.endswith(suffix):
                        return None
                    tail = tail[: -len(suffix)]
                job_id = tail.strip("/")
                return job_id or None

            def _claim_backend_session(self) -> None:
                try:
                    payload, cookie_header = server.claim_session(
                        str(self.headers.get("X-SplitShot-Bootstrap-Token", "") or "")
                    )
                    activity.log(
                        "api.startup.claim",
                        session_id=payload.get("session_id"),
                        require_session_claim=server.require_session_claim,
                    )
                    self._send_json(
                        payload,
                        extra_headers={"Set-Cookie": cookie_header},
                    )
                except PermissionError as exc:
                    activity.log("api.startup.claim.error", error=str(exc))
                    self._send_structured_error(
                        code="backend_startup_claim_failed",
                        message=str(exc),
                        status=HTTPStatus.UNAUTHORIZED,
                        details={"route": "/api/startup/claim"},
                    )
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.startup.claim.error", error=str(exc))
                    self._send_structured_error(
                        code="backend_startup_claim_failed",
                        message="Unable to establish the local backend session.",
                        status=HTTPStatus.INTERNAL_SERVER_ERROR,
                        details={"route": "/api/startup/claim", "reason": str(exc)},
                    )

            def _send_jobs_list(self) -> None:
                self._send_json({"jobs": server._jobs.list_jobs()})

            def _send_job_detail(self, job_id: str) -> None:
                payload = server._jobs.get_job(job_id)
                if payload is None:
                    self._send_structured_error(
                        code="job_not_found",
                        message=f"Unknown job id: {job_id}",
                        status=HTTPStatus.NOT_FOUND,
                        details={"job_id": job_id},
                    )
                    return
                self._send_json({"job": payload})

            def _cancel_job(self, job_id: str) -> None:
                payload, supported = server._jobs.request_cancel(job_id)
                if payload is None:
                    self._send_structured_error(
                        code="job_not_found",
                        message=f"Unknown job id: {job_id}",
                        status=HTTPStatus.NOT_FOUND,
                        details={"job_id": job_id},
                    )
                    return
                if not supported:
                    self._send_structured_error(
                        code="job_cancel_unsupported",
                        message="This job does not support cancellation.",
                        status=HTTPStatus.CONFLICT,
                        details={"job": payload},
                    )
                    return
                self._send_json({"job": payload})

            def _perform_analysis_job(self, body: dict[str, Any]) -> dict[str, Any]:
                action = str(body.get("action") or "set_threshold").strip().lower()
                with controller_lock:
                    if action != "set_threshold":
                        raise ValueError(f"Unsupported analysis job action: {action}")
                    threshold = float(body["threshold"])
                    controller.set_detection_threshold(threshold)
                    return {
                        "action": action,
                        "threshold": controller.project.analysis.detection_threshold,
                        "status": controller.status_message,
                    }

            def _perform_export(
                self, payload: dict[str, Any], job_handle: BackgroundJobHandle
            ) -> dict[str, Any]:
                with controller_lock:
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
                    output_path = Path(str(payload["path"]))
                    activity.log("api.export.start", path=str(output_path))
                    exported_path = export_project(
                        controller.project,
                        output_path,
                        progress_callback=lambda value: (
                            activity.log("api.export.progress", progress=value),
                            job_handle.progress(
                                max(0.0, min(100.0, float(value) * 100.0)),
                                message=f"Export progress {int(round(float(value) * 100.0))}%.",
                                detail={"legacy_event": "api.export.progress", "progress": value},
                            ),
                        ),
                        log_callback=lambda line: (
                            activity.log("api.export.log", line=line),
                            job_handle.log(
                                str(line),
                                detail={"legacy_event": "api.export.log"},
                            ),
                        ),
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
                    return {
                        "output_path": str(exported_path),
                        "bytes": exported_path.stat().st_size,
                        "status": controller.status_message,
                        "legacy_event": "api.export.complete",
                    }

            def _submit_job(self) -> None:
                try:
                    request_payload = self._read_json()
                    job_type = str(request_payload.get("job_type") or "").strip().lower()
                    body = request_payload.get("payload")
                    if not isinstance(body, dict):
                        body = {}
                    scope_type = str(request_payload.get("scope_type") or "project")
                    scope_id = _normalize_scope_id(
                        request_payload.get("scope_id") or getattr(controller.project, "id", None)
                    )
                    detail = {
                        "route": "/api/jobs",
                        "job_type": job_type,
                    }
                    if job_type == "export":
                        output_path = Path(str(body["path"]))

                        def _run_export_job(handle: BackgroundJobHandle) -> dict[str, Any]:
                            result = self._perform_export(body, handle)
                            with controller_lock:
                                controller.autosave_project_if_needed()
                            return result

                        job_payload = server._jobs.submit_background(
                            job_type="export",
                            scope_type=scope_type,
                            scope_id=scope_id,
                            queued_message=f"Queued export to {output_path}.",
                            started_message=f"Exporting video to {output_path}.",
                            completed_message=f"Exported video to {output_path}.",
                            runner=_run_export_job,
                            detail=detail,
                            created_from_route="/api/jobs",
                        )
                    elif job_type == "analysis":
                        action = str(body.get("action") or "set_threshold").strip().lower()

                        def _run_analysis_job(handle: BackgroundJobHandle) -> dict[str, Any]:
                            handle.progress(
                                5, message="Preparing analysis job.", detail={"action": action}
                            )
                            result = self._perform_analysis_job(body)
                            handle.progress(
                                100,
                                message=result.get("status") or "Analysis complete.",
                                detail={"action": action},
                            )
                            with controller_lock:
                                controller.autosave_project_if_needed()
                            return result

                        job_payload = server._jobs.submit_background(
                            job_type="analysis",
                            scope_type=scope_type,
                            scope_id=scope_id,
                            queued_message=f"Queued analysis action {action}.",
                            started_message=f"Running analysis action {action}.",
                            completed_message=f"Completed analysis action {action}.",
                            runner=_run_analysis_job,
                            detail={**detail, "action": action},
                            created_from_route="/api/jobs",
                        )
                    else:
                        raise ValueError(f"Unsupported job type: {job_type}")
                    self._send_json({"job": job_payload}, status=HTTPStatus.ACCEPTED)
                except Exception as exc:  # noqa: BLE001
                    activity.log("api.jobs.error", error=str(exc))
                    self._send_structured_error(
                        code="job_submission_failed",
                        message=str(exc),
                        status=HTTPStatus.BAD_REQUEST,
                        details={"route": "/api/jobs"},
                    )

            def _stream_events(self, query_string: str) -> None:
                params = parse_qs(query_string or "", keep_blank_values=False)
                raw_after = params.get("after", ["0"])[0]
                raw_limit = params.get("limit", ["400"])[0]
                raw_once = params.get("once", ["0"])[0]
                raw_timeout = params.get("timeout", ["15"])[0]
                try:
                    after_seq = max(0, int(raw_after))
                except ValueError:
                    after_seq = 0
                try:
                    limit = max(1, int(raw_limit))
                except ValueError:
                    limit = 400
                once = str(raw_once).strip().lower() in {"1", "true", "yes"}
                try:
                    wait_timeout = max(0.25, float(raw_timeout))
                except ValueError:
                    wait_timeout = 15.0

                self.send_response(HTTPStatus.OK)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-store")
                self.send_header("Connection", "close" if once else "keep-alive")
                self._send_security_headers()
                self.end_headers()
                if once:
                    self.close_connection = True

                def _write_event(event_payload: dict[str, Any]) -> None:
                    payload_text = json.dumps(event_payload)
                    message = (
                        f"id: {event_payload['seq']}\n"
                        f"event: {event_payload['event_type']}\n"
                        f"data: {payload_text}\n\n"
                    )
                    self.wfile.write(message.encode("utf-8"))
                    self.wfile.flush()

                try:
                    current_after = after_seq
                    if server._shutdown_event.is_set():
                        return
                    initial_events = server.structured_events_after(current_after, limit=limit)
                    for event_payload in initial_events:
                        if server._shutdown_event.is_set():
                            return
                        _write_event(event_payload)
                        current_after = int(event_payload["seq"])
                    if once:
                        return
                    while True:
                        if server._shutdown_event.is_set():
                            return
                        if not server.wait_for_structured_events(
                            current_after, timeout=wait_timeout
                        ):
                            if server._shutdown_event.is_set():
                                return
                            self.wfile.write(b": keepalive\n\n")
                            self.wfile.flush()
                            continue
                        if server._shutdown_event.is_set():
                            return
                        next_events = server.structured_events_after(current_after, limit=limit)
                        for event_payload in next_events:
                            if server._shutdown_event.is_set():
                                return
                            _write_event(event_payload)
                            current_after = int(event_payload["seq"])
                except OSError as exc:
                    if not is_expected_disconnect_error(exc):
                        raise

            def _choose_dialog_path(self) -> None:
                try:
                    payload = self._read_json()
                    kind = str(payload.get("kind", ""))
                    requested_current = (
                        None if payload.get("current") in {"", None} else str(payload["current"])
                    )
                    home = None if payload.get("home") in {"", None} else str(payload["home"])
                    active_project_path = (
                        None if controller.project_path is None else str(controller.project_path)
                    )
                    chooser_current = _dialog_chooser_current(
                        kind,
                        requested_current,
                        home,
                        active_project_path,
                    )
                    activity.log(
                        "api.dialog.path.start",
                        kind=kind,
                        current=requested_current,
                        home=home,
                        chooser_current=chooser_current,
                    )
                    selected_path = path_chooser(kind, chooser_current) or ""
                    activity.log(
                        "api.dialog.path.success",
                        kind=kind,
                        current=requested_current,
                        home=home,
                        chooser_current=chooser_current,
                        selected=selected_path,
                    )
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
                self._send_json(activity.snapshot(after_seq=after_seq, limit=limit))

            def _browser_state(self) -> dict[str, Any]:
                payload = browser_state(
                    controller.project,
                    controller.status_message,
                    settings=controller.effective_settings().to_dict(),
                    settings_layers=controller.settings_layers(),
                    practiscore_options=controller.practiscore_browser_state(),
                    media_cache_token=server._media_url_token,
                    controller=controller,
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
                payload["project"]["path"] = (
                    "" if controller.project_path is None else str(controller.project_path)
                )
                return payload

            def _start_practiscore_session(self) -> None:
                try:
                    payload = self._read_json()
                    defer_external_open = bool(payload.get("defer_external_open"))
                    with controller_lock:
                        status = practiscore_session.start_login_flow(
                            external_open=not defer_external_open
                        )
                    activity.log(
                        "api.practiscore.session.start",
                        state=status.state,
                        defer_external_open=defer_external_open,
                    )
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
                    electron_host_enabled = (
                        self.headers.get(_PRACTISCORE_ELECTRON_HOST_HEADER) == "1"
                    )
                    if electron_host_enabled:
                        session_payload = self._read_json_header(
                            _PRACTISCORE_ELECTRON_SESSION_HEADER
                        )
                        matches_payload = self._read_json_header(
                            _PRACTISCORE_ELECTRON_MATCHES_HEADER
                        )
                        with controller_lock:
                            payload = (
                                practiscore_sync_service.list_practiscore_matches_from_host_payload(
                                    controller,
                                    session_payload,
                                    matches_payload,
                                )
                            )
                    else:
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
                    electron_host_enabled = (
                        self.headers.get(_PRACTISCORE_ELECTRON_HOST_HEADER) == "1"
                    )
                    if electron_host_enabled and isinstance(
                        payload.get("__electron_host_download"),
                        dict,
                    ):
                        session_payload = self._read_json_header(
                            _PRACTISCORE_ELECTRON_SESSION_HEADER
                        )
                        with controller_lock:
                            result = (
                                practiscore_sync_service.start_practiscore_sync_from_host_payload(
                                    controller,
                                    payload,
                                    session_payload,
                                    app_dir=practiscore_session.profile_paths.app_dir,
                                )
                            )
                            controller.autosave_project_if_needed()
                    else:
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
                    if payload.get("description") is None
                    else str(payload["description"]),
                )

            def _set_practiscore_context(self, payload: dict[str, Any]) -> None:
                controller.set_practiscore_context(
                    match_type=None
                    if payload.get("match_type") is None
                    else str(payload.get("match_type", "")),
                    stage_number=(
                        None
                        if payload.get("stage_number") in {None, ""}
                        else int(payload["stage_number"])
                    ),
                    competitor_name=(
                        None
                        if payload.get("competitor_name") is None
                        else str(payload.get("competitor_name", ""))
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
                source = next(
                    (item for item in controller.project.merge_sources if item.id == source_id),
                    None,
                )
                if source is None or not source.asset.path:
                    activity.log("media.missing", source_id=source_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_media(Path(source.asset.path))

            def _send_workspace_stage_media(self, stage_id: str) -> None:
                normalized_stage_id = unquote(str(stage_id or "")).strip()
                if not normalized_stage_id:
                    activity.log("workspace_stage_media.missing", stage_id=stage_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    stage_project_file = controller._workspace_stage_project_file(
                        normalized_stage_id
                    )
                except Exception:
                    stage_project_file = None
                if stage_project_file is None or not Path(stage_project_file).is_file():
                    activity.log("workspace_stage_media.missing", stage_id=normalized_stage_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                try:
                    stage_project = load_project(Path(stage_project_file).parent)
                except Exception:
                    activity.log(
                        "workspace_stage_media.load_failed",
                        stage_id=normalized_stage_id,
                        project_file=str(stage_project_file),
                    )
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                primary_video_path_value = str(
                    getattr(stage_project.primary_video, "path", "") or ""
                ).strip()
                if not primary_video_path_value:
                    activity.log("workspace_stage_media.missing", stage_id=normalized_stage_id)
                    self.send_error(HTTPStatus.NOT_FOUND)
                    return
                self._send_media(Path(primary_video_path_value))

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
                length = int(self.headers.get("Content-Length", "0") or 0)
                if length <= 0:
                    raise ValueError("Video file is required")
                if length > MAX_BROWSER_UPLOAD_BYTES:
                    max_gib = MAX_BROWSER_UPLOAD_BYTES // (1024 * 1024 * 1024)
                    raise ValueError(
                        f"Browser upload exceeds the {max_gib} GiB limit. Use the path import field for larger local media files."
                    )

                form = cgi.FieldStorage(
                    fp=self.rfile,
                    headers=self.headers,
                    environ={
                        "REQUEST_METHOD": "POST",
                        "CONTENT_TYPE": content_type,
                        "CONTENT_LENGTH": str(length),
                    },
                    keep_blank_values=True,
                )
                if "file" not in form:
                    raise ValueError("Multipart request must contain a file field named 'file'")
                file_field = form["file"]
                if isinstance(file_field, list):
                    file_field = file_field[0]
                uploaded_file = getattr(file_field, "file", None)
                filename = getattr(file_field, "filename", None) or "video.mp4"
                if uploaded_file is None:
                    raise ValueError("Video file is required")
                safe_name = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(filename).name).strip("._")
                if not safe_name:
                    safe_name = "video.mp4"

                target = session_path / f"{uuid4().hex}_{safe_name}"
                with target.open("wb") as output_file:
                    shutil.copyfileobj(uploaded_file, output_file, length=64 * 1024)

                if not target.exists() or target.stat().st_size <= 0:
                    target.unlink(missing_ok=True)
                    raise ValueError("Video file is required")
                display_names[str(target)] = Path(filename).name
                return target

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

            def _new_workspace(self, payload: dict[str, Any]) -> None:
                controller.new_workspace()

            def _open_workspace(self, payload: dict[str, Any]) -> None:
                controller.open_workspace(str(payload["path"]))

            def _save_workspace(self, payload: dict[str, Any]) -> None:
                path_value = payload.get("path")
                controller.save_workspace(path_value)

            def _workspace_add_stage(self, payload: dict[str, Any]) -> None:
                controller.workspace_add_stage(
                    str(payload["stage_id"]),
                    str(payload.get("display_name", "")),
                    str(payload.get("project_path", "")),
                )

            def _workspace_remove_stage(self, payload: dict[str, Any]) -> None:
                controller.workspace_remove_stage(str(payload["stage_id"]))

            def _workspace_open_stage(self, payload: dict[str, Any]) -> None:
                error = controller.workspace_open_stage(str(payload["stage_id"]))
                if error is not None:
                    controller._set_status(f"Failed to open stage: {error['reason']}")

            def _workspace_return_to_workspace(self, payload: dict[str, Any]) -> None:
                controller.workspace_return_to_workspace()

            def _workspace_set_defaults(self, payload: dict[str, Any]) -> None:
                controller.workspace_set_defaults(payload)

            def _workspace_set_stage_override(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload.pop("stage_id"))
                controller.workspace_set_stage_override(stage_id, payload)

            def _workspace_reset_stage_override(self, payload: dict[str, Any]) -> None:
                stage_id = str(payload["stage_id"])
                keys = payload.get("keys")
                controller.workspace_reset_stage_override(stage_id, keys)

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
                    controller.adjust_merge_source_sync_offset(
                        str(source_id), int(payload["sync_delta_ms"])
                    )
                    return
                normalized_payload = _normalize_merge_source_update_payload(payload)
                controller.set_merge_source_position(
                    str(source_id),
                    None
                    if payload.get("pip_size_percent") in {None, ""}
                    else int(payload["pip_size_percent"]),
                    None if payload.get("pip_x") in {None, ""} else float(payload["pip_x"]),
                    None if payload.get("pip_y") in {None, ""} else float(payload["pip_y"]),
                    None if payload.get("opacity") in {None, ""} else float(payload["opacity"]),
                    None
                    if normalized_payload["angle_role"] in {None, ""}
                    else str(normalized_payload["angle_role"]),
                    None
                    if normalized_payload["placement_mode"] in {None, ""}
                    else str(normalized_payload["placement_mode"]),
                    None
                    if normalized_payload["placement_slot"] in {None, ""}
                    else str(normalized_payload["placement_slot"]),
                    None
                    if normalized_payload["target_kind"] in {None, ""}
                    else str(normalized_payload["target_kind"]),
                    None
                    if normalized_payload["target_source_id"] in {None, ""}
                    else str(normalized_payload["target_source_id"]),
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

            def _handle_merge_source_trim(self, body: dict[str, Any]) -> dict[str, Any]:
                normalized_body = _normalize_merge_source_trim_payload(body)
                requested_source_id = normalized_body.get("source_id") or normalized_body.get("id")
                if requested_source_id in {None, ""}:
                    raise ValueError("source_id is required")

                with controller_lock:
                    trimmed_source = controller.trim_merge_source_from_payload(normalized_body)
                    server._bump_media_url_token()
                    controller.autosave_project_if_needed()
                    state_payload = self._browser_state()

                merge_source_payload = _merge_source_payload_from_browser_state(
                    state_payload,
                    str(trimmed_source.id),
                )
                if merge_source_payload is None:
                    raise RuntimeError("Updated merge source state is unavailable after trimming.")
                state_payload["merge_source"] = merge_source_payload
                return state_payload

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
                output_path = Path(str(payload["path"]))
                server._jobs.run_inline(
                    job_type="export",
                    scope_type="project",
                    scope_id=_normalize_scope_id(getattr(controller.project, "id", None)),
                    queued_message=f"Queued export to {output_path}.",
                    started_message=f"Exporting video to {output_path}.",
                    completed_message=f"Exported video to {output_path}.",
                    runner=lambda handle: self._perform_export(payload, handle),
                    detail={"route": "/api/export", "output_path": str(output_path)},
                    created_from_route="/api/export",
                )

            def _library_record_score(self, record: dict[str, Any]) -> float | None:
                metric_summary = record.get("metric_summary")
                summary = metric_summary if isinstance(metric_summary, dict) else {}
                aggregate_summary = record.get("aggregate_metric_summary")
                aggregate = aggregate_summary if isinstance(aggregate_summary, dict) else {}
                candidates = [
                    record.get("score"),
                    record.get("score_total"),
                    summary.get("score"),
                    summary.get("score_total"),
                    summary.get("hit_factor"),
                    aggregate.get("score"),
                    aggregate.get("score_total"),
                ]
                for candidate in candidates:
                    if candidate in {None, ""}:
                        continue
                    try:
                        return float(candidate)
                    except (TypeError, ValueError):
                        continue
                return None

            def _normalize_stage_library_record(self, record: dict[str, Any]) -> dict[str, Any]:
                normalized = dict(record or {})
                metric_summary = normalized.get("metric_summary")
                summary = dict(metric_summary) if isinstance(metric_summary, dict) else {}
                if not summary:
                    if normalized.get("first_shot_reaction_ms") not in {None, ""}:
                        summary["first_shot_reaction"] = normalized.get("first_shot_reaction_ms")
                    if normalized.get("cumulative_time_ms") not in {None, ""}:
                        summary["cumulative_time"] = normalized.get("cumulative_time_ms")
                    if normalized.get("penalties") not in {None, ""}:
                        summary["penalties"] = normalized.get("penalties")
                    if normalized.get("score") not in {None, ""}:
                        summary["score"] = normalized.get("score")
                    if normalized.get("score_total") not in {None, ""}:
                        summary["score_total"] = normalized.get("score_total")
                editor_target = normalized.get("editor_target")
                normalized["metric_summary"] = summary
                normalized["editor_target"] = (
                    dict(editor_target) if isinstance(editor_target, dict) else {}
                )
                normalized["tags"] = [str(tag) for tag in (normalized.get("tags") or [])]
                normalized["notes"] = str(normalized.get("notes") or "")
                normalized["score"] = self._library_record_score(
                    {**normalized, "metric_summary": summary}
                )
                normalized["project_path"] = normalized.get("project_path") or normalized[
                    "editor_target"
                ].get("project_path", "")
                normalized["workspace_path"] = normalized.get("workspace_path") or normalized[
                    "editor_target"
                ].get("workspace_path", "")
                return normalized

            def _normalize_match_library_record(self, record: dict[str, Any]) -> dict[str, Any]:
                normalized = dict(record or {})
                aggregate_summary = normalized.get("aggregate_metric_summary")
                summary = dict(aggregate_summary) if isinstance(aggregate_summary, dict) else {}
                editor_target = normalized.get("editor_target")
                stage_ids = normalized.get("stage_ids") or summary.get("stages") or []
                normalized["aggregate_metric_summary"] = summary
                normalized["editor_target"] = (
                    dict(editor_target) if isinstance(editor_target, dict) else {}
                )
                normalized["stage_ids"] = [str(stage_id) for stage_id in stage_ids]
                normalized["stage_count"] = (
                    normalized.get("stage_count")
                    or summary.get("stage_count")
                    or len(normalized["stage_ids"])
                )
                normalized["tags"] = [str(tag) for tag in (normalized.get("tags") or [])]
                normalized["notes"] = str(normalized.get("notes") or "")
                normalized["workspace_path"] = normalized.get("workspace_path") or normalized[
                    "editor_target"
                ].get("workspace_path", "")
                normalized["score"] = self._library_record_score(
                    {**normalized, "aggregate_metric_summary": summary}
                )
                return normalized

            def _library_stage_rows(self) -> list[dict[str, Any]]:
                from splitshot.persistence.library import read_stage_metrics, read_stage_records

                records = read_stage_records() or read_stage_metrics()
                return [self._normalize_stage_library_record(record) for record in records]

            def _library_match_rows(self) -> list[dict[str, Any]]:
                from splitshot.persistence.library import read_match_metrics, read_match_records

                records = read_match_records() or read_match_metrics()
                return [self._normalize_match_library_record(record) for record in records]

            def _library_sort_key(
                self, record: dict[str, Any], sort_by: str
            ) -> tuple[int, float | str]:
                if sort_by == "score":
                    score = self._library_record_score(record)
                    return (0 if score is not None else 1, score if score is not None else 0.0)
                if sort_by == "display_name":
                    return (
                        0,
                        str(record.get("display_name") or record.get("competitor_name") or ""),
                    )
                if sort_by == "discipline":
                    return (0, str(record.get("discipline") or ""))
                return (0, str(record.get(sort_by) or record.get("event_date") or ""))

            def _library_matches_search(self, record: dict[str, Any], query_text: str) -> bool:
                normalized_query = query_text.strip().lower()
                if not normalized_query:
                    return True
                haystacks = [
                    record.get("display_name"),
                    record.get("competitor_name"),
                    record.get("discipline"),
                    record.get("event_date"),
                    record.get("stage_id"),
                    record.get("match_id"),
                    record.get("library_record_id"),
                    " ".join(record.get("stage_ids") or []),
                ]
                return any(normalized_query in str(value or "").lower() for value in haystacks)

            def _handle_library_list(self) -> dict[str, Any]:
                """Return paginated list of library records."""
                stage_metrics = sorted(
                    self._library_stage_rows(),
                    key=lambda record: str(record.get("event_date") or ""),
                    reverse=True,
                )
                match_metrics = sorted(
                    self._library_match_rows(),
                    key=lambda record: str(record.get("event_date") or ""),
                    reverse=True,
                )

                return {
                    "stages": stage_metrics,
                    "matches": match_metrics,
                    "total_stages": len(stage_metrics),
                    "total_matches": len(match_metrics),
                }

            def _handle_library_filter(self, body: dict[str, Any]) -> dict[str, Any]:
                """Filter library records by criteria."""
                query = body or {}
                stage_metrics = self._library_stage_rows()
                match_metrics = self._library_match_rows()

                filtered_stages = stage_metrics
                if query.get("discipline"):
                    filtered_stages = [
                        s for s in filtered_stages if s.get("discipline") == query["discipline"]
                    ]
                    match_metrics = [
                        m for m in match_metrics if m.get("discipline") == query["discipline"]
                    ]
                query_text = str(query.get("search") or query.get("competitor") or "").strip()
                if query_text:
                    filtered_stages = [
                        s for s in filtered_stages if self._library_matches_search(s, query_text)
                    ]
                    filtered_matches = [
                        m for m in match_metrics if self._library_matches_search(m, query_text)
                    ]
                else:
                    filtered_matches = match_metrics
                if query.get("stage_id"):
                    filtered_stages = [
                        s for s in filtered_stages if s.get("stage_id") == query["stage_id"]
                    ]
                if query.get("match_id"):
                    filtered_stages = [
                        s for s in filtered_stages if s.get("match_id") == query["match_id"]
                    ]
                    filtered_matches = [
                        m for m in match_metrics if m.get("match_id") == query["match_id"]
                    ]

                sort_by = query.get("sort_by", "event_date")
                sort_order = query.get("sort_order", "desc")
                reverse = sort_order == "desc"
                if sort_by == "score":
                    scored_stages = [
                        record
                        for record in filtered_stages
                        if self._library_record_score(record) is not None
                    ]
                    unscored_stages = [
                        record
                        for record in filtered_stages
                        if self._library_record_score(record) is None
                    ]
                    scored_matches = [
                        record
                        for record in filtered_matches
                        if self._library_record_score(record) is not None
                    ]
                    unscored_matches = [
                        record
                        for record in filtered_matches
                        if self._library_record_score(record) is None
                    ]
                    scored_stages.sort(
                        key=lambda record: self._library_record_score(record) or 0.0,
                        reverse=reverse,
                    )
                    scored_matches.sort(
                        key=lambda record: self._library_record_score(record) or 0.0,
                        reverse=reverse,
                    )
                    filtered_stages = [*scored_stages, *unscored_stages]
                    filtered_matches = [*scored_matches, *unscored_matches]
                else:
                    filtered_stages.sort(
                        key=lambda record: self._library_sort_key(record, sort_by),
                        reverse=reverse,
                    )
                    filtered_matches.sort(
                        key=lambda record: self._library_sort_key(record, sort_by),
                        reverse=reverse,
                    )

                return {
                    "stages": filtered_stages,
                    "matches": filtered_matches,
                    "total_stages": len(filtered_stages),
                    "total_matches": len(filtered_matches),
                }

            def _handle_library_stage_open(self, body: dict[str, Any]) -> dict[str, Any]:
                """Get editor target for reopening a stage from library."""
                from splitshot.persistence.library import load_stage_record

                record_id = body.get("library_record_id") or body.get("stage_id")
                if not record_id:
                    return {"success": False, "error": "No record identifier provided"}

                record = load_stage_record(record_id)
                normalized_record: dict[str, Any] | None = None
                if record is not None:
                    normalized_record = self._normalize_stage_library_record(
                        {
                            "library_record_id": record.library_record_id,
                            "stage_id": record.stage_id,
                            "match_id": record.match_id,
                            "display_name": record.display_name,
                            "event_date": record.event_date.isoformat()
                            if record.event_date
                            else None,
                            "discipline": record.discipline,
                            "competitor_name": record.competitor_name,
                            "metric_summary": dict(record.metric_summary),
                            "editor_target": dict(record.editor_target),
                            "truth_hash": record.truth_hash,
                            "tags": list(record.tags),
                            "notes": record.notes,
                        }
                    )
                else:
                    normalized_record = next(
                        (
                            row
                            for row in self._library_stage_rows()
                            if row.get("library_record_id") == record_id
                            or row.get("stage_id") == record_id
                        ),
                        None,
                    )

                if normalized_record is None:
                    return {
                        "success": False,
                        "error": f"Stage record {record_id} not found",
                    }

                editor_target = dict(normalized_record.get("editor_target") or {})
                editor_target.setdefault("type", "single")
                editor_target.setdefault("stage_id", normalized_record.get("stage_id", ""))
                editor_target.setdefault("project_path", normalized_record.get("project_path", ""))
                editor_target.setdefault(
                    "workspace_path", normalized_record.get("workspace_path", "")
                )

                return {
                    "success": True,
                    "record": normalized_record,
                    "editor_target": editor_target,
                }

            def _handle_library_match_open(self, body: dict[str, Any]) -> dict[str, Any]:
                """Get editor target for reopening a match from library."""
                from splitshot.persistence.library import load_match_record

                record_id = body.get("library_record_id") or body.get("match_id")
                if not record_id:
                    return {"success": False, "error": "No record identifier provided"}

                record = load_match_record(record_id)
                normalized_record: dict[str, Any] | None = None
                if record is not None:
                    normalized_record = self._normalize_match_library_record(
                        {
                            "library_record_id": record.library_record_id,
                            "match_id": record.match_id,
                            "display_name": record.display_name,
                            "event_date": record.event_date.isoformat()
                            if record.event_date
                            else None,
                            "discipline": record.discipline,
                            "stage_ids": list(record.stage_ids),
                            "aggregate_metric_summary": dict(record.aggregate_metric_summary),
                            "editor_target": dict(record.editor_target),
                            "truth_hash": record.truth_hash,
                            "tags": list(record.tags),
                            "notes": record.notes,
                        }
                    )
                else:
                    normalized_record = next(
                        (
                            row
                            for row in self._library_match_rows()
                            if row.get("library_record_id") == record_id
                            or row.get("match_id") == record_id
                        ),
                        None,
                    )

                if normalized_record is None:
                    return {
                        "success": False,
                        "error": f"Match record {record_id} not found",
                    }

                editor_target = dict(normalized_record.get("editor_target") or {})
                editor_target.setdefault("type", "multi")
                editor_target.setdefault("match_id", normalized_record.get("match_id", ""))
                editor_target.setdefault(
                    "workspace_path", normalized_record.get("workspace_path", "")
                )

                return {
                    "success": True,
                    "record": normalized_record,
                    "editor_target": editor_target,
                }

            def _handle_proxy_status(self, body: dict[str, Any]) -> dict[str, Any]:
                """Check retained proxy status and staleness."""
                scope_type = str(body.get("scope_type") or "stage")
                scope_id = body.get("scope_id") or None
                return controller.proxy_status(scope_type, scope_id)

            def _handle_proxy_refresh(self, body: dict[str, Any]) -> dict[str, Any]:
                """Request proxy regeneration."""
                scope_type = str(body.get("scope_type") or "stage")
                scope_id = body.get("scope_id") or None
                return controller.proxy_refresh(scope_type, scope_id)

            def _handle_library_proxy_open(self, body: dict[str, Any]) -> dict[str, Any]:
                """Get path to open a retained proxy for playback."""
                scope_type = str(body.get("scope_type") or "stage")
                scope_id = body.get("scope_id") or None
                return controller.proxy_open_target(scope_type, scope_id)

            def _handle_output_profile_list(self, body: dict) -> dict:
                """List output profiles with optional filters."""
                scope_type = body.get("scope_type") or None
                scope_id = body.get("scope_id") or None
                profiles = controller.output_profile_list(scope_type, scope_id)
                return {"success": True, "profiles": profiles}

            def _handle_output_profile_create(self, body: dict) -> dict:
                """Create a new output profile."""
                scope_type = str(body.get("scope_type") or "stage")
                scope_id = str(body.get("scope_id") or controller.project.id)
                profile_name = str(body.get("profile_name") or "Default")
                profile_kind = str(body.get("profile_kind") or "stage_output")

                kwargs = {}
                for key in (
                    "frame_profile",
                    "metric_caption_preset",
                    "lead_in_card",
                    "brand_mark",
                    "subject_track_crop",
                    "visibility_recipe",
                ):
                    if key in body:
                        kwargs[key] = body[key]

                result = controller.output_profile_create(
                    scope_type, scope_id, profile_name, profile_kind, **kwargs
                )
                return {"success": True, "profile": result}

            def _handle_output_profile_update(self, body: dict) -> dict:
                """Update an existing output profile."""
                output_id = str(body.get("output_id") or "")
                if not output_id:
                    return {"success": False, "error": "output_id required"}

                kwargs = {k: v for k, v in body.items() if k != "output_id"}
                result = controller.output_profile_update(output_id, **kwargs)
                if result is None:
                    return {"success": False, "error": f"Profile {output_id} not found"}
                return {"success": True, "profile": result}

            def _handle_output_profile_delete(self, body: dict) -> dict:
                """Delete an output profile."""
                output_id = str(body.get("output_id") or "")
                if not output_id:
                    return {"success": False, "error": "output_id required"}
                deleted = controller.output_profile_delete(output_id)
                return {"success": deleted}

            def _handle_output_profile_render(self, body: dict) -> dict:
                """Get render plan for an output profile."""
                output_id = str(body.get("output_id") or "")
                if not output_id:
                    return {"success": False, "error": "output_id required"}
                return controller.output_profile_render(output_id)

            def _handle_workspace_stage_clip_list(self, body: dict) -> dict:
                """Return persisted clips for a workspace stage."""
                stage_id = str(body.get("stage_id") or "")
                if not stage_id:
                    return {"success": False, "error": "stage_id required"}
                if controller.workspace is None:
                    return {"success": False, "error": "No workspace is open"}
                if stage_id not in controller.workspace.stage_entries:
                    return {"success": False, "error": f"Stage {stage_id} not found"}
                return {
                    "success": True,
                    "stage_id": stage_id,
                    "clips": controller._get_stage_clips(stage_id),
                }

            def _handle_workspace_stage_clip_add(self, body: dict) -> dict:
                """Add a clip to a stage for composite editing."""
                stage_id = str(body.get("stage_id") or "")
                source_path = str(body.get("source_path") or "")
                angle_role = str(body.get("camera_role") or body.get("angle_role") or "primary")
                clips = controller.workspace_stage_clip_add(
                    stage_id,
                    source_path,
                    angle_role,
                    **{
                        k: v
                        for k, v in body.items()
                        if k not in ("stage_id", "source_path", "camera_role", "angle_role")
                    },
                )
                return {"success": True, "clips": clips}

            def _handle_workspace_stage_clip_update(self, body: dict) -> dict:
                """Update a clip's properties."""
                stage_id = str(body.get("stage_id") or "")
                clip_id = str(body.get("clip_id") or "")
                normalized_body = dict(body)
                if "camera_role" in normalized_body:
                    normalized_body["angle_role"] = normalized_body.pop("camera_role")
                kwargs = {
                    k: v for k, v in normalized_body.items() if k not in ("stage_id", "clip_id")
                }
                result = controller.workspace_stage_clip_update(stage_id, clip_id, **kwargs)
                if result is None:
                    return {"success": False, "error": "Clip not found"}
                return {"success": True, "clip": result}

            def _handle_workspace_stage_clip_reorder(self, body: dict) -> dict:
                """Reorder a clip within the stage composite list."""
                stage_id = str(body.get("stage_id") or "")
                clip_id = str(body.get("clip_id") or "")
                target_index = int(body.get("target_index", 0))
                clips = controller.workspace_stage_clip_reorder(stage_id, clip_id, target_index)
                if clips is None:
                    return {"success": False, "error": "Clip not found"}
                return {"success": True, "clips": clips}

            def _handle_workspace_stage_clip_remove(self, body: dict) -> dict:
                """Remove a clip from a stage."""
                stage_id = str(body.get("stage_id") or "")
                clip_id = str(body.get("clip_id") or "")
                removed = controller.workspace_stage_clip_remove(stage_id, clip_id)
                return {"success": removed}

            def _handle_angle_align(self, body: dict) -> dict:
                """Align clips for a stage."""
                stage_id = str(body.get("stage_id") or "")
                reference_clip_id = str(body.get("reference_clip_id") or "")
                return controller.angle_align(stage_id, reference_clip_id)

            def _handle_angle_director_generate(self, body: dict) -> dict:
                """Generate auto-cut plan for multi-angle composition."""
                stage_id = str(body.get("stage_id") or "")
                return controller.angle_director_generate(stage_id)

            def _handle_angle_director_plan(self, body: dict) -> dict:
                """Read current angle-director plan for a stage/output profile."""
                stage_id = str(body.get("stage_id") or "")
                output_id = str(body.get("output_id") or "")
                if not stage_id:
                    return {"success": False, "error": "stage_id required"}
                if not output_id:
                    return {"success": False, "error": "output_id required"}
                return controller.angle_director_plan(stage_id, output_id)

            def _handle_angle_director_override(self, body: dict) -> dict:
                """Override a cut in the angle director plan."""
                stage_id = str(body.get("stage_id") or "")
                clip_id = str(body.get("clip_id") or "")
                output_id = body.get("output_id")
                position = int(body.get("position", 0))
                start_ms = int(body.get("start_ms", 0))
                duration_ms = int(body.get("duration_ms", 0))
                return controller.angle_director_override_cut(
                    stage_id,
                    clip_id,
                    position,
                    start_ms,
                    duration_ms,
                    None if output_id in {None, ""} else str(output_id),
                )

            def _handle_angle_director_override_clear(self, body: dict) -> dict:
                """Clear a persisted cut override from the angle director plan."""
                stage_id = str(body.get("stage_id") or "")
                output_id = body.get("output_id")
                position = int(body.get("position", 0))
                return controller.angle_director_clear_cut(
                    stage_id,
                    position,
                    None if output_id in {None, ""} else str(output_id),
                )

            def _handle_audio_mix(self, body: dict) -> dict:
                """Set audio mix properties for a clip."""
                stage_id = str(body.get("stage_id") or "")
                clip_id = str(body.get("clip_id") or "")
                gain = body.get("gain")
                muted = body.get("muted")
                primary = body.get("primary")
                result = controller.audio_mix_set(
                    stage_id,
                    clip_id,
                    gain=float(gain) if gain is not None else None,
                    muted=bool(muted) if muted is not None else None,
                    primary=bool(primary) if primary is not None else None,
                )
                if result is None:
                    return {"success": False, "error": "Clip not found"}
                return {"success": True, "clip": result}

            def _handle_result_cards_resolve(self, body: dict) -> dict:
                """Resolve result cards for a match recap."""
                match_output_id = str(body.get("output_id") or body.get("match_output_id") or "")
                return controller.resolve_result_cards(match_output_id)

            # === Landing Page ===

            def _handle_landing_recent(self) -> dict[str, Any]:
                """Return recent activity for the landing page."""
                with controller_lock:
                    return controller.landing_recent()

            # === Workspace: Setup Once, Apply Everywhere ===

            def _handle_workspace_apply_from_first(self, body: dict[str, Any]) -> dict[str, Any]:
                """Apply Stage 1 settings to all sibling stages in the workspace."""
                with controller_lock:
                    return controller.workspace_apply_from_first()

            def _handle_workspace_apply_from_first_preview(
                self, body: dict[str, Any]
            ) -> dict[str, Any]:
                """Preview what would change before applying Stage 1 settings to siblings."""
                with controller_lock:
                    return controller.workspace_apply_from_first_preview()

            def _handle_workspace_export(self, body: dict[str, Any]) -> dict[str, Any]:
                with controller_lock:
                    stage_id = (body or {}).get("stage_id")
                    recipe = (body or {}).get("recipe")
                    return controller.workspace_export(stage_id=stage_id, recipe=recipe)

            def _handle_workspace_recap_render(self, body: dict[str, Any]) -> dict[str, Any]:
                with controller_lock:
                    return controller.workspace_recap_render(**(body or {}))

            def _handle_workspace_defaults_reset(self, body: dict[str, Any]) -> dict[str, Any]:
                with controller_lock:
                    return controller.workspace_reset_defaults()

            # === Library: Analytics ===

            def _handle_library_analytics_trend(self, body: dict[str, Any]) -> dict[str, Any]:
                """Return trend data for library analytics charts."""
                from splitshot.persistence.library import compute_analytics

                query = body or {}
                metric_key = query.get("metric_key", "score")
                discipline = query.get("discipline")
                return compute_analytics(discipline=discipline, metric_key=metric_key)

            def _handle_library_analytics_compare(self, body: dict[str, Any]) -> dict[str, Any]:
                """Compare two stages side by side."""
                query = body or {}
                stage_id_a = query.get("stage_id_a", "")
                stage_id_b = query.get("stage_id_b", "")

                all_metrics = self._library_stage_rows()
                metric_a = next((m for m in all_metrics if m.get("stage_id") == stage_id_a), None)
                metric_b = next((m for m in all_metrics if m.get("stage_id") == stage_id_b), None)

                if not metric_a or not metric_b:
                    return {"error": "One or both stages not found in library"}

                return {
                    "stage_a": {
                        "name": metric_a.get("display_name", ""),
                        "summary": metric_a.get("metric_summary", {}),
                    },
                    "stage_b": {
                        "name": metric_b.get("display_name", ""),
                        "summary": metric_b.get("metric_summary", {}),
                    },
                }

            # === Library: Archive ===

            def _handle_library_archive_create(self, body: dict[str, Any]) -> dict[str, Any]:
                """Create a compressed video archive for a library record."""
                from splitshot.persistence.library import generate_archive

                stage_id = (body or {}).get("stage_id", "")
                if not stage_id:
                    return {"error": "stage_id required"}
                return generate_archive(stage_id)

            # === Library: Tags ===

            def _handle_library_tags_update(self, body: dict[str, Any]) -> dict[str, Any]:
                """Update tags on a library record."""
                record_id = (body or {}).get("record_id", "")
                tags = (body or {}).get("tags", [])
                if not record_id:
                    return {"error": "record_id required"}

                from splitshot.persistence.library import (
                    load_stage_record,
                    load_match_record,
                    save_stage_record,
                    save_match_record,
                )

                record = load_stage_record(record_id)
                if record is not None:
                    record.tags = list(tags)
                    save_stage_record(record)
                    return {"record_id": record_id, "tags": tags, "updated": True}

                match_record = load_match_record(record_id)
                if match_record is not None:
                    match_record.tags = list(tags)
                    save_match_record(match_record)
                    return {"record_id": record_id, "tags": tags, "updated": True}

                return {"error": "Record not found", "record_id": record_id}

            # === Library: Notes ===

            def _handle_library_notes_update(self, body: dict[str, Any]) -> dict[str, Any]:
                """Update notes on a library record."""
                record_id = (body or {}).get("record_id", "")
                notes = (body or {}).get("notes", "")
                if not record_id:
                    return {"error": "record_id required"}

                from splitshot.persistence.library import (
                    load_stage_record,
                    load_match_record,
                    save_stage_record,
                    save_match_record,
                )

                record = load_stage_record(record_id)
                if record is not None:
                    record.notes = str(notes)
                    save_stage_record(record)
                    return {"record_id": record_id, "notes": notes, "updated": True}

                match_record = load_match_record(record_id)
                if match_record is not None:
                    match_record.notes = str(notes)
                    save_match_record(match_record)
                    return {"record_id": record_id, "notes": notes, "updated": True}

                return {"error": "Record not found", "record_id": record_id}

            # === Library: Export ===

            def _handle_library_export_csv(self) -> dict[str, Any]:
                """Export library records as CSV data."""
                records = [
                    *self._library_stage_rows(),
                    *self._library_match_rows(),
                ]
                lines = ["Type,Name,Date,Discipline,Score,StageCount,RecordId"]
                for r in records:
                    stage_ids = r.get("stage_ids") or []
                    stage_count = r.get("stage_count") or len(stage_ids)
                    record_type = "match" if r.get("match_id") and stage_count else "stage"
                    lines.append(
                        f'"{record_type}",'
                        f'"{r.get("display_name", "")}",'
                        f'"{r.get("event_date", "")}",'
                        f'"{r.get("discipline", "")}",'
                        f'"{r.get("score", "") if r.get("score") not in {None, ""} else ""}",'
                        f'"{stage_count if record_type == "match" else ""}",'
                        f'"{r.get("library_record_id", "")}"'
                    )

                return {
                    "format": "csv",
                    "data": "\n".join(lines),
                    "record_count": len(records),
                }

            def _handle_library_export_json(self) -> dict[str, Any]:
                """Export library records as JSON data."""
                stages = self._library_stage_rows()
                matches = self._library_match_rows()
                return {
                    "format": "json",
                    "data": {
                        "stages": stages,
                        "matches": matches,
                    },
                    "record_count": len(stages) + len(matches),
                }

            # === Library: Backup/Restore ===

            def _handle_library_backup_create(self) -> dict[str, Any]:
                """Create a backup of the library."""
                with controller_lock:
                    return controller.library_backup_create()

            def _handle_library_backup_restore(self, body: dict[str, Any]) -> dict[str, Any]:
                """Restore library from a backup manifest."""
                with controller_lock:
                    manifest = (body or {}).get("manifest", {})
                    return controller.library_backup_restore(manifest)

        return Handler
