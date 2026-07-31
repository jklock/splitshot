"""Shared controller layer that owns authoritative project mutations and settings flow."""

from __future__ import annotations

import json
import math
import re
import subprocess
from collections.abc import Callable, Iterable
from copy import deepcopy
from dataclasses import asdict, dataclass, fields, replace
from datetime import UTC, datetime
from inspect import Parameter, signature
from pathlib import Path
from typing import Any
from uuid import uuid4

from PySide6.QtCore import QObject, Signal

from splitshot.analysis.detection import (
    TimingReviewSuggestion,
    analyze_video_audio,
    timing_change_proposals_from_review_suggestions,
)
from splitshot.analysis.sync import compute_sync_offset
from splitshot.config import (
    AppSettings,
    delete_folder_settings,
    load_folder_settings,
    load_settings,
    save_folder_settings,
    save_settings,
)
from splitshot.domain.models import (
    AnalysisState,
    AspectRatio,
    BadgeSize,
    BadgeStyle,
    CombinedExportSettings,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    MergeSource,
    MergeSourceAssetPathKind,
    MergeSourceTrimDerivative,
    OutputProfile,
    OutputProfileKind,
    OverlayPosition,
    OverlaySettings,
    OverlayTextBox,
    PipSize,
    PopupBubble,
    PopupTemplate,
    Project,
    ProjectStage,
    QueueEntry,
    QueueStatus,
    ScoreLetter,
    ScoreMark,
    SecondarySourceAnalysis,
    ShotEvent,
    ShotMLSettings,
    ShotSource,
    TimingChangeProposal,
    TimingEvent,
    UIState,
    VideoAsset,
    _deserialize_output_profiles,
    _merge_source_from_dict,
    _normalize_frame_profile,
    _normalize_output_profile_export_settings,
    _popup_bubble_from_dict,
    _serialize_output_profiles,
    legacy_custom_box_as_text_box,
    overlay_text_boxes_for_render,
    project_to_dict,
    stage_to_dict,
    sync_overlay_legacy_custom_box_fields,
)
from splitshot.export.presets import apply_export_preset as apply_export_preset_settings
from splitshot.media.ffmpeg import MediaError, run_ffmpeg, run_ffprobe_json, trim_video
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import (
    INPUT_DIRNAME,
    INTRO_OUTRO_DIRNAME,
    POPUP_DIRNAME,
    PRACTISCORE_DIRNAME,
    copy_path_to_project_subdir,
    default_project_output_path,
    delete_project,
    ensure_project_suffix,
    load_project,
    normalize_project_path,
    project_has_metadata,
    save_project,
)
from splitshot.scoring.logic import (
    apply_scoring_preset,
    calculate_hit_factor,
    default_score_mark_for_ruleset,
    ensure_default_shot_scores,
    format_imported_stage_overlay_text,
    format_review_summary_overlay_text,
)
from splitshot.scoring.practiscore import (
    PractiScoreCompetitorOption,
    PractiScoreOptions,
    _normalize_name,
    default_ruleset_for_match_type,
    describe_practiscore_file,
    normalize_match_type,
)
from splitshot.scoring.practiscore_sync_normalize import normalize_downloaded_practiscore_artifact
from splitshot.scoring.practiscore_web_extract import (
    EXPIRED_AUTHENTICATION_ERROR,
    MALFORMED_REMOTE_RESPONSE_ERROR,
    NORMALIZATION_IMPORT_FAILURE_ERROR,
    TRANSIENT_NETWORK_FAILURE_ERROR,
    PractiScoreSyncError,
    RemotePractiScoreMatch,
    discover_remote_matches,
    download_remote_match_artifacts,
    practiscore_sync_audit_root,
)
from splitshot.timeline.model import (
    normalize_project_timing_events,
    normalized_timing_event_for_shots,
    sort_shots,
)

VALID_OVERLAY_BADGE_NAMES = {
    "timer_badge",
    "shot_badge",
    "current_shot_badge",
    "hit_factor_badge",
}

_PRACTISCORE_FILE_SUFFIXES = {".csv", ".txt"}
_DEFAULT_SUMMARY_METRIC_IDS = (
    "score_time",
    "raw_time",
    "points_down",
    "penalties",
    "division_placement",
    "class_placement",
    "overall_placement",
)

_VALID_BROWSER_UI_TOOLS = {
    "project",
    "scoring",
    "shotml",
    "timing",
    "merge",
    "overlay",
    "review",
    "popup",
    "markers",
    "settings",
    "export",
    "metrics",
}

_VALID_WAVEFORM_MODES = {"select", "add"}

_PRACTISCORE_SYNC_UNSET = object()
_VALID_PRACTISCORE_SYNC_STATES = {
    "idle",
    "discovering_matches",
    "match_list_ready",
    "importing_selected_match",
    "success",
    "error",
}


def _default_practiscore_session_payload() -> dict[str, object]:
    return {
        "state": "not_authenticated",
        "message": "Connect PractiScore to use your browser session for background sync.",
        "details": {},
    }


def _default_practiscore_sync_payload() -> dict[str, object]:
    return {
        "state": "idle",
        "message": "No remote PractiScore sync activity yet.",
        "matches": [],
        "selected_remote_id": None,
        "error_category": "",
        "details": {},
    }


def _practiscore_session_payload_from_status(status: object) -> dict[str, object]:
    payload = _default_practiscore_session_payload()
    if isinstance(status, dict):
        source = status
    else:
        to_dict = getattr(status, "to_dict", None)
        if callable(to_dict):
            source = to_dict()
        else:
            source = {
                "state": getattr(status, "state", payload["state"]),
                "message": getattr(status, "message", payload["message"]),
                "details": getattr(status, "details", payload["details"]),
            }
    payload["state"] = str(source.get("state") or payload["state"])
    payload["message"] = str(source.get("message") or payload["message"])
    details = source.get("details")
    payload["details"] = dict(details) if isinstance(details, dict) else {}
    return payload


def _practiscore_session_payload_from_manager(practiscore_session: object) -> dict[str, object]:
    current_status = getattr(practiscore_session, "current_status", None)
    if callable(current_status):
        return _practiscore_session_payload_from_status(current_status())
    serialize_status = getattr(practiscore_session, "serialize_status", None)
    if callable(serialize_status):
        return _practiscore_session_payload_from_status(serialize_status())
    return _default_practiscore_session_payload()


def _serialize_practiscore_remote_matches(matches: object) -> list[dict[str, object]]:
    if not isinstance(matches, list):
        return []
    payloads: list[dict[str, object]] = []
    for item in matches:
        match = (
            item
            if isinstance(item, RemotePractiScoreMatch)
            else RemotePractiScoreMatch.from_dict(item)
        )
        if match is None:
            continue
        payloads.append(match.to_dict())
    return payloads


def _practiscore_remote_match_objects(matches: object) -> list[RemotePractiScoreMatch]:
    if not isinstance(matches, list):
        return []
    resolved: list[RemotePractiScoreMatch] = []
    for item in matches:
        match = (
            item
            if isinstance(item, RemotePractiScoreMatch)
            else RemotePractiScoreMatch.from_dict(item)
        )
        if match is not None:
            resolved.append(match)
    return resolved


def _practiscore_error_category_from_exception(exc: BaseException) -> str:
    message = str(exc).lower()
    if any(
        token in message
        for token in ("timeout", "timed out", "network", "fetch", "net::", "connection")
    ):
        return TRANSIENT_NETWORK_FAILURE_ERROR
    return MALFORMED_REMOTE_RESPONSE_ERROR


@dataclass(slots=True)
class _OriginalShotState:
    time_ms: int
    source: ShotSource
    confidence: float | None
    score: ScoreMark | None


@dataclass(slots=True)
class _ShotSelectionContext:
    shot_id: str
    time_ms: int
    index: int
    fallback_mode: str = "time"


def _pip_size_percent_from_enum(size: PipSize) -> int:
    return {
        PipSize.SMALL: 25,
        PipSize.MEDIUM: 35,
        PipSize.LARGE: 50,
    }[size]


def _badge_font_size_from_enum(size: BadgeSize) -> int:
    return {
        BadgeSize.XS: 10,
        BadgeSize.S: 12,
        BadgeSize.M: 14,
        BadgeSize.L: 16,
        BadgeSize.XL: 20,
        BadgeSize.CUSTOM: 14,
    }[size]


def _float_matches(left: float | None, right: float | None, *, tolerance: float = 1e-6) -> bool:
    if left is None or right is None:
        return left == right
    return abs(float(left) - float(right)) <= tolerance


def _optional_layout_dimension(value: object, minimum: int, maximum: int) -> int | None:
    if value in {None, ""}:
        return None
    return max(minimum, min(maximum, int(value)))


def _optional_payload_bool(value: object) -> bool | None:
    if value in {None, ""}:
        return None
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _normalize_popup_motion_mode(value: object, *, follow_motion: bool = False) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"fixed", "guided", "manual", "auto"} and not (
        normalized == "fixed" and follow_motion
    ):
        return normalized
    return "manual" if follow_motion else "fixed"


def _badge_style_from_payload(style: BadgeStyle, payload: object) -> None:
    if not isinstance(payload, dict):
        return
    if "background_color" in payload:
        style.background_color = str(
            payload.get("background_color", style.background_color) or style.background_color
        )
    if "text_color" in payload:
        style.text_color = str(payload.get("text_color", style.text_color) or style.text_color)
    if "opacity" in payload:
        raw_opacity = payload.get("opacity")
        if raw_opacity not in {None, ""}:
            style.opacity = max(0.0, min(1.0, float(raw_opacity)))


def _popup_template_from_payload(template: PopupTemplate, payload: object) -> None:
    if not isinstance(payload, dict):
        return
    if "enabled" in payload:
        template.enabled = bool(payload.get("enabled", template.enabled))
    if "content_type" in payload:
        template.content_type = str(
            payload.get("content_type", template.content_type) or template.content_type
        )
    if "text_source" in payload:
        template.text_source = str(
            payload.get("text_source", template.text_source) or template.text_source
        )
    if "duration_ms" in payload:
        raw_duration = payload.get("duration_ms")
        if raw_duration not in {None, ""}:
            template.duration_ms = max(1, int(raw_duration))
    if "use_shot_split_duration" in payload:
        template.use_shot_split_duration = bool(
            payload.get("use_shot_split_duration", template.use_shot_split_duration)
        )
    if "quadrant" in payload:
        template.quadrant = str(payload.get("quadrant", template.quadrant) or template.quadrant)
    if "width" in payload:
        raw_width = payload.get("width")
        if raw_width not in {None, ""}:
            template.width = max(0, int(raw_width))
    if "height" in payload:
        raw_height = payload.get("height")
        if raw_height not in {None, ""}:
            template.height = max(0, int(raw_height))
    if "follow_motion" in payload:
        template.follow_motion = bool(payload.get("follow_motion", template.follow_motion))
    if "motion_mode" in payload:
        template.motion_mode = _normalize_popup_motion_mode(
            payload.get("motion_mode", template.motion_mode),
            follow_motion=template.follow_motion,
        )
    if "background_color" in payload:
        template.background_color = str(
            payload.get("background_color", template.background_color) or template.background_color
        )
    if "text_color" in payload:
        template.text_color = str(
            payload.get("text_color", template.text_color) or template.text_color
        )
    if "opacity" in payload:
        raw_opacity = payload.get("opacity")
        if raw_opacity not in {None, ""}:
            template.opacity = max(0.0, min(1.0, float(raw_opacity)))
    if "style_type" in payload:
        template.style_type = str(
            payload.get("style_type", template.style_type) or template.style_type
        )
    if "font_family" in payload:
        template.font_family = str(
            payload.get("font_family", template.font_family) or template.font_family
        )[:80]
    if "font_size" in payload:
        raw_font_size = payload.get("font_size")
        if raw_font_size not in {None, ""}:
            template.font_size = max(8, min(72, int(raw_font_size)))
    if "font_bold" in payload:
        template.font_bold = bool(payload.get("font_bold", template.font_bold))
    if "font_italic" in payload:
        template.font_italic = bool(payload.get("font_italic", template.font_italic))


def _overlay_text_boxes_to_payload(boxes: list[OverlayTextBox]) -> list[dict[str, object]]:
    return [asdict(box) for box in boxes]


def _settings_template_payload(settings: AppSettings) -> dict[str, object]:
    return settings.template_snapshot()


def _practiscore_name_matches(input_name: str, candidate_name: str) -> bool:
    if _normalize_name(input_name) == _normalize_name(candidate_name):
        return True
    input_parts = sorted(part for part in re.split(r"[^A-Za-z0-9]+", input_name.lower()) if part)
    candidate_parts = sorted(
        part for part in re.split(r"[^A-Za-z0-9]+", candidate_name.lower()) if part
    )
    return bool(input_parts) and input_parts == candidate_parts


def _normalize_media_name_fragment(value: str) -> str:
    return re.sub(r"\d+", lambda match: str(int(match.group(0))), value.lower())


def _media_name_tokens(path: str | Path) -> set[str]:
    stem = _normalize_media_name_fragment(Path(path).stem)
    return {token for token in re.split(r"[^a-z0-9]+", stem) if token}


def _project_media_recovery_score(
    expected_path: str,
    expected_asset: VideoAsset,
    candidate_path: Path,
    candidate_asset: VideoAsset,
) -> int:
    if expected_asset.is_still_image != candidate_asset.is_still_image:
        return -1
    if (
        expected_asset.width
        and candidate_asset.width
        and expected_asset.width != candidate_asset.width
    ):
        return -1
    if (
        expected_asset.height
        and candidate_asset.height
        and expected_asset.height != candidate_asset.height
    ):
        return -1
    if expected_asset.rotation != candidate_asset.rotation:
        return -1
    if expected_asset.duration_ms and candidate_asset.duration_ms:
        duration_delta = abs(expected_asset.duration_ms - candidate_asset.duration_ms)
        if duration_delta > 2000:
            return -1
    else:
        duration_delta = None
    fps_delta = abs(expected_asset.fps - candidate_asset.fps)
    if expected_asset.fps and candidate_asset.fps and fps_delta > 1.0:
        return -1

    expected_name = Path(expected_path).name.lower()
    expected_stem = Path(expected_path).stem.lower()
    expected_name_normalized = _normalize_media_name_fragment(Path(expected_path).name)
    expected_stem_normalized = _normalize_media_name_fragment(Path(expected_path).stem)
    candidate_name = candidate_path.name.lower()
    candidate_stem = candidate_path.stem.lower()
    candidate_name_normalized = _normalize_media_name_fragment(candidate_path.name)
    candidate_stem_normalized = _normalize_media_name_fragment(candidate_path.stem)
    score = 0

    if expected_name and candidate_name == expected_name:
        score += 1000
    elif expected_name_normalized and candidate_name_normalized == expected_name_normalized:
        score += 950
    elif expected_stem and candidate_stem == expected_stem:
        score += 900
    elif expected_stem_normalized and candidate_stem_normalized == expected_stem_normalized:
        score += 850
    elif expected_stem and (expected_stem in candidate_stem or candidate_stem in expected_stem):
        score += 700
    elif expected_stem_normalized and (
        expected_stem_normalized in candidate_stem_normalized
        or candidate_stem_normalized in expected_stem_normalized
    ):
        score += 650
    else:
        score += 120 * len(
            _media_name_tokens(expected_path).intersection(_media_name_tokens(candidate_path))
        )

    if Path(expected_path).suffix.lower() == candidate_path.suffix.lower():
        score += 20
    if expected_asset.width and candidate_asset.width == expected_asset.width:
        score += 150
    if expected_asset.height and candidate_asset.height == expected_asset.height:
        score += 150
    if duration_delta is not None:
        if duration_delta <= 50:
            score += 200
        elif duration_delta <= 250:
            score += 150
        elif duration_delta <= 1000:
            score += 100
        else:
            score += 50
    if expected_asset.fps and candidate_asset.fps:
        if fps_delta <= 0.01:
            score += 60
        elif fps_delta <= 0.1:
            score += 40
        else:
            score += 10
    if (
        expected_asset.audio_sample_rate
        and candidate_asset.audio_sample_rate == expected_asset.audio_sample_rate
    ):
        score += 25
    score += 10
    return score


def _source_supports_secondary_analysis(source: MergeSource | None) -> bool:
    if source is None:
        return False
    asset = source.asset
    return bool(asset.path) and not asset.is_still_image and asset.media_kind != "animated_gif"


def _format_trim_boundary(value: float | None) -> str:
    return "--.--" if value is None else f"{float(value):.2f}"


def _normalized_trim_window(
    asset: VideoAsset, start_s: float | None, end_s: float | None
) -> tuple[float | None, float | None]:
    normalized_start = None if start_s is None else max(0.0, float(start_s))
    normalized_end = None if end_s is None else max(0.0, float(end_s))
    duration_s = float(asset.duration_ms or 0) / 1000
    if duration_s > 0:
        if normalized_start is not None:
            normalized_start = min(normalized_start, duration_s)
        if normalized_end is not None:
            normalized_end = min(normalized_end, duration_s)
    if (
        normalized_start is not None
        and normalized_end is not None
        and normalized_start >= normalized_end
    ):
        raise ValueError("Trim start must be earlier than trim end")
    return normalized_start, normalized_end


def _merge_source_trim_derivative_is_active(source: MergeSource | None) -> bool:
    trim_derivative = getattr(source, "trim_derivative", None)
    return bool(
        trim_derivative is not None
        and trim_derivative.active_path_kind == MergeSourceAssetPathKind.LOCAL_DERIVATIVE
        and trim_derivative.derivative_path
    )


def _primary_trim_derivative_is_active(project: Project | None) -> bool:
    trim_derivative = getattr(project, "primary_trim_derivative", None)
    return bool(
        project is not None
        and trim_derivative is not None
        and trim_derivative.active_path_kind == MergeSourceAssetPathKind.LOCAL_DERIVATIVE
        and trim_derivative.derivative_path
    )


def _effective_primary_media_path(project: Project | None) -> str:
    if project is None:
        return ""
    if _primary_trim_derivative_is_active(project):
        return str(project.primary_trim_derivative.derivative_path or "")
    return str(project.primary_video.path or "")


def _effective_primary_asset(project: Project | None) -> VideoAsset:
    if project is None:
        return VideoAsset()
    if _primary_trim_derivative_is_active(project):
        derivative_asset = project.primary_trim_derivative.derivative_asset
        if derivative_asset.path:
            return derivative_asset
    return project.primary_video


def _effective_merge_source_media_path(source: MergeSource | None) -> str:
    if source is None:
        return ""
    if _merge_source_trim_derivative_is_active(source):
        return str(source.trim_derivative.derivative_path or "")
    return str(source.asset.path or "")


def _effective_merge_source_asset(source: MergeSource | None) -> VideoAsset | None:
    if source is None:
        return None
    active_path = _effective_merge_source_media_path(source)
    if not active_path:
        return None
    if active_path == source.asset.path:
        return source.asset
    derivative_asset = source.trim_derivative.derivative_asset
    if derivative_asset.path == active_path:
        return derivative_asset
    return replace(source.asset, path=active_path)


def _first_analyzable_merge_source(project: Project) -> MergeSource | None:
    for source in project.merge_sources:
        if _source_supports_secondary_analysis(source):
            return source
    return None


def _sync_secondary_video_from_merge_sources(project: Project) -> None:
    _refresh_secondary_analysis_projection(project)


def _secondary_analysis_entry_for_source(
    project: Project,
    source_id: str,
    *,
    create: bool = False,
) -> SecondarySourceAnalysis | None:
    for entry in project.analysis.secondary_sources:
        if entry.source_id == source_id:
            return entry
    if not create:
        return None
    entry = SecondarySourceAnalysis(source_id=source_id)
    project.analysis.secondary_sources.append(entry)
    return entry


def _prune_secondary_analysis_entries(project: Project) -> None:
    valid_source_ids = {
        source.id for source in project.merge_sources if _source_supports_secondary_analysis(source)
    }
    project.analysis.secondary_sources = [
        entry for entry in project.analysis.secondary_sources if entry.source_id in valid_source_ids
    ]


def _refresh_secondary_analysis_projection(
    project: Project,
    *,
    preferred_source_id: str | None = None,
) -> None:
    _prune_secondary_analysis_entries(project)
    analyzable_sources = [
        source for source in project.merge_sources if _source_supports_secondary_analysis(source)
    ]
    if not analyzable_sources:
        project.secondary_video = None
        project.analysis.beep_time_ms_secondary = None
        project.analysis.analyzed_secondary_source_id = None
        project.analysis.secondary_analysis_status = "idle"
        project.analysis.secondary_analysis_message = ""
        project.analysis.waveform_secondary = []
        return

    selected_source = None
    if preferred_source_id:
        selected_source = next(
            (source for source in analyzable_sources if source.id == preferred_source_id), None
        )
    if selected_source is None and project.analysis.analyzed_secondary_source_id:
        selected_source = next(
            (
                source
                for source in analyzable_sources
                if source.id == project.analysis.analyzed_secondary_source_id
            ),
            None,
        )
    if selected_source is None:
        selected_source = analyzable_sources[0]
    entry = _secondary_analysis_entry_for_source(project, selected_source.id, create=False)
    project.secondary_video = _effective_merge_source_asset(selected_source)
    project.analysis.analyzed_secondary_source_id = selected_source.id
    if entry is None:
        project.analysis.beep_time_ms_secondary = None
        project.analysis.secondary_analysis_status = "idle"
        project.analysis.secondary_analysis_message = ""
        project.analysis.secondary_sync_source = "manual"
        project.analysis.waveform_secondary = []
        project.analysis.sync_offset_ms = int(selected_source.sync_offset_ms)
        return
    project.analysis.beep_time_ms_secondary = entry.beep_time_ms
    project.analysis.secondary_analysis_status = entry.analysis_status
    project.analysis.secondary_analysis_message = entry.analysis_message
    project.analysis.secondary_sync_source = entry.sync_source
    project.analysis.waveform_secondary = list(entry.waveform)
    project.analysis.sync_offset_ms = int(entry.sync_offset_ms)


def _clear_secondary_analysis_state(
    project: Project, *, preserve_sync_offset: bool = False
) -> None:
    project.analysis.beep_time_ms_secondary = None
    project.analysis.analyzed_secondary_source_id = None
    project.analysis.secondary_analysis_status = "idle"
    project.analysis.secondary_analysis_message = ""
    project.analysis.waveform_secondary = []
    project.analysis.secondary_sources = []
    if not preserve_sync_offset:
        project.analysis.sync_offset_ms = 0
        project.analysis.secondary_sync_source = "manual"


def _reset_media_dependent_state_for_primary_video(project: Project) -> None:
    project.primary_trim_derivative = MergeSourceTrimDerivative()
    project.analysis.beep_time_ms_primary = None
    _clear_secondary_analysis_state(project)
    project.analysis.waveform_primary = []
    project.analysis.shots = []
    project.analysis.events = []
    project.analysis.timing_change_proposals = []
    project.analysis.last_shotml_run_summary = {}
    if project.scoring.imported_stage is None:
        project.scoring.penalties = 0.0
        project.scoring.penalty_counts = {}
        project.scoring.hit_factor = None
    project.secondary_video = None
    project.merge_sources = []
    project.merge.enabled = False
    _reset_project_merge_defaults(project)
    project.merge.primary_is_left_or_top = True
    project.overlay.custom_box_text = ""
    for text_box in project.overlay.text_boxes:
        text_box.text = ""
    sync_overlay_legacy_custom_box_fields(project.overlay)
    project.popups = []
    project.export.last_log = ""
    project.export.last_error = None
    project.ui_state.selected_shot_id = None


def _reset_project_merge_defaults(project: Project) -> None:
    project.merge.layout = MergeLayout.SIDE_BY_SIDE
    project.merge.pip_size = PipSize.MEDIUM
    project.merge.pip_size_percent = _pip_size_percent_from_enum(PipSize.MEDIUM)
    project.merge.pip_x = 1.0
    project.merge.pip_y = 1.0
    project.ui_state.timeline_offset_ms = 0
    project.ui_state.scoring_shot_expansion = {}
    project.ui_state.scoring_edit_shot_ids = []
    project.ui_state.waveform_shot_amplitudes = {}
    project.ui_state.timing_edit_shot_ids = []
    project.ui_state.review_text_box_expansion = {}
    project.ui_state.popup_bubble_expansion = {}
    project.ui_state.merge_source_expansion = {}
    project.ui_state.shotml_section_expansion = {}


def _run_analyze_video_audio(path: str, threshold: float, settings: ShotMLSettings):
    parameters = list(signature(analyze_video_audio).parameters.values())
    if (
        any(parameter.kind == Parameter.VAR_POSITIONAL for parameter in parameters)
        or len(parameters) >= 3
    ):
        return analyze_video_audio(path, threshold, settings)
    return analyze_video_audio(path, threshold)


def _shot_selection_context(
    project: Project,
    shot_id: str | None,
    *,
    fallback_mode: str = "time",
) -> _ShotSelectionContext | None:
    if shot_id is None:
        return None
    shots = sort_shots(project.analysis.shots)
    for index, shot in enumerate(shots):
        if shot.id == shot_id:
            return _ShotSelectionContext(
                shot_id=shot.id,
                time_ms=shot.time_ms,
                index=index,
                fallback_mode=fallback_mode,
            )
    return None


def _fallback_selected_shot_id(
    project: Project,
    context: _ShotSelectionContext | None,
) -> str | None:
    shots = sort_shots(project.analysis.shots)
    if not shots or context is None:
        return None
    if any(shot.id == context.shot_id for shot in shots):
        return context.shot_id
    if context.fallback_mode == "index":
        return shots[min(context.index, len(shots) - 1)].id
    return min(
        enumerate(shots),
        key=lambda item: (abs(item[1].time_ms - context.time_ms), item[0]),
    )[1].id


def _revalidate_timing_ui_state(
    project: Project,
    fallback_context: _ShotSelectionContext | None = None,
) -> bool:
    valid_shot_ids = {shot.id for shot in project.analysis.shots}
    ui_state = project.ui_state
    changed = False

    if ui_state.selected_shot_id and ui_state.selected_shot_id not in valid_shot_ids:
        next_selected_shot_id = _fallback_selected_shot_id(project, fallback_context)
        if ui_state.selected_shot_id != next_selected_shot_id:
            ui_state.selected_shot_id = next_selected_shot_id
            changed = True
    elif fallback_context and ui_state.selected_shot_id is None:
        next_selected_shot_id = _fallback_selected_shot_id(project, fallback_context)
        if next_selected_shot_id is not None:
            ui_state.selected_shot_id = next_selected_shot_id
            changed = True

    next_scoring_expansion = {
        shot_id: expanded
        for shot_id, expanded in ui_state.scoring_shot_expansion.items()
        if shot_id in valid_shot_ids
    }
    if ui_state.scoring_shot_expansion != next_scoring_expansion:
        ui_state.scoring_shot_expansion = next_scoring_expansion
        changed = True

    next_scoring_edit_shot_ids = [
        shot_id for shot_id in ui_state.scoring_edit_shot_ids if shot_id in valid_shot_ids
    ]
    if ui_state.scoring_edit_shot_ids != next_scoring_edit_shot_ids:
        ui_state.scoring_edit_shot_ids = next_scoring_edit_shot_ids
        changed = True

    next_waveform_amplitudes = {
        shot_id: amplitude
        for shot_id, amplitude in ui_state.waveform_shot_amplitudes.items()
        if shot_id in valid_shot_ids
    }
    if ui_state.waveform_shot_amplitudes != next_waveform_amplitudes:
        ui_state.waveform_shot_amplitudes = next_waveform_amplitudes
        changed = True

    next_timing_edit_shot_ids = [
        shot_id for shot_id in ui_state.timing_edit_shot_ids if shot_id in valid_shot_ids
    ]
    if ui_state.timing_edit_shot_ids != next_timing_edit_shot_ids:
        ui_state.timing_edit_shot_ids = next_timing_edit_shot_ids
        changed = True

    valid_text_box_ids = {box.id for box in project.overlay.text_boxes}
    next_review_text_box_expansion = {
        box_id: expanded
        for box_id, expanded in ui_state.review_text_box_expansion.items()
        if box_id in valid_text_box_ids
    }
    if ui_state.review_text_box_expansion != next_review_text_box_expansion:
        ui_state.review_text_box_expansion = next_review_text_box_expansion
        changed = True

    return changed


def _merge_reanalyzed_shots(
    previous_shots: list[ShotEvent],
    detected_shots: list[ShotEvent],
    settings: ShotMLSettings,
) -> list[ShotEvent]:
    merged_shots = [deepcopy(shot) for shot in detected_shots]
    for shot in merged_shots:
        shot.shotml_time_ms = shot.time_ms
        shot.shotml_confidence = shot.confidence
    manual_shots = [
        deepcopy(shot)
        for shot in previous_shots
        if shot.source == ShotSource.MANUAL and shot.user_added
    ]
    if not manual_shots:
        return sort_shots(merged_shots)

    overlap_window_ms = max(1, int(settings.min_shot_interval_ms or 0))
    for manual_shot in sort_shots(manual_shots):
        merged_shots = [
            shot
            for shot in merged_shots
            if abs(int(shot.time_ms) - int(manual_shot.time_ms)) > overlap_window_ms
        ]
        merged_shots.append(manual_shot)
    return sort_shots(merged_shots)


def _nearest_shot_id_by_time(shots: list[ShotEvent], target_time_ms: int) -> str | None:
    if not shots:
        return None
    return min(
        enumerate(shots),
        key=lambda item: (abs(int(item[1].time_ms) - int(target_time_ms)), item[0]),
    )[1].id


def _event_boundary_index(shots: list[ShotEvent], boundary_time_ms: int) -> int:
    for index, shot in enumerate(shots):
        if int(shot.time_ms) >= int(boundary_time_ms):
            return index
    return len(shots)


def _reanchor_timing_events_for_shots(
    events: list[TimingEvent],
    previous_shots: list[ShotEvent],
    next_shots: list[ShotEvent],
) -> list[TimingEvent]:
    if not events:
        return []
    previous_by_id = {shot.id: shot for shot in previous_shots}
    reanchored_events: list[TimingEvent] = []

    for event in events:
        if not event.after_shot_id and not event.before_shot_id:
            reanchored_events.append(deepcopy(event))
            continue

        previous_after = previous_by_id.get(event.after_shot_id or "")
        previous_before = previous_by_id.get(event.before_shot_id or "")
        rebased_event = deepcopy(event)

        if previous_after is not None and previous_before is not None:
            boundary_time_ms = previous_after.time_ms + max(
                1, (previous_before.time_ms - previous_after.time_ms) // 2
            )
            boundary_index = _event_boundary_index(next_shots, boundary_time_ms)
            rebased_event.after_shot_id = (
                next_shots[boundary_index - 1].id if boundary_index > 0 else None
            )
            rebased_event.before_shot_id = (
                next_shots[boundary_index].id if boundary_index < len(next_shots) else None
            )
        elif previous_after is not None:
            rebased_event.after_shot_id = _nearest_shot_id_by_time(
                next_shots, previous_after.time_ms
            )
            rebased_event.before_shot_id = None
        elif previous_before is not None:
            rebased_event.after_shot_id = None
            rebased_event.before_shot_id = _nearest_shot_id_by_time(
                next_shots, previous_before.time_ms
            )
        else:
            rebased_event.after_shot_id = None
            rebased_event.before_shot_id = None

        normalized_event = normalized_timing_event_for_shots(rebased_event, next_shots)
        if normalized_event is not None:
            reanchored_events.append(normalized_event)

    return reanchored_events


class ProjectController(QObject):
    project_changed = Signal()
    settings_changed = Signal()
    project_path_changed = Signal(str)
    status_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self.settings: AppSettings = load_settings()
        self.folder_settings: AppSettings | None = None
        self.folder_settings_error: str | None = None
        self.project = self._new_project_with_settings_defaults()
        self.project_path: Path | None = None
        self._practiscore_source_path: Path | None = None
        self._practiscore_source_name: str = ""
        self._practiscore_options: PractiScoreOptions | None = None
        self._practiscore_comparison_competitors: list[dict[str, object]] = []
        self._practiscore_session_payload = _default_practiscore_session_payload()
        self._practiscore_sync_payload = _default_practiscore_sync_payload()
        self.status_message = "Ready."
        self._saved_snapshot = project_to_dict(self.project)
        self._original_shot_state_by_id: dict[str, _OriginalShotState] = {}
        self._autosave_in_progress = False
        self._output_profiles: list[OutputProfile] = []
        self._output_profiles_cache_dirty = False
        self._remember_original_shots()
        self.project_changed.connect(self._autosave_project_if_needed)

    def new_project(self) -> None:
        self.folder_settings = None
        self.folder_settings_error = None
        self.project = self._new_project_with_settings_defaults()
        self.project_path = None
        self._clear_practiscore_source()
        self._practiscore_sync_payload = _default_practiscore_sync_payload()
        self._set_status("Ready.")
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self.project_changed.emit()

    def has_unsaved_changes(self) -> bool:
        return project_to_dict(self.project) != self._saved_snapshot

    def load_primary_video(self, path: str) -> None:
        _reset_media_dependent_state_for_primary_video(self.project)
        self.project.primary_video = probe_video(path)
        self._remember_original_shots()
        self._set_status("Loaded primary video.")
        self.project.touch()
        self.project_changed.emit()

    def load_secondary_video(self, path: str) -> None:
        self.add_merge_source(path)

    def analyze_primary(self) -> None:
        active_primary_path = _effective_primary_media_path(self.project)
        if not active_primary_path:
            return
        selection_context = _shot_selection_context(
            self.project,
            self.project.ui_state.selected_shot_id,
            fallback_mode="time",
        )
        previous_shots = [deepcopy(shot) for shot in self.project.analysis.shots]
        previous_events = [deepcopy(event) for event in self.project.analysis.events]
        self._set_status("Analyzing primary video for beep and shot detections...")
        result = _run_analyze_video_audio(
            active_primary_path,
            self.project.analysis.shotml_settings.detection_threshold,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.beep_time_ms_primary = result.beep_time_ms
        self.project.analysis.waveform_primary = result.waveform
        self.project.analysis.shots = _merge_reanalyzed_shots(
            previous_shots,
            result.shots,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.events = _reanchor_timing_events_for_shots(
            previous_events,
            previous_shots,
            self.project.analysis.shots,
        )
        self.project.analysis.detection_review_suggestions = [
            asdict(suggestion) for suggestion in result.review_suggestions
        ]
        self.project.analysis.detection_threshold = (
            self.project.analysis.shotml_settings.detection_threshold
        )
        self.project.analysis.timing_change_proposals = []
        self.project.analysis.last_shotml_run_summary = {
            "video_path": active_primary_path,
            "threshold": self.project.analysis.shotml_settings.detection_threshold,
            "sample_rate": result.sample_rate,
            "beep_time_ms": result.beep_time_ms,
            "shot_count": len(result.shots),
            "review_suggestion_count": len(result.review_suggestions),
        }
        ensure_default_shot_scores(self.project)
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project, selection_context)
        self._remember_original_shots()
        self.update_hit_factor()
        self._set_status(
            f"Primary analysis complete. Detected {len(result.shots)} shots"
            + ("" if result.beep_time_ms is None else f" and beep at {result.beep_time_ms} ms")
            + "."
        )
        self.project.touch()
        self.project_changed.emit()

    def analyze_secondary(self, source_id: str | None = None) -> None:
        source = (
            next(
                (
                    item
                    for item in self.project.merge_sources
                    if item.id == source_id and _source_supports_secondary_analysis(item)
                ),
                None,
            )
            if source_id
            else _first_analyzable_merge_source(self.project)
        )
        active_path = _effective_merge_source_media_path(source)
        if source is None or not active_path:
            _clear_secondary_analysis_state(self.project, preserve_sync_offset=True)
            self.project.secondary_video = None
            return
        self.project.secondary_video = _effective_merge_source_asset(source)
        self.project.analysis.analyzed_secondary_source_id = source.id
        self.project.analysis.secondary_analysis_status = "running"
        self.project.analysis.secondary_analysis_message = "Analyzing PiP sync source."
        running_entry = _secondary_analysis_entry_for_source(self.project, source.id, create=True)
        if running_entry is not None:
            running_entry.analysis_status = "running"
            running_entry.analysis_message = "Analyzing PiP sync source."
        self._set_status("Analyzing secondary video and computing sync offset...")
        result = _run_analyze_video_audio(
            active_path,
            self.project.analysis.shotml_settings.detection_threshold,
            self.project.analysis.shotml_settings,
        )
        sync_offset_ms = compute_sync_offset(
            self.project.analysis.beep_time_ms_primary,
            result.beep_time_ms,
        )
        entry = _secondary_analysis_entry_for_source(self.project, source.id, create=True)
        if entry is not None:
            entry.beep_time_ms = result.beep_time_ms
            entry.waveform = list(result.waveform)
            entry.sync_offset_ms = int(sync_offset_ms)
            entry.sync_source = "auto"
            entry.analysis_status = "ready" if result.beep_time_ms is not None else "no_beep"
            entry.analysis_message = (
                "Secondary beep detected."
                if result.beep_time_ms is not None
                else "No secondary beep detected. Manual sync is still available."
            )
        self.project.analysis.beep_time_ms_secondary = result.beep_time_ms
        self.project.analysis.waveform_secondary = list(result.waveform)
        self.project.analysis.sync_offset_ms = int(sync_offset_ms)
        self.project.analysis.secondary_sync_source = "auto"
        self.project.analysis.secondary_analysis_status = (
            "ready" if result.beep_time_ms is not None else "no_beep"
        )
        self.project.analysis.secondary_analysis_message = (
            "Secondary beep detected."
            if result.beep_time_ms is not None
            else "No secondary beep detected. Manual sync is still available."
        )
        source.sync_offset_ms = self.project.analysis.sync_offset_ms
        _refresh_secondary_analysis_projection(self.project, preferred_source_id=source.id)
        self._set_status(
            "Secondary analysis complete."
            + (
                ""
                if result.beep_time_ms is None
                else f" Sync offset: {self.project.analysis.sync_offset_ms} ms."
            )
        )
        self.project.touch()
        self.project_changed.emit()

    def effective_merge_source_media_path(self, source_id: str | None = None) -> str:
        source = (
            next((item for item in self.project.merge_sources if item.id == source_id), None)
            if source_id
            else _first_analyzable_merge_source(self.project)
        )
        return _effective_merge_source_media_path(source)

    def effective_primary_media_path(self) -> str:
        return _effective_primary_media_path(self.project)

    def ingest_primary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing primary video...")
        self.load_primary_video(self._stage_project_input_path(path, source_name=source_name))
        self.analyze_primary()

    def ingest_secondary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing secondary video...")
        self.load_secondary_video(self._stage_project_input_path(path, source_name=source_name))

    def set_project_details(
        self,
        name: str | None = None,
        description: str | None = None,
        output_root: str | None = None,
    ) -> None:
        changed = False
        if name is not None:
            next_name = name.strip() or "Untitled Project"
            if self.project.name != next_name:
                self.project.name = next_name
                changed = True
        if description is not None:
            next_description = str(description)
            if self.project.description != next_description:
                self.project.description = next_description
                changed = True
        if output_root is not None:
            next_output_root = str(output_root).strip()
            if self.project.output_root != next_output_root:
                self.project.output_root = next_output_root
                changed = True
        if changed:
            self.project.touch()
            self.project_changed.emit()
            self._set_status("Updated project details.")
        else:
            self._set_status("Project details unchanged.")

    def set_practiscore_context(
        self,
        match_type: str | None = None,
        stage_number: int | None = None,
        competitor_name: str | None = None,
        competitor_place: int | None = None,
        classification: str | None = None,
        division: str | None = None,
    ) -> None:
        scoring = self.project.scoring
        changed = False
        if match_type is not None:
            clean_match_type = (
                "" if not str(match_type).strip() else normalize_match_type(str(match_type))
            )
            if scoring.match_type != clean_match_type:
                scoring.match_type = clean_match_type
                changed = True
            if clean_match_type:
                target_ruleset = default_ruleset_for_match_type(clean_match_type)
                if scoring.ruleset != target_ruleset:
                    changed = True
                apply_scoring_preset(self.project, target_ruleset)
        if stage_number is not None:
            next_stage_number = None if int(stage_number) <= 0 else max(1, int(stage_number))
            if scoring.stage_number != next_stage_number:
                scoring.stage_number = next_stage_number
                changed = True
        if competitor_name is not None:
            next_competitor_name = str(competitor_name).strip()
            if scoring.competitor_name != next_competitor_name:
                scoring.competitor_name = next_competitor_name
                changed = True
        if competitor_place is not None:
            next_competitor_place = None if int(competitor_place) <= 0 else int(competitor_place)
            if scoring.competitor_place != next_competitor_place:
                scoring.competitor_place = next_competitor_place
                changed = True
        if classification is not None:
            next_classification = str(classification).strip()
            if scoring.classification != next_classification:
                scoring.classification = next_classification
                changed = True
        if division is not None:
            next_division = str(division).strip()
            if scoring.division != next_division:
                scoring.division = next_division
                changed = True
        if changed:
            if self._can_reimport_practiscore_source():
                self._import_practiscore_source_for_all_stages(
                    str(self._practiscore_source_path),
                    self._practiscore_source_name,
                )
                return
            scoring.imported_stage = None
            scoring.penalties = 0.0
            scoring.penalty_counts = {}
            self.update_hit_factor()
            self._set_status("Updated PractiScore import settings.")
        else:
            self._set_status("PractiScore import settings unchanged.")
        self.project.touch()
        self.project_changed.emit()

    def import_practiscore_file(self, path: str, source_name: str | None = None) -> None:
        path = self._stage_practiscore_source_path(path, source_name=source_name)
        self._set_practiscore_source(path, source_name)
        self.project.excluded_imported_stage_numbers = []
        self._rebuild_stages_from_practiscore_source(path, source_name)
        self._import_practiscore_source_for_all_stages(path, source_name)

    def _rebuild_stages_from_practiscore_source(
        self, path: str, source_name: str | None = None
    ) -> None:
        options = describe_practiscore_file(path, source_name=source_name)
        excluded_stage_numbers = set(self.project.excluded_imported_stage_numbers)
        stage_numbers = [
            stage_number
            for stage_number in (options.stage_numbers or [])
            if stage_number not in excluded_stage_numbers
        ]
        if not stage_numbers:
            return

        current_match_type = self.project.scoring.match_type
        current_stage_number = self.project.scoring.stage_number
        current_competitor_name = self.project.scoring.competitor_name
        current_competitor_place = self.project.scoring.competitor_place
        current_classification = self.project.scoring.classification
        current_division = self.project.scoring.division
        current_source_path = self.project.scoring.practiscore_source_path
        current_source_name = self.project.scoring.practiscore_source_name
        seed_project_state = not bool(self.project.stages)
        seeded_primary = deepcopy(self.project.primary_video)
        seeded_merge_sources = list(self.project.merge_sources)
        seeded_analysis = deepcopy(self.project.analysis)
        seeded_scoring = deepcopy(self.project.scoring)
        seeded_overlay = deepcopy(self.project.overlay)
        seeded_popups = list(self.project.popups)
        seeded_popup_template = deepcopy(self.project.popup_template)
        seeded_merge = deepcopy(self.project.merge)
        seeded_export = deepcopy(self.project.export)
        self._sync_project_to_active_stage()

        existing_by_number = {
            stage.imported_stage_number: stage
            for stage in self.project.stages
            if stage.imported_stage_number is not None
        }
        new_stages: list[ProjectStage] = []
        for order_index, stage_number in enumerate(stage_numbers, start=1):
            stage_name = f"Stage {stage_number}"
            stage = existing_by_number.get(stage_number)
            if stage is None:
                stage = ProjectStage(
                    label=stage_name,
                    order_index=order_index,
                    imported_stage_number=stage_number,
                    imported_stage_name=stage_name,
                    analysis=AnalysisState(
                        detection_threshold=seeded_analysis.detection_threshold,
                        shotml_settings=deepcopy(seeded_analysis.shotml_settings),
                    ),
                    scoring=deepcopy(seeded_scoring),
                    overlay=deepcopy(seeded_overlay),
                    popups=deepcopy(seeded_popups),
                    popup_template=deepcopy(seeded_popup_template),
                    merge=deepcopy(seeded_merge),
                    export=deepcopy(seeded_export),
                )
                stage.scoring.stage_number = stage_number
                stage.scoring.imported_stage = None
                stage.scoring.penalties = 0.0
                stage.scoring.penalty_counts = {}
                stage.scoring.hit_factor = None
                stage.export.output_path = None
                stage.export.last_log = ""
                stage.export.last_error = None
            else:
                stage.order_index = order_index
                stage.imported_stage_number = stage_number
                if not stage.imported_stage_name:
                    stage.imported_stage_name = stage_name
                if not stage.label or re.fullmatch(r"Stage\s+\d+", stage.label):
                    stage.label = stage.imported_stage_name or stage_name
            new_stages.append(stage)

        stage_ids = {stage.id for stage in new_stages}
        self.project.stages = new_stages
        self.project.queue = [entry for entry in self.project.queue if entry.stage_id in stage_ids]
        self.project.practiscore_source_file = path

        target_stage_number = self.project.scoring.stage_number
        active_stage = next(
            (
                stage
                for stage in self.project.stages
                if stage.imported_stage_number == target_stage_number
            ),
            None,
        )
        if active_stage is None:
            active_stage = self.project.stages[0]
        self.project.active_stage_id = active_stage.id
        if seed_project_state:
            active_stage.primary_media = seeded_primary
            active_stage.added_media = seeded_merge_sources
            active_stage.analysis = seeded_analysis
            active_stage.scoring = seeded_scoring
            active_stage.overlay = seeded_overlay
            active_stage.popups = seeded_popups
            active_stage.popup_template = seeded_popup_template
            active_stage.merge = seeded_merge
            active_stage.export = seeded_export
        self._sync_active_stage_to_project()
        if current_match_type:
            self.project.scoring.match_type = current_match_type
        if current_stage_number is not None:
            self.project.scoring.stage_number = current_stage_number
        if current_competitor_name:
            self.project.scoring.competitor_name = current_competitor_name
        if current_competitor_place is not None:
            self.project.scoring.competitor_place = current_competitor_place
        if current_classification:
            self.project.scoring.classification = current_classification
        if current_division:
            self.project.scoring.division = current_division
        if current_source_path:
            self.project.scoring.practiscore_source_path = current_source_path
        if current_source_name:
            self.project.scoring.practiscore_source_name = current_source_name

    def _practiscore_options_browser_payload(self) -> dict[str, object]:
        options = self._practiscore_options
        competitors = (
            []
            if options is None
            else [
                {
                    "name": option.name,
                    "place": option.place,
                    "division": option.division,
                    "classification": option.classification,
                    "power_factor": option.power_factor,
                }
                for option in options.competitors
            ]
        )
        return {
            "has_source": self._practiscore_source_path is not None,
            "source_name": self._practiscore_source_name,
            "detected_match_type": "" if options is None else options.match_type,
            "stage_numbers": [] if options is None else list(options.stage_numbers),
            "competitors": competitors,
        }

    def practiscore_browser_state(self) -> dict[str, object]:
        payload = self._practiscore_options_browser_payload()
        payload["_session_payload"] = deepcopy(self._practiscore_session_payload)
        payload["_sync_payload"] = deepcopy(self._practiscore_sync_payload)
        payload["comparison_competitors"] = deepcopy(self._practiscore_comparison_competitors)
        return payload

    def _set_practiscore_session_payload(self, payload: dict[str, object]) -> None:
        self._practiscore_session_payload = _practiscore_session_payload_from_status(payload)

    def _set_practiscore_sync_state(
        self,
        state: str,
        message: str,
        *,
        matches: list[RemotePractiScoreMatch] | list[dict[str, object]] | None = None,
        selected_remote_id: str | None | object = _PRACTISCORE_SYNC_UNSET,
        error_category: str = "",
        details: dict[str, object] | None = None,
    ) -> None:
        next_matches = (
            _serialize_practiscore_remote_matches(matches)
            if matches is not None
            else _serialize_practiscore_remote_matches(
                self._practiscore_sync_payload.get("matches")
            )
        )
        next_selected_remote_id = (
            self._practiscore_sync_payload.get("selected_remote_id")
            if selected_remote_id is _PRACTISCORE_SYNC_UNSET
            else (None if selected_remote_id in {None, ""} else str(selected_remote_id))
        )
        self._practiscore_sync_payload = {
            "state": state if state in _VALID_PRACTISCORE_SYNC_STATES else "error",
            "message": str(message),
            "matches": next_matches,
            "selected_remote_id": next_selected_remote_id,
            "error_category": str(error_category or ""),
            "details": deepcopy(details or {}),
        }

    def _practiscore_route_payload(self) -> dict[str, object]:
        return {
            "practiscore_session": deepcopy(self._practiscore_session_payload),
            "practiscore_sync": deepcopy(self._practiscore_sync_payload),
            "practiscore_options": self._practiscore_options_browser_payload(),
            "matches": _serialize_practiscore_remote_matches(
                self._practiscore_sync_payload.get("matches")
            ),
        }

    def list_practiscore_matches(self, practiscore_session: object) -> dict[str, object]:
        session_payload = _practiscore_session_payload_from_manager(practiscore_session)
        self._set_practiscore_session_payload(session_payload)
        if self._practiscore_session_payload.get("state") != "authenticated_ready":
            message = str(
                self._practiscore_session_payload.get("message")
                or "PractiScore session is not ready."
            )
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                matches=[],
                error_category=EXPIRED_AUTHENTICATION_ERROR,
                details={"route": "/api/practiscore/matches"},
            )
            return self._practiscore_route_payload()

        self._set_status("Discovering remote PractiScore matches...")
        self._set_practiscore_sync_state(
            "discovering_matches",
            "Discovering remote PractiScore matches...",
            matches=[],
        )
        try:
            browser_context = practiscore_session.require_authenticated_browser()
            matches = discover_remote_matches(browser_context)
        except PractiScoreSyncError as exc:
            self._set_status(str(exc))
            self._set_practiscore_sync_state(
                "error",
                str(exc),
                matches=[],
                error_category=exc.category,
                details=exc.details,
            )
            self._set_practiscore_session_payload(
                _practiscore_session_payload_from_manager(practiscore_session)
            )
            return self._practiscore_route_payload()
        except Exception as exc:  # noqa: BLE001
            session_payload = _practiscore_session_payload_from_manager(practiscore_session)
            self._set_practiscore_session_payload(session_payload)
            category = (
                EXPIRED_AUTHENTICATION_ERROR
                if self._practiscore_session_payload.get("state") != "authenticated_ready"
                else _practiscore_error_category_from_exception(exc)
            )
            message = str(exc) or "Unable to list remote PractiScore matches."
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                matches=[],
                error_category=category,
                details={"route": "/api/practiscore/matches"},
            )
            return self._practiscore_route_payload()

        match_payloads = _serialize_practiscore_remote_matches(matches)
        previous_selected_remote_id = self._practiscore_sync_payload.get("selected_remote_id")
        selected_remote_id = (
            previous_selected_remote_id
            if any(
                payload.get("remote_id") == previous_selected_remote_id
                for payload in match_payloads
            )
            else None
        )
        message = (
            "No remote PractiScore matches found."
            if not match_payloads
            else f"Found {len(match_payloads)} remote PractiScore match(es)."
        )
        self._set_status(message)
        self._set_practiscore_sync_state(
            "match_list_ready",
            message,
            matches=match_payloads,
            selected_remote_id=selected_remote_id,
            details={"match_count": len(match_payloads)},
        )
        self._set_practiscore_session_payload(
            _practiscore_session_payload_from_manager(practiscore_session)
        )
        return self._practiscore_route_payload()

    def start_practiscore_sync(
        self, payload: dict[str, object], practiscore_session: object
    ) -> dict[str, object]:
        remote_id = str(payload.get("remote_id") or "").strip()
        if not remote_id:
            message = "A remote PractiScore match must be selected before import."
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                error_category=MALFORMED_REMOTE_RESPONSE_ERROR,
                details={"route": "/api/practiscore/sync/start"},
            )
            return self._practiscore_route_payload()

        session_payload = _practiscore_session_payload_from_manager(practiscore_session)
        self._set_practiscore_session_payload(session_payload)
        if self._practiscore_session_payload.get("state") != "authenticated_ready":
            message = str(
                self._practiscore_session_payload.get("message")
                or "PractiScore session is not ready."
            )
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                selected_remote_id=remote_id,
                error_category=EXPIRED_AUTHENTICATION_ERROR,
                details={"route": "/api/practiscore/sync/start", "remote_id": remote_id},
            )
            return self._practiscore_route_payload()

        existing_matches = _practiscore_remote_match_objects(
            self._practiscore_sync_payload.get("matches")
        )
        self._set_status("Importing selected remote PractiScore match...")
        self._set_practiscore_sync_state(
            "importing_selected_match",
            "Importing selected remote PractiScore match...",
            matches=existing_matches,
            selected_remote_id=remote_id,
        )
        try:
            browser_context = practiscore_session.require_authenticated_browser()
            app_dir = getattr(getattr(practiscore_session, "profile_paths", None), "app_dir", None)
            artifacts = download_remote_match_artifacts(
                browser_context,
                remote_id,
                practiscore_sync_audit_root(app_dir),
                match_catalog=existing_matches,
            )
            normalize_downloaded_practiscore_artifact(
                artifacts.source_artifact_path,
                source_name=artifacts.source_name,
                match_type=self.project.scoring.match_type or None,
                stage_number=self.project.scoring.stage_number,
                competitor_name=self.project.scoring.competitor_name or None,
                competitor_place=self.project.scoring.competitor_place,
            )
            self.import_practiscore_file(
                str(artifacts.source_artifact_path), source_name=artifacts.source_name
            )
        except PractiScoreSyncError as exc:
            self._set_status(str(exc))
            self._set_practiscore_sync_state(
                "error",
                str(exc),
                matches=existing_matches,
                selected_remote_id=remote_id,
                error_category=exc.category,
                details={**exc.details, "remote_id": remote_id},
            )
            self._set_practiscore_session_payload(
                _practiscore_session_payload_from_manager(practiscore_session)
            )
            return self._practiscore_route_payload()
        except ValueError as exc:
            message = str(exc) or "Unable to normalize the downloaded PractiScore artifact."
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                matches=existing_matches,
                selected_remote_id=remote_id,
                error_category=NORMALIZATION_IMPORT_FAILURE_ERROR,
                details={"remote_id": remote_id},
            )
            self._set_practiscore_session_payload(
                _practiscore_session_payload_from_manager(practiscore_session)
            )
            return self._practiscore_route_payload()
        except Exception as exc:  # noqa: BLE001
            session_payload = _practiscore_session_payload_from_manager(practiscore_session)
            self._set_practiscore_session_payload(session_payload)
            category = (
                EXPIRED_AUTHENTICATION_ERROR
                if self._practiscore_session_payload.get("state") != "authenticated_ready"
                else _practiscore_error_category_from_exception(exc)
            )
            message = str(exc) or "Unable to import the selected remote PractiScore match."
            self._set_status(message)
            self._set_practiscore_sync_state(
                "error",
                message,
                matches=existing_matches,
                selected_remote_id=remote_id,
                error_category=category,
                details={"remote_id": remote_id},
            )
            return self._practiscore_route_payload()

        imported_stage = self.project.scoring.imported_stage
        updated_matches = _serialize_practiscore_remote_matches(existing_matches)
        if not any(item.get("remote_id") == artifacts.match.remote_id for item in updated_matches):
            updated_matches.append(artifacts.match.to_dict())
        message = f"Imported remote PractiScore match {artifacts.match.label}."
        self._set_practiscore_sync_state(
            "success",
            message,
            matches=updated_matches,
            selected_remote_id=remote_id,
            details={
                "remote_id": remote_id,
                "label": artifacts.match.label,
                "cache_dir": str(artifacts.cache_dir),
                "source_artifact_path": str(artifacts.source_artifact_path),
                "html_path": str(artifacts.html_path),
                "summary_path": str(artifacts.summary_path),
                "staged_source_path": ""
                if self._practiscore_source_path is None
                else str(self._practiscore_source_path),
                "imported_stage_number": None
                if imported_stage is None
                else imported_stage.stage_number,
            },
        )
        self._set_practiscore_session_payload(
            _practiscore_session_payload_from_manager(practiscore_session)
        )
        return self._practiscore_route_payload()

    def _clear_practiscore_source(self) -> None:
        self._practiscore_source_path = None
        self._practiscore_source_name = ""
        self._practiscore_options = None
        self._practiscore_comparison_competitors = []
        self.project.scoring.practiscore_source_path = ""
        self.project.scoring.practiscore_source_name = ""

    def _set_practiscore_source(self, path: str, source_name: str | None = None) -> None:
        resolved_path = Path(path)
        display_name = source_name or resolved_path.name
        options = describe_practiscore_file(resolved_path, source_name=display_name)
        self._practiscore_source_path = resolved_path
        self._practiscore_source_name = display_name
        self._practiscore_options = options
        self.project.scoring.practiscore_source_path = str(resolved_path)
        self.project.scoring.practiscore_source_name = display_name

    def _practiscore_import_context_kwargs(self) -> dict[str, object]:
        scoring = self.project.scoring
        return {
            "match_type": scoring.match_type or None,
            "stage_number": scoring.stage_number,
            "competitor_name": scoring.competitor_name or None,
            "competitor_place": scoring.competitor_place,
            "classification": scoring.classification or None,
            "division": scoring.division or None,
        }

    def _project_practiscore_candidates(self) -> list[Path]:
        if self.project_path is None:
            return []
        practiscore_dir = self.project_path / PRACTISCORE_DIRNAME
        if not practiscore_dir.is_dir():
            return []
        candidates: list[Path] = []
        for path in practiscore_dir.iterdir():
            if not path.is_file() or path.suffix.lower() not in _PRACTISCORE_FILE_SUFFIXES:
                continue
            candidates.append(path.resolve())
        candidates.sort(key=lambda item: (item.stat().st_mtime_ns, item.name.lower()), reverse=True)
        return candidates

    def settings_template_names(self) -> list[str]:
        names = [name for name in self.settings.settings_templates if str(name).strip()]
        if not names:
            names = [self.settings.active_template_name or "Default"]
        if self.settings.active_template_name not in names:
            names.insert(0, self.settings.active_template_name)
        return names

    def _settings_template_snapshot(self, template_name: str | None = None) -> dict[str, object]:
        name = str(template_name or self.settings.active_template_name or "Default")
        template = self.settings.settings_templates.get(name)
        if isinstance(template, dict) and template:
            return deepcopy(template)
        return self.settings.template_snapshot()

    def _apply_settings_template_snapshot(
        self, template_name: str, snapshot: dict[str, object]
    ) -> None:
        next_settings = AppSettings.from_dict(
            {**snapshot, "recent_projects": self.settings.recent_projects}
        )
        next_settings.active_template_name = template_name
        next_settings.settings_templates = deepcopy(self.settings.settings_templates)
        next_settings.settings_templates[template_name] = deepcopy(snapshot)
        next_settings.recent_projects = self.settings.recent_projects
        self.settings = next_settings

    def _sync_active_settings_template(self) -> None:
        templates = deepcopy(self.settings.settings_templates)
        templates[self.settings.active_template_name] = self.settings.template_snapshot()
        self.settings.settings_templates = templates

    def _save_settings_and_emit(self) -> None:
        self._sync_active_settings_template()
        save_settings(self.settings)
        self.settings_changed.emit()

    def _template_snapshot_from_current_project(
        self, snapshot: dict[str, object], section: str | None = None
    ) -> dict[str, object]:
        project_payload = project_to_dict(self.project)
        current_settings = self.settings.config_dict()
        next_snapshot = deepcopy(snapshot)
        section_name = (section or "all").strip().lower()

        def update_project_defaults() -> None:
            scoring = project_payload.get("scoring", {})
            if not isinstance(scoring, dict):
                return
            match_type = str(
                scoring.get("match_type") or current_settings.get("default_match_type") or "uspsa"
            )
            try:
                default_match_type = normalize_match_type(match_type)
            except ValueError:
                default_match_type = str(current_settings.get("default_match_type") or "uspsa")
            stage_number = scoring.get("stage_number")
            competitor_name = str(scoring.get("competitor_name") or "")
            competitor_place = scoring.get("competitor_place")
            next_snapshot.update(
                {
                    "default_match_type": default_match_type,
                    "default_stage_number": None
                    if stage_number in {None, ""}
                    else int(stage_number),
                    "default_competitor_name": competitor_name,
                    "default_competitor_place": None
                    if competitor_place in {None, ""}
                    else int(competitor_place),
                }
            )

        def update_pip_defaults() -> None:
            merge = project_payload.get("merge", {})
            if not isinstance(merge, dict):
                return
            next_snapshot.update(
                {
                    "merge_layout": str(
                        merge.get("layout")
                        or current_settings.get("merge_layout")
                        or MergeLayout.SIDE_BY_SIDE.value
                    ),
                    "pip_size": str(
                        merge.get("pip_size")
                        or current_settings.get("pip_size")
                        or PipSize.MEDIUM.value
                    ),
                    "merge_pip_x": float(
                        merge.get("pip_x", current_settings.get("merge_pip_x", 1.0))
                    ),
                    "merge_pip_y": float(
                        merge.get("pip_y", current_settings.get("merge_pip_y", 1.0))
                    ),
                }
            )

        def update_marker_defaults() -> None:
            popup_template = project_payload.get("popup_template", {})
            if isinstance(popup_template, dict):
                next_snapshot["marker_template"] = deepcopy(popup_template)

        def update_overlay_defaults() -> None:
            overlay = project_payload.get("overlay", {})
            if not isinstance(overlay, dict):
                return
            mapping = {
                "position": "overlay_position",
                "badge_size": "badge_size",
                "custom_box_background_color": "overlay_custom_box_background_color",
                "custom_box_text_color": "overlay_custom_box_text_color",
                "custom_box_opacity": "overlay_custom_box_opacity",
                "timer_badge": "timer_badge",
                "shot_badge": "shot_badge",
                "current_shot_badge": "current_shot_badge",
                "hit_factor_badge": "hit_factor_badge",
            }
            for source_key, target_key in mapping.items():
                if source_key in overlay:
                    next_snapshot[target_key] = deepcopy(overlay[source_key])

        def update_review_defaults() -> None:
            overlay = project_payload.get("overlay", {})
            if isinstance(overlay, dict):
                next_snapshot["review_text_boxes"] = deepcopy(overlay.get("text_boxes", []))

        def update_export_defaults() -> None:
            export = project_payload.get("export", {})
            if not isinstance(export, dict):
                return
            for key in (
                "quality",
                "preset",
                "frame_rate",
                "video_codec",
                "audio_codec",
                "color_space",
                "two_pass",
                "ffmpeg_preset",
            ):
                if key in export:
                    next_snapshot[f"export_{key}"] = deepcopy(export[key])

        if section_name in {"all", "project"}:
            update_project_defaults()
        if section_name in {"all", "pip"}:
            update_pip_defaults()
        if section_name in {"all", "markers"}:
            update_marker_defaults()
        if section_name in {"all", "overlay"}:
            update_overlay_defaults()
        if section_name in {"all", "review"}:
            update_review_defaults()
        if section_name in {"all", "export"}:
            update_export_defaults()
        return next_snapshot

    def select_settings_template(self, template_name: str) -> None:
        template_name = str(template_name or "").strip()
        if not template_name:
            raise ValueError("Template name is required.")
        snapshot = self._settings_template_snapshot(template_name)
        self._apply_settings_template_snapshot(template_name, snapshot)
        self._save_settings_and_emit()
        self._set_status(f"Selected settings template {template_name}.")

    def save_settings_template(self, template_name: str, *, section: str | None = None) -> None:
        template_name = (
            str(template_name or "").strip() or self.settings.active_template_name or "Default"
        )
        snapshot = self._settings_template_snapshot(template_name)
        snapshot = self._template_snapshot_from_current_project(snapshot, section=section)
        self._apply_settings_template_snapshot(template_name, snapshot)
        self._save_settings_and_emit()
        if section:
            self._set_status(f"Saved {section} defaults to template {template_name}.")
        else:
            self._set_status(f"Saved current project defaults to template {template_name}.")

    def duplicate_settings_template(self, template_name: str, duplicate_name: str) -> None:
        source_name = str(template_name or "").strip() or self.settings.active_template_name
        duplicate_name = str(duplicate_name or "").strip()
        if not duplicate_name:
            raise ValueError("Duplicate template name is required.")
        snapshot = self._settings_template_snapshot(source_name)
        self._apply_settings_template_snapshot(duplicate_name, snapshot)
        self._save_settings_and_emit()
        self._set_status(f"Duplicated settings template {source_name} to {duplicate_name}.")

    def delete_settings_template(self, template_name: str) -> None:
        template_name = str(template_name or "").strip()
        if not template_name:
            return
        templates = deepcopy(self.settings.settings_templates)
        if template_name not in templates:
            return
        if len(templates) <= 1:
            templates = {"Default": self.settings.template_snapshot()}
            template_name = "Default"
        else:
            templates.pop(template_name, None)
        next_template_name = (
            self.settings.active_template_name
            if template_name != self.settings.active_template_name
            else next(iter(templates.keys()))
        )
        snapshot = templates.get(next_template_name) or next(iter(templates.values()))
        self._apply_settings_template_snapshot(next_template_name, snapshot)
        self.settings.settings_templates = templates
        self._save_settings_and_emit()
        self._set_status(f"Deleted settings template {template_name}.")

    def _recover_practiscore_path_from_project_folder(
        self,
        stored_path: str,
        stored_name: str | None,
    ) -> tuple[Path | None, str | None, bool]:
        candidates = self._project_practiscore_candidates()
        if not candidates:
            return None, stored_name, False

        preferred_names = [
            stored_name or "",
            Path(stored_path).name if stored_path else "",
        ]
        imported_stage = self.project.scoring.imported_stage
        if imported_stage is not None:
            preferred_names.extend(
                [
                    imported_stage.source_name or "",
                    Path(imported_stage.source_path).name if imported_stage.source_path else "",
                ]
            )

        for preferred_name in preferred_names:
            clean_name = preferred_name.strip()
            if not clean_name:
                continue
            for candidate in candidates:
                if candidate.name == clean_name:
                    return candidate, clean_name, True

        if stored_path or imported_stage is not None or len(candidates) != 1:
            return None, stored_name, False
        return candidates[0], stored_name or candidates[0].name, True

    def _restore_practiscore_source_from_project(self, *, emit_change: bool = True) -> bool:
        stored_path = self.project.scoring.practiscore_source_path.strip()
        stored_name = self.project.scoring.practiscore_source_name.strip() or None
        resolved_path = Path(stored_path) if stored_path else None
        recovered_from_folder = False

        if resolved_path is None or not resolved_path.exists():
            recovered_path, recovered_name, recovered_from_folder = (
                self._recover_practiscore_path_from_project_folder(
                    stored_path,
                    stored_name,
                )
            )
            if recovered_path is not None:
                resolved_path = recovered_path
                stored_name = recovered_name or resolved_path.name

        if resolved_path is None:
            self._clear_practiscore_source()
            return False

        display_name = stored_name or resolved_path.name
        changed = False
        if self.project.scoring.practiscore_source_path != str(resolved_path):
            self.project.scoring.practiscore_source_path = str(resolved_path)
            changed = True
        if self.project.scoring.practiscore_source_name != display_name:
            self.project.scoring.practiscore_source_name = display_name
            changed = True
        if self.project.scoring.imported_stage is not None:
            if self.project.scoring.imported_stage.source_path != str(resolved_path):
                self.project.scoring.imported_stage.source_path = str(resolved_path)
                changed = True
            if self.project.scoring.imported_stage.source_name != display_name:
                self.project.scoring.imported_stage.source_name = display_name
                changed = True

        try:
            options = describe_practiscore_file(resolved_path, source_name=display_name)
        except (OSError, ValueError):
            self._practiscore_source_path = resolved_path
            self._practiscore_source_name = display_name
            self._practiscore_options = None
            return changed or recovered_from_folder

        self._practiscore_source_path = resolved_path
        self._practiscore_source_name = display_name
        self._practiscore_options = options
        summary_metrics_changed = False
        for stage in self.project.stages:
            imported_box = next(
                (box for box in stage.overlay.text_boxes if box.source == "imported_summary"),
                None,
            )
            if imported_box is None and stage.scoring.imported_stage is not None:
                boxes = list(overlay_text_boxes_for_render(stage.overlay))
                boxes.append(
                    OverlayTextBox(
                        enabled=True,
                        lock_to_stack=False,
                        source="imported_summary",
                        quadrant="above_final",
                        background_color=stage.overlay.custom_box_background_color,
                        text_color=stage.overlay.custom_box_text_color,
                        opacity=stage.overlay.custom_box_opacity,
                        style_type=stage.overlay.style_type,
                        font_family=stage.overlay.font_family,
                        font_size=stage.overlay.font_size,
                        font_bold=stage.overlay.font_bold,
                        font_italic=stage.overlay.font_italic,
                        summary_metric_ids=list(_DEFAULT_SUMMARY_METRIC_IDS),
                    )
                )
                stage.overlay.text_boxes = boxes
                sync_overlay_legacy_custom_box_fields(stage.overlay)
                summary_metrics_changed = True
            elif imported_box is not None and not imported_box.summary_metric_ids:
                imported_box.summary_metric_ids = list(_DEFAULT_SUMMARY_METRIC_IDS)
                summary_metrics_changed = True
        if summary_metrics_changed:
            self._sync_active_stage_to_project()
            changed = True
        expected_stage_numbers = set(options.stage_numbers or [])
        actual_stage_numbers = {
            stage.imported_stage_number
            for stage in self.project.stages
            if stage.imported_stage_number is not None
        }
        imported_stage_structure_needs_refresh = (
            bool(expected_stage_numbers) and actual_stage_numbers != expected_stage_numbers
        )
        imported_stages_need_refresh = any(
            stage.imported_stage_number is not None
            and (
                stage.scoring.imported_stage is None
                or stage.scoring.imported_stage.stage_number != stage.imported_stage_number
                or stage.scoring.match_type != options.match_type
            )
            for stage in self.project.stages
        )
        if (
            self.project.scoring.imported_stage is None
            or self.project.scoring.match_type != options.match_type
            or imported_stage_structure_needs_refresh
            or imported_stages_need_refresh
        ):
            try:
                self.project.scoring.match_type = options.match_type
                if imported_stage_structure_needs_refresh:
                    self._rebuild_stages_from_practiscore_source(str(resolved_path), display_name)
                self._import_practiscore_source_for_all_stages(
                    str(resolved_path), display_name, emit_change=emit_change
                )
                return True
            except ValueError:
                return changed or recovered_from_folder
        try:
            normalized = normalize_downloaded_practiscore_artifact(
                resolved_path,
                source_name=display_name,
                **self._practiscore_import_context_kwargs(),
            )
            self._set_practiscore_comparison_competitors(
                normalized.stage_import.comparison_competitors
            )
        except ValueError:
            self._practiscore_comparison_competitors = []
        return changed or recovered_from_folder

    def _project_input_candidates(self) -> list[tuple[Path, VideoAsset]]:
        if self.project_path is None:
            return []

        candidates: list[tuple[Path, VideoAsset]] = []
        seen_paths: set[Path] = set()
        candidate_dirs = [self.project_path]
        input_dir = self.project_path / INPUT_DIRNAME
        if input_dir.is_dir():
            candidate_dirs.insert(0, input_dir)

        for directory in candidate_dirs:
            for path in directory.iterdir():
                if not path.is_file():
                    continue
                resolved_path = path.resolve()
                if resolved_path in seen_paths:
                    continue
                seen_paths.add(resolved_path)
                try:
                    candidates.append((resolved_path, probe_video(resolved_path)))
                except (MediaError, OSError, ValueError):
                    continue
        candidates.sort(key=lambda item: item[0].name.lower())
        return candidates

    def _recover_media_asset_from_project_folder(
        self,
        asset: VideoAsset,
        candidates: list[tuple[Path, VideoAsset]],
        used_paths: set[Path],
    ) -> VideoAsset | None:
        stored_path = asset.path.strip()
        if not stored_path:
            return None

        resolved_path = Path(stored_path)
        if resolved_path.exists():
            used_paths.add(resolved_path.resolve())
            return None

        scored_candidates: list[tuple[int, Path, VideoAsset]] = []
        for candidate_path, candidate_asset in candidates:
            if candidate_path in used_paths:
                continue
            score = _project_media_recovery_score(
                stored_path, asset, candidate_path, candidate_asset
            )
            if score <= 0:
                continue
            scored_candidates.append((score, candidate_path, candidate_asset))
        if not scored_candidates:
            return None

        scored_candidates.sort(key=lambda item: (-item[0], item[1].name.lower()))
        if len(scored_candidates) > 1 and scored_candidates[0][0] == scored_candidates[1][0]:
            return None

        best_score, best_path, best_asset = scored_candidates[0]
        if best_score < 350:
            return None
        used_paths.add(best_path)
        return best_asset

    def _restore_media_sources_from_project(self) -> bool:
        candidates = self._project_input_candidates()
        if not candidates:
            return False

        used_paths: set[Path] = set()
        changed = False

        recovered_primary = self._recover_media_asset_from_project_folder(
            self.project.primary_video, candidates, used_paths
        )
        if recovered_primary is not None:
            self.project.primary_video = recovered_primary
            changed = True

        for source in self.project.merge_sources:
            recovered_asset = self._recover_media_asset_from_project_folder(
                source.asset, candidates, used_paths
            )
            if recovered_asset is None:
                continue
            source.asset = recovered_asset
            changed = True

        if self.project.merge_sources:
            _sync_secondary_video_from_merge_sources(self.project)
        elif self.project.secondary_video is not None:
            recovered_secondary = self._recover_media_asset_from_project_folder(
                self.project.secondary_video,
                candidates,
                used_paths,
            )
            if recovered_secondary is not None:
                self.project.secondary_video = recovered_secondary
                changed = True

        return changed

    def _current_practiscore_selection_matches_source(self) -> bool:
        scoring = self.project.scoring
        options = self._practiscore_options
        if options is None:
            return False
        if not scoring.match_type or scoring.match_type != options.match_type:
            return False
        if scoring.stage_number is None or scoring.stage_number not in options.stage_numbers:
            return False
        competitor_name = scoring.competitor_name.strip()
        if not competitor_name:
            return False
        normalized_competitor_name = _normalize_name(competitor_name)
        matching_competitors = [
            option
            for option in options.competitors
            if _normalize_name(option.name) == normalized_competitor_name
            or _practiscore_name_matches(competitor_name, option.name)
        ]
        if not matching_competitors:
            return False
        if scoring.competitor_place is None and len(matching_competitors) > 1:
            return False
        if scoring.competitor_place is None:
            return True
        if any(option.place == scoring.competitor_place for option in matching_competitors):
            return True
        return len(matching_competitors) == 1

    def _can_reimport_practiscore_source(self) -> bool:
        return (
            self._practiscore_source_path is not None
            and self._current_practiscore_selection_matches_source()
        )

    def _refresh_practiscore_comparison_for_active_stage(self) -> None:
        if self._practiscore_source_path is None:
            self._practiscore_comparison_competitors = []
            self.project.scoring.comparison_competitors = []
            return
        try:
            normalized = normalize_downloaded_practiscore_artifact(
                self._practiscore_source_path,
                source_name=self._practiscore_source_name,
                **self._practiscore_import_context_kwargs(),
            )
        except ValueError:
            self._practiscore_comparison_competitors = []
            self.project.scoring.comparison_competitors = []
            return
        self._set_practiscore_comparison_competitors(normalized.stage_import.comparison_competitors)

    def _active_stage_practiscore_overrides(self) -> dict[str, object]:
        stage = self.project.active_stage
        scoring = self.project.scoring
        imported = scoring.imported_stage
        overrides: dict[str, object] = {}
        if stage is None or imported is None:
            return overrides
        if scoring.match_type and scoring.match_type != imported.match_type:
            overrides["match_type"] = scoring.match_type
        if scoring.stage_number is not None and scoring.stage_number != imported.stage_number:
            overrides["stage_number"] = scoring.stage_number
        if scoring.competitor_name.strip() and scoring.competitor_name != imported.competitor_name:
            overrides["competitor_name"] = scoring.competitor_name
        if (
            scoring.competitor_place is not None
            and scoring.competitor_place != imported.competitor_place
        ):
            overrides["competitor_place"] = scoring.competitor_place
        if scoring.classification != imported.classification:
            overrides["classification"] = scoring.classification
        if scoring.division != imported.division:
            overrides["division"] = scoring.division
        if (
            stage.label
            and stage.label
            not in {
                imported.stage_name or "",
                f"Stage {imported.stage_number}" if imported.stage_number is not None else "",
            }
            and not re.fullmatch(r"Stage\s+\d+", stage.label)
        ):
            overrides["label"] = stage.label
        return overrides

    def _restore_active_stage_practiscore_overrides(self, overrides: dict[str, object]) -> None:
        if not overrides:
            return
        stage = self.project.active_stage
        if stage is None:
            return
        if "label" in overrides:
            stage.label = str(overrides["label"] or "").strip() or stage.label
        scoring = self.project.scoring
        if "match_type" in overrides:
            scoring.match_type = str(overrides["match_type"] or "").strip()
        if "stage_number" in overrides:
            scoring.stage_number = max(1, int(overrides["stage_number"]))
        if "competitor_name" in overrides:
            scoring.competitor_name = str(overrides["competitor_name"] or "").strip()
        if "competitor_place" in overrides:
            scoring.competitor_place = int(overrides["competitor_place"])
        if "classification" in overrides:
            scoring.classification = str(overrides["classification"] or "").strip()
        if "division" in overrides:
            scoring.division = str(overrides["division"] or "").strip()
        self._sync_project_to_active_stage()

    def _set_practiscore_comparison_competitors(
        self, competitors: Iterable[PractiScoreCompetitorOption]
    ) -> None:
        self._practiscore_comparison_competitors = [
            {
                "name": c.name,
                "place": c.place,
                "division": c.division,
                "classification": c.classification,
                "power_factor": c.power_factor,
                "raw_seconds": c.raw_seconds,
                "hit_factor": c.hit_factor,
                "final_time": c.final_time,
                "stage_points": c.stage_points,
                "stage_place": c.stage_place,
                "total_points": c.total_points,
                "class_place": c.class_place,
            }
            for c in competitors
        ]
        self.project.scoring.comparison_competitors = deepcopy(
            self._practiscore_comparison_competitors
        )

    def _import_practiscore_source(
        self,
        path: str,
        source_name: str | None = None,
        *,
        emit_change: bool = True,
        preserve_active_overrides: bool = True,
    ) -> None:
        active_stage_overrides = (
            self._active_stage_practiscore_overrides() if preserve_active_overrides else {}
        )
        normalized = normalize_downloaded_practiscore_artifact(
            path,
            source_name=source_name,
            **self._practiscore_import_context_kwargs(),
        )
        self._practiscore_options = normalized.options
        imported = normalized.stage_import
        self._set_practiscore_comparison_competitors(imported.comparison_competitors)
        apply_scoring_preset(self.project, imported.ruleset)
        self.project.scoring.enabled = True
        self.project.scoring.penalties = max(0.0, float(imported.manual_penalties))
        self.project.scoring.penalty_counts = dict(imported.penalty_counts)
        self.project.scoring.imported_stage = imported.imported_stage
        self.project.scoring.competitor_name = imported.imported_stage.competitor_name
        self.project.scoring.competitor_place = imported.imported_stage.competitor_place
        self.project.scoring.match_type = imported.imported_stage.match_type
        self.project.scoring.stage_number = imported.imported_stage.stage_number
        self.project.scoring.classification = imported.imported_stage.classification
        self.project.scoring.division = imported.imported_stage.division
        active_stage = self.project.active_stage
        if active_stage is not None:
            active_stage.imported_stage_number = imported.imported_stage.stage_number
            active_stage.imported_stage_name = (
                imported.imported_stage.stage_name
                or f"Stage {imported.imported_stage.stage_number}"
            )
            if not active_stage.label or re.fullmatch(r"Stage\s+\d+", active_stage.label):
                active_stage.label = active_stage.imported_stage_name
        imported_box = next(
            (box for box in self.project.overlay.text_boxes if box.source == "imported_summary"),
            None,
        )
        if imported_box is None:
            boxes = list(overlay_text_boxes_for_render(self.project.overlay))
            boxes.append(
                OverlayTextBox(
                    enabled=True,
                    lock_to_stack=False,
                    source="imported_summary",
                    quadrant="above_final",
                    x=None,
                    y=None,
                    background_color=self.project.overlay.custom_box_background_color,
                    text_color=self.project.overlay.custom_box_text_color,
                    opacity=self.project.overlay.custom_box_opacity,
                    width=0,
                    height=0,
                    style_type=self.project.overlay.style_type,
                    font_family=self.project.overlay.font_family,
                    font_size=self.project.overlay.font_size,
                    font_bold=self.project.overlay.font_bold,
                    font_italic=self.project.overlay.font_italic,
                    summary_metric_ids=list(_DEFAULT_SUMMARY_METRIC_IDS),
                )
            )
            self.project.overlay.text_boxes = boxes
        else:
            imported_box.enabled = True
            if not imported_box.summary_metric_ids:
                imported_box.summary_metric_ids = list(_DEFAULT_SUMMARY_METRIC_IDS)
        sync_overlay_legacy_custom_box_fields(self.project.overlay)
        self._restore_active_stage_practiscore_overrides(active_stage_overrides)
        self.update_hit_factor()
        stage_label = (
            imported.imported_stage.stage_name or f"Stage {imported.imported_stage.stage_number}"
        )
        self._set_status(f"Imported PractiScore results for {stage_label}.")
        if emit_change:
            self.project.touch()
            self.project_changed.emit()

    def _import_practiscore_source_for_all_stages(
        self,
        path: str,
        source_name: str | None = None,
        *,
        emit_change: bool = True,
    ) -> None:
        imported_stages = [
            stage for stage in self.project.stages if stage.imported_stage_number is not None
        ]
        if not imported_stages:
            self._import_practiscore_source(path, source_name, emit_change=emit_change)
            self._sync_project_to_active_stage()
            return

        selected_scoring = deepcopy(self.project.scoring)
        self._sync_project_to_active_stage()
        original_active_stage_id = self.project.active_stage_id
        selected_stage = next(
            (
                stage
                for stage in imported_stages
                if stage.imported_stage_number == selected_scoring.stage_number
            ),
            None,
        )
        target_active_stage_id = (
            selected_stage.id if selected_stage is not None else original_active_stage_id
        )
        detected_match_type = describe_practiscore_file(path, source_name=source_name).match_type

        for stage in imported_stages:
            self.project.active_stage_id = stage.id
            self._sync_active_stage_to_project()
            scoring = self.project.scoring
            scoring.match_type = detected_match_type
            scoring.stage_number = stage.imported_stage_number
            scoring.competitor_name = selected_scoring.competitor_name
            scoring.competitor_place = selected_scoring.competitor_place
            scoring.classification = selected_scoring.classification
            scoring.division = selected_scoring.division
            scoring.practiscore_source_path = path
            scoring.practiscore_source_name = source_name or Path(path).name
            self._import_practiscore_source(
                path,
                source_name,
                emit_change=False,
                preserve_active_overrides=False,
            )
            self._sync_project_to_active_stage()

        if any(stage.id == target_active_stage_id for stage in imported_stages):
            self.project.active_stage_id = target_active_stage_id
        else:
            self.project.active_stage_id = imported_stages[0].id
        self._sync_active_stage_to_project()
        active_stage_number = self.project.active_stage.imported_stage_number
        if active_stage_number is not None:
            self.project.scoring.stage_number = active_stage_number
            self._import_practiscore_source(
                path,
                source_name,
                emit_change=False,
                preserve_active_overrides=False,
            )
            self._sync_project_to_active_stage()
        if emit_change:
            self.project.touch()
            self.project_changed.emit()

    def add_merge_source(self, path: str, source_name: str | None = None) -> None:
        project_path = self._stage_project_input_path(path, source_name=source_name)
        asset = probe_video(project_path)
        self.project.merge_sources.append(
            MergeSource(
                asset=asset,
                pip_size_percent=self.project.merge.pip_size_percent,
                pip_x=self.project.merge.pip_x,
                pip_y=self.project.merge.pip_y,
                sync_offset_ms=0,
            )
        )
        new_source = self.project.merge_sources[-1]
        _sync_secondary_video_from_merge_sources(self.project)
        active_stage_id = self.project.active_stage_id
        if _source_supports_secondary_analysis(new_source):
            self._set_status("Imported merge media.")
            self.analyze_secondary(new_source.id)
            self._sync_project_to_active_stage()
            self._mark_stage_queue_stale(active_stage_id)
            self.project.touch()
            self.project_changed.emit()
            return
        self._set_status("Imported merge media.")
        self._sync_project_to_active_stage()
        self._mark_stage_queue_stale(active_stage_id)
        self.project.touch()
        self.project_changed.emit()

    def remove_merge_source(self, source_id: str) -> None:
        before_sources = list(self.project.merge_sources)
        before_count = len(before_sources)
        self.project.merge_sources = [
            source for source in self.project.merge_sources if source.id != source_id
        ]
        if len(self.project.merge_sources) == before_count:
            return
        if not self.project.merge_sources:
            self.project.merge.enabled = False
        removed_analyzed = self.project.analysis.analyzed_secondary_source_id == source_id
        _sync_secondary_video_from_merge_sources(self.project)
        active_stage_id = self.project.active_stage_id
        _prune_secondary_analysis_entries(self.project)
        if removed_analyzed:
            if _first_analyzable_merge_source(self.project) is not None:
                _refresh_secondary_analysis_projection(self.project)
            else:
                _clear_secondary_analysis_state(
                    self.project, preserve_sync_offset=bool(self.project.merge_sources)
                )
                self.project.analysis.sync_offset_ms = 0
        self._set_status("Removed merge media.")
        self._sync_project_to_active_stage()
        self._mark_stage_queue_stale(active_stage_id)
        self.project.touch()
        self.project_changed.emit()

    # --- Stage management ---

    def select_stage(self, stage_id: str) -> None:
        if not any(s.id == stage_id for s in self.project.stages):
            raise ValueError(f"Stage {stage_id} not found")
        if self.project.active_stage_id and self.project.active_stage_id != stage_id:
            self._sync_project_to_active_stage()
        self.project.active_stage_id = stage_id
        self._sync_active_stage_to_project()
        self._refresh_practiscore_comparison_for_active_stage()
        self._set_status(f"Selected stage {self._active_stage_label()}.")
        self.project.touch()
        self.project_changed.emit()

    def create_stage(self, label: str | None = None) -> ProjectStage:
        seed_from_project = not self.project.stages
        if not seed_from_project:
            self._sync_project_to_active_stage()
        next_order = max((stage.order_index for stage in self.project.stages), default=0) + 1
        stage_label = str(label or "").strip() or f"Stage {next_order}"
        if any(
            stage.label.strip().casefold() == stage_label.casefold()
            for stage in self.project.stages
        ):
            raise ValueError(f'A stage named "{stage_label}" already exists.')
        stage = ProjectStage(
            label=stage_label,
            order_index=next_order,
            export=deepcopy(self.project.export),
        )
        if seed_from_project:
            stage.primary_media = deepcopy(self.project.primary_video)
            stage.primary_trim_derivative = deepcopy(self.project.primary_trim_derivative)
            stage.added_media = list(self.project.merge_sources)
            stage.analysis = deepcopy(self.project.analysis)
            stage.scoring = deepcopy(self.project.scoring)
            stage.overlay = deepcopy(self.project.overlay)
            stage.popups = list(self.project.popups)
            stage.popup_template = deepcopy(self.project.popup_template)
            stage.merge = deepcopy(self.project.merge)
            stage.export = deepcopy(self.project.export)
        else:
            active = self.project.active_stage
            if active is not None:
                stage.analysis = AnalysisState(
                    detection_threshold=active.analysis.detection_threshold,
                    shotml_settings=deepcopy(active.analysis.shotml_settings),
                )
                stage.scoring = deepcopy(active.scoring)
                stage.scoring.stage_number = next_order
                stage.scoring.imported_stage = None
                stage.scoring.penalties = 0.0
                stage.scoring.penalty_counts = {}
                stage.scoring.hit_factor = None
                stage.overlay = deepcopy(active.overlay)
                stage.popups = deepcopy(active.popups)
                stage.popup_template = deepcopy(active.popup_template)
                stage.merge = deepcopy(active.merge)
                stage.export = deepcopy(active.export)
                stage.export.output_path = None
                stage.export.last_log = ""
                stage.export.last_error = None
        self.project.stages.append(stage)
        self.project.active_stage_id = stage.id
        self._sync_active_stage_to_project()
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Added {stage.label}.")
        return stage

    def delete_stage(self, stage_id: str) -> None:
        if len(self.project.stages) <= 1:
            raise ValueError("At least one stage must remain.")
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if stage.imported_stage_number is not None:
            self.project.excluded_imported_stage_numbers = sorted(
                {
                    *self.project.excluded_imported_stage_numbers,
                    stage.imported_stage_number,
                }
            )
        self.project.stages = [item for item in self.project.stages if item.id != stage_id]
        self.project.queue = [entry for entry in self.project.queue if entry.stage_id != stage_id]
        for index, item in enumerate(self.project.stages, start=1):
            item.order_index = index
        self.project.active_stage_id = self.project.stages[0].id
        self._sync_active_stage_to_project()
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Deleted {stage.label}.")

    def _sync_active_stage_to_project(self) -> None:
        stage = self.project.active_stage
        if stage is None:
            return
        self.project.primary_video = deepcopy(stage.primary_media)
        self.project.primary_trim_derivative = deepcopy(stage.primary_trim_derivative)
        self.project.merge_sources = deepcopy(stage.added_media)
        self.project.analysis = deepcopy(stage.analysis)
        self.project.scoring = deepcopy(stage.scoring)
        self.project.overlay = deepcopy(stage.overlay)
        self.project.popups = deepcopy(stage.popups)
        self.project.popup_template = deepcopy(stage.popup_template)
        self.project.merge = deepcopy(stage.merge)
        self.project.export = deepcopy(stage.export)
        self.project.analysis.shotml_settings = deepcopy(stage.analysis.shotml_settings)
        self.project.ui_state = UIState()
        _sync_secondary_video_from_merge_sources(self.project)

    def _sync_project_to_active_stage(self) -> None:
        stage = self.project.active_stage
        if stage is None:
            return
        stage.primary_media = deepcopy(self.project.primary_video)
        stage.primary_trim_derivative = deepcopy(self.project.primary_trim_derivative)
        stage.added_media = deepcopy(self.project.merge_sources)
        stage.analysis = deepcopy(self.project.analysis)
        stage.scoring = deepcopy(self.project.scoring)
        stage.overlay = deepcopy(self.project.overlay)
        stage.popups = deepcopy(self.project.popups)
        stage.popup_template = deepcopy(self.project.popup_template)
        stage.merge = deepcopy(self.project.merge)
        stage.export = deepcopy(self.project.export)

    def _cascade_active_presentation_settings(self) -> None:
        """Waterfall video presentation settings to later stages without overrides."""
        active = self.project.active_stage
        if active is None:
            return
        self._sync_project_to_active_stage()
        active.presentation_overridden = True
        for stage in self.project.stages:
            if stage.order_index <= active.order_index or stage.presentation_overridden:
                continue
            stage.overlay = deepcopy(active.overlay)
            stage.popups = deepcopy(active.popups)
            stage.popup_template = deepcopy(active.popup_template)
            stage.merge = deepcopy(active.merge)
            stage.export = deepcopy(active.export)
            stage.export.output_path = None
            stage.export.last_log = ""
            stage.export.last_error = None
            self._mark_stage_queue_stale(stage.id)
        self._mark_stage_queue_stale(active.id)

    def _active_stage_label(self) -> str:
        stage = self.project.active_stage
        return stage.label if stage else "?"

    def _stage_by_id(self, stage_id: str) -> ProjectStage | None:
        return next((stage for stage in self.project.stages if stage.id == stage_id), None)

    def _mark_stage_queue_stale(self, stage_id: str | None) -> None:
        if not stage_id:
            return
        stage = self._stage_by_id(stage_id)
        if stage is None:
            return
        entry = next((item for item in self.project.queue if item.stage_id == stage_id), None)
        if entry is None:
            stage.queue_status = QueueStatus.NOT_QUEUED
            return
        if entry.status == QueueStatus.PROCESSING:
            return
        entry.status = QueueStatus.STALE
        stage.queue_status = QueueStatus.STALE

    def update_stage_metadata(
        self,
        stage_id: str,
        *,
        label: str | None = None,
        stage_number: int | None | object = None,
        competitor_name: str | None = None,
        competitor_place: int | None | object = None,
    ) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        changed = False
        if label is not None:
            next_label = str(label).strip()
            if next_label and stage.label != next_label:
                if any(
                    item.id != stage_id and item.label.strip().casefold() == next_label.casefold()
                    for item in self.project.stages
                ):
                    raise ValueError(f'A stage named "{next_label}" already exists.')
                stage.label = next_label
                changed = True
        if stage_number is not None:
            next_stage_number = None if stage_number == "" else max(1, int(stage_number))
            if stage.scoring.stage_number != next_stage_number:
                stage.scoring.stage_number = next_stage_number
                changed = True
        if competitor_name is not None:
            next_competitor_name = str(competitor_name).strip()
            if next_competitor_name and stage.scoring.competitor_name != next_competitor_name:
                stage.scoring.competitor_name = next_competitor_name
                changed = True
        if competitor_place is not None:
            next_competitor_place = None if competitor_place == "" else int(competitor_place)
            if stage.scoring.competitor_place != next_competitor_place:
                stage.scoring.competitor_place = next_competitor_place
                changed = True
        if not changed:
            self._set_status(f"Stage {stage.label} details unchanged.")
            return
        if stage_id == self.project.active_stage_id:
            self._sync_active_stage_to_project()
        self._mark_stage_queue_stale(stage_id)
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Updated stage details for {stage.label}.")

    def import_stage_primary(self, stage_id: str, path: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if not stage.primary_media.path:
            configured_source = max(
                (
                    item
                    for item in self.project.stages
                    if item.id != stage.id
                    and item.primary_media.path
                    and item.order_index < stage.order_index
                ),
                key=lambda item: item.order_index,
                default=None,
            )
            if configured_source is not None:
                stage.analysis = AnalysisState(
                    detection_threshold=configured_source.analysis.detection_threshold,
                    shotml_settings=deepcopy(configured_source.analysis.shotml_settings),
                )
                stage.overlay = deepcopy(configured_source.overlay)
                stage.popups = deepcopy(configured_source.popups)
                stage.popup_template = deepcopy(configured_source.popup_template)
                stage.merge = deepcopy(configured_source.merge)
                stage.export = deepcopy(configured_source.export)
                stage.export.output_path = None
                stage.export.last_log = ""
                stage.export.last_error = None
                if stage_id == self.project.active_stage_id:
                    self._sync_active_stage_to_project()
        self._set_status(f"Importing primary media for stage {stage.label}...")
        project_path = self._stage_project_input_path(path)
        if stage_id == self.project.active_stage_id:
            preserved_overlay = deepcopy(self.project.overlay)
            preserved_popups = deepcopy(self.project.popups)
            preserved_popup_template = deepcopy(self.project.popup_template)
            preserved_merge = deepcopy(self.project.merge)
            preserved_export = deepcopy(self.project.export)
            self.ingest_primary_video(project_path)
            self.project.overlay = preserved_overlay
            self.project.popups = preserved_popups
            self.project.popup_template = preserved_popup_template
            self.project.merge = preserved_merge
            self.project.export = preserved_export
            self.project.export.output_path = None
            self.project.export.last_log = ""
            self.project.export.last_error = None
            self._sync_project_to_active_stage()
        else:
            stage.primary_media = probe_video(project_path)
            stage.primary_trim_derivative = MergeSourceTrimDerivative(
                original_path=stage.primary_media.path
            )
        stage.label = stage.label or f"Stage {stage.order_index}"
        self._mark_stage_queue_stale(stage_id)
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Imported primary media for stage {stage.label}.")

    def import_stage_added(self, stage_id: str, path: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if not stage.primary_media.path:
            raise ValueError("Add primary media before adding secondary media")
        self._set_status(f"Importing added media for stage {stage.label}...")
        project_path = self._stage_project_input_path(path)
        if stage_id == self.project.active_stage_id:
            self.add_merge_source(project_path)
            self._sync_project_to_active_stage()
        else:
            stage.added_media.append(
                MergeSource(
                    asset=probe_video(project_path),
                    pip_size_percent=stage.merge.pip_size_percent,
                    pip_x=stage.merge.pip_x,
                    pip_y=stage.merge.pip_y,
                    sync_offset_ms=0,
                )
            )
        self._mark_stage_queue_stale(stage_id)
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Imported added media for stage {stage.label}.")

    def set_stage_primary_from_existing(self, stage_id: str, source_id: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")

        def promote(
            primary_asset: VideoAsset,
            primary_trim_derivative: MergeSourceTrimDerivative,
            sources: list[MergeSource],
        ) -> tuple[VideoAsset, MergeSourceTrimDerivative, list[MergeSource]]:
            match = next((source for source in sources if source.id == source_id), None)
            if match is None:
                raise ValueError(f"Merge source {source_id} not found")
            remaining = [source for source in sources if source.id != source_id]
            next_primary = match.asset
            next_primary_trim_derivative = deepcopy(match.trim_derivative)
            if primary_asset.path:
                remaining.append(
                    MergeSource(
                        asset=primary_asset,
                        pip_size_percent=stage.merge.pip_size_percent,
                        pip_x=stage.merge.pip_x,
                        pip_y=stage.merge.pip_y,
                        sync_offset_ms=0,
                        trim_derivative=deepcopy(primary_trim_derivative),
                    )
                )
            return next_primary, next_primary_trim_derivative, remaining

        if stage_id == self.project.active_stage_id:
            next_primary, next_primary_trim_derivative, next_sources = promote(
                self.project.primary_video,
                self.project.primary_trim_derivative,
                list(self.project.merge_sources),
            )
            self.project.primary_video = next_primary
            self.project.primary_trim_derivative = next_primary_trim_derivative
            self.project.merge_sources = next_sources
            self._remember_original_shots()
            _refresh_secondary_analysis_projection(self.project)
            self._sync_project_to_active_stage()
        else:
            next_primary, next_primary_trim_derivative, next_sources = promote(
                stage.primary_media,
                stage.primary_trim_derivative,
                list(stage.added_media),
            )
            stage.primary_media = next_primary
            stage.primary_trim_derivative = next_primary_trim_derivative
            stage.added_media = next_sources
            valid_source_ids = {
                source.id
                for source in stage.added_media
                if _source_supports_secondary_analysis(source)
            }
            stage.analysis.secondary_sources = [
                entry
                for entry in stage.analysis.secondary_sources
                if entry.source_id in valid_source_ids
            ]
            if stage.analysis.analyzed_secondary_source_id not in valid_source_ids:
                stage.analysis.analyzed_secondary_source_id = next(iter(valid_source_ids), None)
                selected_entry = next(
                    (
                        entry
                        for entry in stage.analysis.secondary_sources
                        if entry.source_id == stage.analysis.analyzed_secondary_source_id
                    ),
                    None,
                )
                if selected_entry is None:
                    stage.analysis.beep_time_ms_secondary = None
                    stage.analysis.secondary_analysis_status = "idle"
                    stage.analysis.secondary_analysis_message = ""
                    stage.analysis.secondary_sync_source = "manual"
                    stage.analysis.waveform_secondary = []
                    stage.analysis.sync_offset_ms = 0
                else:
                    stage.analysis.beep_time_ms_secondary = selected_entry.beep_time_ms
                    stage.analysis.secondary_analysis_status = selected_entry.analysis_status
                    stage.analysis.secondary_analysis_message = selected_entry.analysis_message
                    stage.analysis.secondary_sync_source = selected_entry.sync_source
                    stage.analysis.waveform_secondary = list(selected_entry.waveform)
                    stage.analysis.sync_offset_ms = int(selected_entry.sync_offset_ms)
        self._mark_stage_queue_stale(stage_id)
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Set primary media for stage {stage.label}.")

    def clear_stage_primary(self, stage_id: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if stage_id == self.project.active_stage_id:
            _reset_media_dependent_state_for_primary_video(self.project)
            self.project.primary_video = VideoAsset()
            self._remember_original_shots()
            self._sync_project_to_active_stage()
        else:
            stage.primary_media = VideoAsset()
            stage.primary_trim_derivative = MergeSourceTrimDerivative()
        self._mark_stage_queue_stale(stage_id)
        self._set_status(f"Cleared primary media for stage {stage.label}.")
        self.project.touch()
        self.project_changed.emit()

    def remove_stage_added_media(self, stage_id: str, source_id: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if stage_id == self.project.active_stage_id:
            self.remove_merge_source(source_id)
            self._sync_project_to_active_stage()
        else:
            before = len(stage.added_media)
            stage.added_media = [source for source in stage.added_media if source.id != source_id]
            if len(stage.added_media) == before:
                raise ValueError(f"Merge source {source_id} not found")
            if not stage.added_media:
                stage.merge.enabled = False
        self._mark_stage_queue_stale(stage_id)
        self._set_status(f"Removed added media from stage {stage.label}.")
        self.project.touch()
        self.project_changed.emit()

    # --- Queue management ---

    def set_queue_settings(
        self,
        *,
        fade_in_s: float,
        fade_out_s: float,
        include_intro: bool | None = None,
        include_outro: bool | None = None,
    ) -> None:
        values = (float(fade_in_s), float(fade_out_s))
        if any(value < 0 or not math.isfinite(value) for value in values):
            raise ValueError("Fade durations must be finite nonnegative seconds.")
        self.project.queue_settings.fade_in_s = values[0]
        self.project.queue_settings.fade_out_s = values[1]
        if include_intro is not None:
            self.project.queue_settings.include_intro = bool(include_intro)
        if include_outro is not None:
            self.project.queue_settings.include_outro = bool(include_outro)
        self.project.touch()
        self.project_changed.emit()

    def set_in_out_media(self, kind: str, path: str) -> str:
        normalized_kind = str(kind or "").strip().lower()
        if normalized_kind not in {"intro", "outro"}:
            raise ValueError("Intro / Outro media kind must be intro or outro.")
        if self.project_path is None:
            raise ValueError("Create or open a project before selecting Intro / Outro media.")
        source_path = str(path or "").strip()
        if not source_path:
            setattr(self.project.queue_settings, f"{normalized_kind}_path", "")
            getattr(self.project, f"{normalized_kind}_clip").asset = VideoAsset()
            setattr(self.project.queue_settings, f"include_{normalized_kind}", False)
            self.project.touch()
            self.project_changed.emit()
            return ""
        asset = probe_video(source_path)
        if asset.is_still_image or asset.media_kind == "animated_gif":
            raise ValueError("Queue intro and outro files must be videos.")
        staged_path = copy_path_to_project_subdir(
            self.project_path,
            source_path,
            INTRO_OUTRO_DIRNAME,
        )
        setattr(self.project.queue_settings, f"{normalized_kind}_path", staged_path)
        getattr(self.project, f"{normalized_kind}_clip").asset = probe_video(staged_path)
        setattr(self.project.queue_settings, f"include_{normalized_kind}", True)
        label = "Intro" if normalized_kind == "intro" else "Outro"
        self._set_status(f"Selected {label} video: {Path(staged_path).name}")
        self.project.touch()
        self.project_changed.emit()
        return staged_path

    def set_queue_boundary_media(self, kind: str, path: str) -> str:
        """Compatibility alias for projects and callers using the former Queue ownership."""
        return self.set_in_out_media(kind, path)

    def add_stage_to_queue(self, stage_id: str) -> None:
        stage = self._stage_by_id(stage_id)
        if stage is None:
            raise ValueError(f"Stage {stage_id} not found")
        if stage_id == self.project.active_stage_id:
            self._sync_project_to_active_stage()
        if not stage.primary_media.path:
            raise ValueError("Stage must have primary media before queuing.")
        stage.queue_status = QueueStatus.QUEUED
        existing = next((e for e in self.project.queue if e.stage_id == stage_id), None)
        if existing:
            existing.status = QueueStatus.QUEUED
            existing.snapshot = deepcopy(stage_to_dict(stage))
            existing.created_at = datetime.now(UTC)
        else:
            self.project.queue.append(
                QueueEntry(
                    stage_id=stage_id,
                    status=QueueStatus.QUEUED,
                    snapshot=deepcopy(stage_to_dict(stage)),
                )
            )
        self._set_status(f"Added stage {stage.label} to queue.")
        self.project.touch()
        self.project_changed.emit()

    def remove_stage_from_queue(self, stage_id: str) -> None:
        before = len(self.project.queue)
        self.project.queue = [e for e in self.project.queue if e.stage_id != stage_id]
        if len(self.project.queue) < before:
            stage = next((s for s in self.project.stages if s.id == stage_id), None)
            if stage:
                stage.queue_status = QueueStatus.NOT_QUEUED
            self._set_status("Removed stage from queue.")
        self.project.touch()
        self.project_changed.emit()

    def apply_settings_to_all_stages(self) -> None:
        active = self.project.active_stage
        queued_stage_ids = {
            entry.stage_id
            for entry in self.project.queue
            if entry.status
            in (
                QueueStatus.QUEUED,
                QueueStatus.STALE,
                QueueStatus.PROCESSING,
                QueueStatus.COMPLETE,
                QueueStatus.FAILED,
            )
        }
        if active is None or not queued_stage_ids:
            self._set_status("No queued stages to update.")
            return
        applied_count = 0
        for stage in self.project.stages:
            if stage.id == active.id or stage.id not in queued_stage_ids:
                continue
            stage.analysis = deepcopy(active.analysis)
            stage.scoring = deepcopy(active.scoring)
            stage.overlay = deepcopy(active.overlay)
            stage.popups = list(active.popups)
            stage.popup_template = deepcopy(active.popup_template)
            stage.merge = deepcopy(active.merge)
            stage.export = deepcopy(active.export)
            applied_count += 1
            if stage.queue_status == QueueStatus.QUEUED:
                stage.queue_status = QueueStatus.STALE
                entry = next((e for e in self.project.queue if e.stage_id == stage.id), None)
                if entry:
                    entry.status = QueueStatus.STALE
        if applied_count == 0:
            self._set_status("No other queued stages to update.")
            return
        self._set_status("Applied active stage settings to queued stages (markers excluded).")
        self.project.touch()
        self.project_changed.emit()

    def process_queue(
        self,
        mode: str = "individual",
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        if mode not in ("individual", "combined"):
            raise ValueError("Mode must be 'individual' or 'combined'")
        queued = [
            e for e in self.project.queue if e.status in (QueueStatus.QUEUED, QueueStatus.STALE)
        ]
        if not queued:
            self._set_status("No queued stages to process.")
            return
        self._set_status(f"Processing {len(queued)} queued stage(s)...")
        self._sync_project_to_active_stage()
        original_active_stage_id = self.project.active_stage_id
        output_dir = self._ensure_output_dir()
        results: list[Path] = []
        self.project.last_combined_output_path = ""
        boundary_media = [
            (kind, Path(path))
            for kind, path, included in (
                (
                    "Intro",
                    self.project.intro_clip.asset.path or self.project.queue_settings.intro_path,
                    self.project.queue_settings.include_intro,
                ),
                (
                    "Outro",
                    self.project.outro_clip.asset.path or self.project.queue_settings.outro_path,
                    self.project.queue_settings.include_outro,
                ),
            )
            if mode == "combined" and included and str(path or "").strip()
        ]
        for label, path in boundary_media:
            if not path.is_file():
                raise ValueError(f"Queue {label.lower()} file is missing: {path}")
        total_units = len(queued) + (len(boundary_media) if mode == "combined" else 0) + (
            1 if mode == "combined" else 0
        )

        def report_progress(
            *,
            stage_progress: float,
            stage_index: int,
            stage_label: str,
            phase: str = "render",
        ) -> None:
            if progress_callback is None:
                return
            overall = min(
                0.999,
                max(0.0, (stage_index + max(0.0, min(1.0, stage_progress))) / total_units),
            )
            progress_callback(
                {
                    "progress": overall,
                    "stage_progress": max(0.0, min(1.0, stage_progress)),
                    "stage_index": stage_index + 1,
                    "stage_count": len(queued),
                    "stage_label": stage_label,
                    "mode": mode,
                    "phase": phase,
                }
            )

        try:
            for idx, entry in enumerate(
                sorted(queued, key=lambda e: self._stage_order(e.stage_id))
            ):
                entry.status = QueueStatus.PROCESSING
                stage = next((s for s in self.project.stages if s.id == entry.stage_id), None)
                if stage is None:
                    entry.status = QueueStatus.FAILED
                    entry.error_message = "Stage not found"
                    report_progress(
                        stage_progress=1.0,
                        stage_index=idx,
                        stage_label=f"Stage {idx + 1}",
                        phase="failed",
                    )
                    continue
                if not stage.primary_media.path:
                    entry.status = QueueStatus.FAILED
                    entry.error_message = "No primary media"
                    stage.queue_status = QueueStatus.FAILED
                    report_progress(
                        stage_progress=1.0,
                        stage_index=idx,
                        stage_label=stage.label,
                        phase="failed",
                    )
                    continue
                stage.queue_status = QueueStatus.PROCESSING
                self._set_status(f"Rendering stage {idx + 1}/{len(queued)}: {stage.label}...")
                self.project.active_stage_id = stage.id
                self._sync_active_stage_to_project()
                self._refresh_practiscore_comparison_for_active_stage()
                self._sync_project_to_active_stage()
                slug = self._stage_slug(stage)
                output_path = output_dir / f"{stage.order_index}-{slug}.mp4"
                render_path = self._temporary_output_path(output_path)
                try:
                    from splitshot.export.pipeline import export_project

                    export_project(
                        self.project,
                        str(render_path),
                        progress_callback=lambda value, idx=idx, label=stage.label: report_progress(
                            stage_progress=value,
                            stage_index=idx,
                            stage_label=label,
                        ),
                        log_callback=log_callback,
                        fade_in_s=(
                            self.project.queue_settings.fade_in_s if mode == "individual" else 0.0
                        ),
                        fade_out_s=(
                            self.project.queue_settings.fade_out_s if mode == "individual" else 0.0
                        ),
                        fade_audio=mode == "individual",
                    )
                    self._validate_rendered_output(render_path)
                    render_path.replace(output_path)
                    entry.status = QueueStatus.COMPLETE
                    entry.output_path = str(output_path)
                    entry.error_message = ""
                    entry.processed_at = datetime.now(UTC).isoformat()
                    stage.queue_status = QueueStatus.COMPLETE
                    stage.last_output_path = str(output_path)
                    stage.last_processed_at = entry.processed_at
                    self._sync_project_to_active_stage()
                    results.append(output_path)
                    report_progress(
                        stage_progress=1.0,
                        stage_index=idx,
                        stage_label=stage.label,
                    )
                    self._set_status(f"Completed stage {idx + 1}/{len(queued)}: {stage.label}")
                except Exception as exc:  # noqa: BLE001 - isolate failures per queued stage.
                    render_path.unlink(missing_ok=True)
                    entry.status = QueueStatus.FAILED
                    entry.error_message = str(exc)
                    stage.queue_status = QueueStatus.FAILED
                    self._sync_project_to_active_stage()
                    report_progress(
                        stage_progress=1.0,
                        stage_index=idx,
                        stage_label=stage.label,
                        phase="failed",
                    )
                    self._set_status(f"Failed stage {idx + 1}/{len(queued)}: {stage.label} — {exc}")

            if mode == "combined" and len(results) >= 1:
                prepared_boundary_paths: list[Path] = []
                sequence_results = list(results)
                try:
                    for boundary_index, (label, source_path) in enumerate(boundary_media):
                        overlay_path = self._render_queue_boundary_overlay(
                            label.lower(),
                            source_path,
                            output_dir,
                            progress_callback=(
                                None
                                if progress_callback is None
                                else lambda value, boundary_index=boundary_index, label=label: progress_callback(
                                    {
                                        "progress": min(
                                            0.999,
                                            (len(queued) + boundary_index + value) / total_units,
                                        ),
                                        "stage_progress": value,
                                        "stage_index": len(queued),
                                        "stage_count": len(queued),
                                        "stage_label": label,
                                        "mode": mode,
                                        "phase": "boundary",
                                    }
                                )
                            ),
                            log_callback=log_callback,
                        )
                        try:
                            prepared_path = self._prepare_queue_boundary_clip(
                                overlay_path,
                                results[0],
                                output_dir,
                                label.lower(),
                                log_callback=log_callback,
                            )
                        finally:
                            overlay_path.unlink(missing_ok=True)
                        prepared_boundary_paths.append(prepared_path)
                        if label == "Intro":
                            sequence_results.insert(0, prepared_path)
                        else:
                            sequence_results.append(prepared_path)
                        if progress_callback is not None:
                            completed_units = len(queued) + boundary_index + 1
                            progress_callback(
                                {
                                    "progress": min(0.999, completed_units / total_units),
                                    "stage_progress": 1.0,
                                    "stage_index": len(queued),
                                    "stage_count": len(queued),
                                    "stage_label": label,
                                    "mode": mode,
                                    "phase": "boundary",
                                }
                            )
                    report_progress(
                        stage_progress=0.0,
                        stage_index=len(queued),
                        stage_label="Combined output",
                        phase="combine",
                    )
                    combined_path = self._concat_outputs(sequence_results, output_dir)
                    report_progress(
                        stage_progress=0.55,
                        stage_index=len(queued),
                        stage_label="Combined output",
                        phase="combine",
                    )
                    self._apply_queue_fades_to_file(
                        combined_path,
                        fade_in_s=(
                            0.0
                            if self.project.queue_settings.include_intro
                            and self.project.intro_clip.asset.path
                            else None
                        ),
                        fade_out_s=(
                            0.0
                            if self.project.queue_settings.include_outro
                            and self.project.outro_clip.asset.path
                            else None
                        ),
                        log_callback=log_callback,
                    )
                finally:
                    for prepared_path in prepared_boundary_paths:
                        prepared_path.unlink(missing_ok=True)
                self._validate_rendered_output(combined_path)
                self.project.last_combined_output_path = str(combined_path)
                if progress_callback is not None:
                    progress_callback(
                        {
                            "progress": 1.0,
                            "stage_progress": 1.0,
                            "stage_index": len(queued),
                            "stage_count": len(queued),
                            "stage_label": "Combined output",
                            "mode": mode,
                            "phase": "complete",
                        }
                    )
                failed_count = sum(1 for entry in queued if entry.status == QueueStatus.FAILED)
                self._set_status(
                    f"Combined export complete: {combined_path} "
                    f"({len(results)} succeeded, {failed_count} failed)."
                )
            else:
                if progress_callback is not None:
                    progress_callback(
                        {
                            "progress": 1.0,
                            "stage_progress": 1.0,
                            "stage_index": len(queued),
                            "stage_count": len(queued),
                            "stage_label": "Queue",
                            "mode": mode,
                            "phase": "complete",
                        }
                    )
                failed_count = sum(1 for entry in queued if entry.status == QueueStatus.FAILED)
                self._set_status(
                    f"Queue finished: {len(results)} succeeded, {failed_count} failed."
                )
        finally:
            self.project.active_stage_id = original_active_stage_id
            if self.project.active_stage:
                self._sync_active_stage_to_project()
            self.project.touch()
            self.project_changed.emit()

    def _stage_order(self, stage_id: str) -> int:
        stage = next((s for s in self.project.stages if s.id == stage_id), None)
        return stage.order_index if stage else 999

    def _stage_slug(self, stage: ProjectStage) -> str:
        import re

        label = stage.label or f"stage-{stage.order_index}"
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
        return slug or f"stage-{stage.order_index}"

    def stage_output_path(self, stage: ProjectStage | None = None) -> Path:
        target_stage = stage or self.project.active_stage
        if target_stage is None:
            raise ValueError("No active stage available for export.")
        output_dir = self._ensure_output_dir()
        return output_dir / f"{target_stage.order_index}-{self._stage_slug(target_stage)}.mp4"

    def _concat_outputs(self, results: list[Path], output_dir: Path) -> Path:
        combined_path = output_dir / f"{self.project.name}-combined.mp4"
        temp_combined_path = self._temporary_output_path(combined_path)
        ces = self.project.combined_export_settings

        try:
            if not ces.separator_enabled:
                self._plain_concat(results, output_dir, temp_combined_path)
            else:
                self._separator_concat(results, output_dir, temp_combined_path, ces)
            self._validate_rendered_output(temp_combined_path)
            temp_combined_path.replace(combined_path)
            return combined_path
        except Exception:
            temp_combined_path.unlink(missing_ok=True)
            raise

    def _apply_queue_fades_to_file(
        self,
        output_path: Path,
        *,
        fade_in_s: float | None = None,
        fade_out_s: float | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        fade_in_s = (
            self.project.queue_settings.fade_in_s if fade_in_s is None else float(fade_in_s)
        )
        fade_out_s = (
            self.project.queue_settings.fade_out_s if fade_out_s is None else float(fade_out_s)
        )
        if fade_in_s <= 0 and fade_out_s <= 0:
            return
        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                str(output_path),
            ],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        info = json.loads(probe.stdout)
        duration_s = float(info.get("format", {}).get("duration") or 0.0)
        from splitshot.export.pipeline import _normalized_output_fades

        fade_in_s, fade_out_s = _normalized_output_fades(fade_in_s, fade_out_s, duration_s)
        video_filters: list[str] = []
        audio_filters: list[str] = []
        if fade_in_s > 0:
            video_filters.append(f"fade=t=in:st=0:d={fade_in_s:.3f}:color=black")
            audio_filters.append(f"afade=t=in:st=0:d={fade_in_s:.3f}")
        if fade_out_s > 0:
            start_s = max(0.0, duration_s - fade_out_s)
            video_filters.append(f"fade=t=out:st={start_s:.3f}:d={fade_out_s:.3f}:color=black")
            audio_filters.append(f"afade=t=out:st={start_s:.3f}:d={fade_out_s:.3f}")
        has_audio = any(stream.get("codec_type") == "audio" for stream in info.get("streams", []))
        faded_path = self._temporary_output_path(output_path)
        codec = "libx265" if self.project.export.video_codec == ExportVideoCodec.HEVC else "libx264"
        command = [
            "-i",
            str(output_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0?",
            "-vf",
            ",".join(video_filters),
            "-c:v",
            codec,
            "-preset",
            self.project.export.ffmpeg_preset,
            "-b:v",
            f"{self.project.export.video_bitrate_mbps:g}M",
        ]
        if has_audio:
            command.extend(
                [
                    "-af",
                    ",".join(audio_filters),
                    "-c:a",
                    self.project.export.audio_codec.value,
                    "-ar",
                    str(self.project.export.audio_sample_rate),
                    "-b:a",
                    f"{self.project.export.audio_bitrate_kbps}k",
                ]
            )
        else:
            command.append("-an")
        command.extend(["-movflags", "+faststart", str(faded_path)])
        try:
            run_ffmpeg(command, log_callback=log_callback)
            self._validate_rendered_output(faded_path)
            faded_path.replace(output_path)
        finally:
            faded_path.unlink(missing_ok=True)

    def _match_summary_overlay_text(self, metric_ids: list[str]) -> str:
        from splitshot.browser.state import _build_match_metrics, _build_stage_metrics

        metrics = _build_match_metrics(_build_stage_metrics(self.project))
        scoring = self.project.scoring
        values = {
            "match_result": str(metrics.get("display_value") or ""),
            "raw_time": (
                ""
                if metrics.get("raw_time_ms") is None
                else f"{float(metrics['raw_time_ms']) / 1000.0:.2f}s"
            ),
            "stage_count": str(metrics.get("stage_count") or ""),
            "total_shots": str(metrics.get("total_shots") or ""),
            "shot_points": f"{float(metrics.get('shot_points') or 0):g}",
            "penalties": f"{float(metrics.get('total_penalties') or 0):g}",
            "competitor": scoring.competitor_name,
            "division": scoring.division,
            "classification": scoring.classification,
            "overall_place": (
                "" if scoring.competitor_place is None else str(scoring.competitor_place)
            ),
        }
        labels = {
            "match_result": str(metrics.get("result_label") or "Final"),
            "raw_time": "Raw Time",
            "stage_count": "Stages",
            "total_shots": "Shots",
            "shot_points": "Shot Points",
            "penalties": "Penalties",
            "competitor": "Competitor",
            "division": "Division",
            "classification": "Class",
            "overall_place": "Overall",
        }
        return "\n".join(
            f"{labels[metric_id]} {values[metric_id]}"
            for metric_id in metric_ids
            if values.get(metric_id)
        )

    def _render_queue_boundary_overlay(
        self,
        kind: str,
        source_path: Path,
        output_dir: Path,
        *,
        progress_callback: Callable[[float], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> Path:
        clip = getattr(self.project, f"{kind}_clip")
        boundary_project = deepcopy(self.project)
        boundary_project.stages = []
        boundary_project.active_stage_id = ""
        boundary_project.primary_video = deepcopy(clip.asset)
        boundary_project.primary_video.path = str(source_path)
        boundary_project.primary_trim_derivative = MergeSourceTrimDerivative()
        boundary_project.secondary_video = None
        boundary_project.merge_sources = []
        boundary_project.analysis = AnalysisState()
        boundary_project.scoring.enabled = False
        boundary_project.overlay = deepcopy(clip.overlay)
        boundary_project.popups = []
        boundary_project.merge.enabled = False
        for box in boundary_project.overlay.text_boxes:
            if box.source != "match_summary":
                continue
            box.text = self._match_summary_overlay_text(box.summary_metric_ids)
            box.source = "manual"
        rendered_path = self._temporary_output_path(output_dir / f"queue-{kind}-overlay.mp4")
        from splitshot.export.pipeline import export_project

        try:
            export_project(
                boundary_project,
                str(rendered_path),
                progress_callback=progress_callback,
                log_callback=log_callback,
            )
            self._validate_rendered_output(rendered_path)
            return rendered_path
        except Exception:
            rendered_path.unlink(missing_ok=True)
            raise

    def _prepare_queue_boundary_clip(
        self,
        source_path: Path,
        reference_path: Path,
        output_dir: Path,
        kind: str,
        *,
        log_callback: Callable[[str], None] | None = None,
    ) -> Path:
        source_info = run_ffprobe_json(source_path)
        reference_info = run_ffprobe_json(reference_path)
        source_duration_s = float(source_info.get("format", {}).get("duration") or 0.0)
        if source_duration_s <= 0:
            raise RuntimeError(f"Queue {kind} has no measurable duration: {source_path}")
        reference_video = next(
            (
                stream
                for stream in reference_info.get("streams", [])
                if stream.get("codec_type") == "video"
            ),
            None,
        )
        if reference_video is None:
            raise RuntimeError(f"Queue reference output has no video: {reference_path}")
        width = max(2, int(reference_video.get("width") or 0))
        height = max(2, int(reference_video.get("height") or 0))
        frame_rate = str(reference_video.get("avg_frame_rate") or "30/1")
        source_has_audio = any(
            stream.get("codec_type") == "audio" for stream in source_info.get("streams", [])
        )
        reference_audio = next(
            (
                stream
                for stream in reference_info.get("streams", [])
                if stream.get("codec_type") == "audio"
            ),
            None,
        )
        from splitshot.export.pipeline import _normalized_output_fades

        clip = getattr(self.project, f"{kind}_clip", None)
        if clip is None:
            raise ValueError("Queue boundary kind must be intro or outro.")
        fade_in_s, fade_out_s = _normalized_output_fades(
            clip.fade_in_s,
            clip.fade_out_s,
            source_duration_s,
        )
        video_filters = [
            f"scale={width}:{height}:force_original_aspect_ratio=decrease",
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black",
            "setsar=1",
            f"fps={frame_rate}",
            "format=yuv420p",
        ]
        audio_filters: list[str] = []
        if fade_in_s > 0:
            video_filters.append(f"fade=t=in:st=0:d={fade_in_s:.3f}:color=black")
            audio_filters.append(f"afade=t=in:st=0:d={fade_in_s:.3f}")
        if fade_out_s > 0:
            fade_out_start = max(0.0, source_duration_s - fade_out_s)
            video_filters.append(
                f"fade=t=out:st={fade_out_start:.3f}:d={fade_out_s:.3f}:color=black"
            )
            audio_filters.append(f"afade=t=out:st={fade_out_start:.3f}:d={fade_out_s:.3f}")
        sample_rate = int((reference_audio or {}).get("sample_rate") or 48000)
        channel_layout = str((reference_audio or {}).get("channel_layout") or "stereo")
        prepared_path = self._temporary_output_path(output_dir / f"queue-{kind}.mp4")
        codec = "libx265" if self.project.export.video_codec == ExportVideoCodec.HEVC else "libx264"
        command = ["-i", str(source_path)]
        if reference_audio is not None and not source_has_audio:
            command.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    f"anullsrc=r={sample_rate}:cl={channel_layout}",
                ]
            )
        command.extend(
            [
                "-map",
                "0:v:0",
                "-vf",
                ",".join(video_filters),
                "-c:v",
                codec,
                "-preset",
                self.project.export.ffmpeg_preset,
                "-b:v",
                f"{self.project.export.video_bitrate_mbps:g}M",
            ]
        )
        if reference_audio is not None:
            command.extend(["-map", "0:a:0" if source_has_audio else "1:a:0"])
            normalized_audio_filters = [
                f"aresample={sample_rate}",
                f"aformat=sample_rates={sample_rate}:channel_layouts={channel_layout}",
                *audio_filters,
            ]
            command.extend(
                [
                    "-af",
                    ",".join(normalized_audio_filters),
                    "-c:a",
                    self.project.export.audio_codec.value,
                    "-ar",
                    str(sample_rate),
                    "-b:a",
                    f"{self.project.export.audio_bitrate_kbps}k",
                ]
            )
        else:
            command.append("-an")
        command.extend(
            [
                "-t",
                f"{source_duration_s:.3f}",
                "-movflags",
                "+faststart",
                str(prepared_path),
            ]
        )
        try:
            run_ffmpeg(command, log_callback=log_callback)
            self._validate_rendered_output(prepared_path)
            return prepared_path
        except Exception:
            prepared_path.unlink(missing_ok=True)
            raise

    def _validate_rendered_output(self, output_path: Path) -> None:
        if not output_path.exists():
            raise RuntimeError(f"Rendered output missing: {output_path}")
        if output_path.stat().st_size <= 0:
            raise RuntimeError(f"Rendered output is empty: {output_path}")
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "quiet",
                    "-print_format",
                    "json",
                    "-show_format",
                    "-show_streams",
                    str(output_path),
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            info = json.loads(result.stdout)
        except Exception as exc:
            raise RuntimeError(f"Rendered output is invalid: {output_path} ({exc})") from exc
        streams = info.get("streams", [])
        if not any(stream.get("codec_type") == "video" for stream in streams):
            raise RuntimeError(f"Rendered output has no video stream: {output_path}")

    def _temporary_output_path(self, output_path: Path) -> Path:
        return output_path.with_name(f"{output_path.stem}.tmp-{uuid4().hex}{output_path.suffix}")

    def _plain_concat(self, results: list[Path], output_dir: Path, combined_path: Path) -> Path:
        import subprocess

        list_path = output_dir / "concat-list.txt"
        with open(list_path, "w") as f:
            f.writelines(f"file '{result.resolve()}'\n" for result in results)
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-c",
                    "copy",
                    str(combined_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Concat failed: {e.stderr}") from e
        finally:
            if list_path.exists():
                list_path.unlink()
        return combined_path

    def _separator_concat(
        self,
        results: list[Path],
        output_dir: Path,
        combined_path: Path,
        ces: CombinedExportSettings,
    ) -> Path:
        import subprocess

        duration = max(0.5, min(1.0, ces.separator_duration_s))
        separator_paths: list[Path] = []

        # Generate separator clips
        for i in range(len(results)):
            sep_path = output_dir / f"separator-{i:04d}.mp4"
            separator_paths.append(sep_path)
            if i >= len(results) - 1:
                # No separator needed after last stage; create a dummy for indexing
                continue
            self._render_separator(sep_path, duration, ces)

        # Build concat with separators between stages
        list_path = output_dir / "concat-list.txt"
        with open(list_path, "w") as f:
            for i, result in enumerate(results):
                f.write(f"file '{result}'\n")
                if i < len(results) - 1:
                    f.write(f"file '{separator_paths[i]}'\n")
        try:
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(list_path),
                    "-c",
                    "copy",
                    str(combined_path),
                ],
                capture_output=True,
                text=True,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Separator concat failed: {e.stderr}") from e
        finally:
            if list_path.exists():
                list_path.unlink()
            for sp in separator_paths:
                if sp.exists():
                    sp.unlink()
        return combined_path

    def _render_separator(
        self,
        output_path: Path,
        duration_s: float,
        ces: CombinedExportSettings,
    ) -> None:
        import subprocess

        filter_parts: list[str] = []
        has_text = bool(ces.separator_text.strip())
        has_image = (
            bool(ces.separator_image_path.strip()) and Path(ces.separator_image_path).exists()
        )

        if has_text:
            escaped_text = ces.separator_text.replace("'", "'\\''")
            filter_parts.append(
                f"drawtext=text='{escaped_text}':fontsize=48:fontcolor=white:"
                f"x=(w-text_w)/2:y=(h-text_h)/2"
            )

        if has_image:
            filter_parts.append(
                f"movie='{ces.separator_image_path}'[img];"
                f"[img]scale=iw*min(1\\,min(w/iw\\,h/ih)):-1[scaled];"
            )

        cmd = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s=1920x1080:d={duration_s}:r=30",
        ]

        if filter_parts:
            filter_str = ";".join(filter_parts)
            if has_image and has_text:
                filter_str = (
                    f"movie='{ces.separator_image_path}'[img];"
                    f"[0][img]overlay=(W-w)/2:(H-h)/2:shortest=1,"
                    f"drawtext=text='{escaped_text}':fontsize=48:fontcolor=white:"
                    f"x=(w-text_w)/2:y=(h-text_h)/2-60"
                )
            elif has_image:
                filter_str = (
                    f"movie='{ces.separator_image_path}'[img];"
                    f"[0][img]overlay=(W-w)/2:(H-h)/2:shortest=1"
                )
            cmd.extend(["-filter_complex", filter_str])

        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-pix_fmt",
                "yuv420p",
                "-an",
                str(output_path),
            ]
        )

        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Separator render failed: {result.stderr}")

    def rerun_merge_source_analysis(self, source_id: str) -> None:
        source = next((item for item in self.project.merge_sources if item.id == source_id), None)
        if source is None:
            raise ValueError("Merge source not found")
        if not _source_supports_secondary_analysis(source):
            raise ValueError("Selected merge source does not support sync analysis")
        self.analyze_secondary(source_id)

    def _trimmed_media_dir(self) -> Path | None:
        if self.project_path is None:
            return None
        derivative_dir = self.project_path / INPUT_DIRNAME / "trimmed"
        derivative_dir.mkdir(parents=True, exist_ok=True)
        return derivative_dir

    def _trimmed_derivative_path(self, source_file: Path) -> str:
        stage = self.project.active_stage
        stage_number = (
            stage.imported_stage_number
            if stage is not None and stage.imported_stage_number is not None
            else (stage.order_index if stage is not None else 1)
        )
        timestamp = datetime.now().astimezone()
        stem = f"Trim_Stage{stage_number}_{timestamp:%H-%M-%S}_{timestamp:%Y-%m-%d}"
        directory = self._trimmed_media_dir() or source_file.parent
        candidate = directory / f"{stem}.mp4"
        suffix = 2
        while candidate.exists():
            candidate = directory / f"{stem}_{suffix}.mp4"
            suffix += 1
        return str(candidate)

    def _apply_primary_trim(
        self,
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        clear: bool = False,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        if clear:
            self.project.primary_trim_derivative = MergeSourceTrimDerivative(
                original_path=self.project.primary_video.path,
            )
            return
        if (
            self.project.primary_video.is_still_image
            or self.project.primary_video.media_kind == "animated_gif"
        ):
            raise ValueError("Still images and animated images cannot be trimmed")
        if start_s is None and end_s is None:
            return
        start_s, end_s = _normalized_trim_window(self.project.primary_video, start_s, end_s)
        source_path = self.project.primary_video.path
        if not source_path:
            raise ValueError("Primary video has no asset path")
        source_file = Path(source_path)
        derivative_path = self._trimmed_derivative_path(source_file)
        try:
            trim_video(
                source_path,
                derivative_path,
                start_s=start_s,
                end_s=end_s,
                log_callback=log_callback,
            )
            derivative_asset = probe_video(derivative_path)
        except Exception as exc:
            Path(derivative_path).unlink(missing_ok=True)
            raise ValueError(f"Trim failed for {source_path} -> {derivative_path}: {exc}") from exc
        self.project.primary_trim_derivative = MergeSourceTrimDerivative(
            original_path=source_path,
            derivative_path=derivative_path,
            derivative_asset=derivative_asset,
            active_path_kind=MergeSourceAssetPathKind.LOCAL_DERIVATIVE,
            start_s=start_s,
            end_s=end_s,
        )

    def _apply_merge_source_trim(
        self,
        source: MergeSource,
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        clear: bool = False,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        if clear:
            source.trim_derivative = MergeSourceTrimDerivative(original_path=source.asset.path)
            return
        if not _source_supports_secondary_analysis(source):
            raise ValueError("Still images and animated images cannot be trimmed")
        if start_s is None and end_s is None:
            return
        start_s, end_s = _normalized_trim_window(source.asset, start_s, end_s)
        source_path = source.asset.path
        if not source_path:
            raise ValueError("Merge source has no asset path")
        source_file = Path(source_path)
        derivative_path = self._trimmed_derivative_path(source_file)
        try:
            trim_video(
                source_path,
                derivative_path,
                start_s=start_s,
                end_s=end_s,
                log_callback=log_callback,
            )
            derivative_asset = probe_video(derivative_path)
        except Exception as exc:
            Path(derivative_path).unlink(missing_ok=True)
            raise ValueError(f"Trim failed for {source_path} -> {derivative_path}: {exc}") from exc
        source.trim_derivative = MergeSourceTrimDerivative(
            original_path=source_path,
            derivative_path=derivative_path,
            derivative_asset=derivative_asset,
            active_path_kind=MergeSourceAssetPathKind.LOCAL_DERIVATIVE,
            start_s=start_s,
            end_s=end_s,
        )

    def _source_trim_window_from_buffers(
        self,
        source: MergeSource,
        *,
        keep_before_beep_s: float | None = None,
        keep_after_last_shot_s: float | None = None,
    ) -> tuple[float | None, float | None]:
        start_s = None
        end_s = None
        primary_timeline_offset_ms = round(
            float(self.project.primary_trim_derivative.start_s or 0.0) * 1000
        )
        primary_beep_ms = self.project.analysis.beep_time_ms_primary
        if primary_beep_ms is not None and keep_before_beep_s is not None:
            start_s = max(
                0.0,
                (
                    (int(primary_beep_ms) + primary_timeline_offset_ms + int(source.sync_offset_ms))
                    / 1000
                )
                - keep_before_beep_s,
            )
        shots = self.project.analysis.shots or []
        if shots and keep_after_last_shot_s is not None:
            last_shot_ms = max(int(shot.time_ms or 0) for shot in shots)
            end_s = (
                (last_shot_ms + primary_timeline_offset_ms + int(source.sync_offset_ms)) / 1000
            ) + keep_after_last_shot_s
            duration_ms = int(source.asset.duration_ms or 0)
            if duration_ms > 0:
                end_s = min(end_s, duration_ms / 1000)
        return start_s, end_s

    def _primary_trim_window_from_buffers(
        self,
        *,
        keep_before_beep_s: float | None = None,
        keep_after_last_shot_s: float | None = None,
    ) -> tuple[float | None, float | None]:
        start_s = None
        end_s = None
        primary_timeline_offset_ms = round(
            float(self.project.primary_trim_derivative.start_s or 0.0) * 1000
        )
        primary_beep_ms = self.project.analysis.beep_time_ms_primary
        if primary_beep_ms is not None and keep_before_beep_s is not None:
            start_s = max(
                0.0,
                ((int(primary_beep_ms) + primary_timeline_offset_ms) / 1000) - keep_before_beep_s,
            )
        shots = self.project.analysis.shots or []
        if shots and keep_after_last_shot_s is not None:
            last_shot_ms = max(int(shot.time_ms or 0) for shot in shots)
            end_s = ((last_shot_ms + primary_timeline_offset_ms) / 1000) + keep_after_last_shot_s
            duration_ms = int(self.project.primary_video.duration_ms or 0)
            if duration_ms > 0:
                end_s = min(end_s, duration_ms / 1000)
        return start_s, end_s

    def trim_merge_source(
        self,
        source_id: str,
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        clear: bool = False,
    ) -> None:
        source = next((s for s in self.project.merge_sources if s.id == source_id), None)
        if source is None:
            raise ValueError(f"Merge source {source_id} not found")
        self._apply_merge_source_trim(source, start_s=start_s, end_s=end_s, clear=clear)
        active_stage_id = self.project.active_stage_id
        self._mark_stage_queue_stale(active_stage_id)
        self._set_status(
            "Cleared trim."
            if clear
            else f"Trimmed {source.asset.path} (start={_format_trim_boundary(start_s)}s, end={_format_trim_boundary(end_s)}s)."
        )
        if _source_supports_secondary_analysis(source):
            self.analyze_secondary(source_id)
            self._sync_project_to_active_stage()
            self.project.touch()
            self.project_changed.emit()
        else:
            self._sync_project_to_active_stage()
            self.project.touch()
            self.project_changed.emit()

    def trim_primary_video(
        self,
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        clear: bool = False,
    ) -> None:
        if not self.project.primary_video.path:
            raise ValueError("Primary video not found")
        self._apply_primary_trim(start_s=start_s, end_s=end_s, clear=clear)
        active_stage_id = self.project.active_stage_id
        self._mark_stage_queue_stale(active_stage_id)
        self.analyze_primary()
        for source in self.project.merge_sources:
            if _source_supports_secondary_analysis(source):
                self.analyze_secondary(source.id)
        self._sync_project_to_active_stage()
        self._set_status(
            "Cleared primary trim."
            if clear
            else f"Trimmed {self.project.primary_video.path} (start={_format_trim_boundary(start_s)}s, end={_format_trim_boundary(end_s)}s)."
        )
        self.project.touch()
        self.project_changed.emit()

    def trim_all_merge_sources(
        self,
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        keep_before_beep_s: float | None = None,
        keep_after_last_shot_s: float | None = None,
        clear: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        primary_is_trimmable = bool(
            self.project.primary_video.path
            and not self.project.primary_video.is_still_image
            and self.project.primary_video.media_kind != "animated_gif"
        )
        trimmable_sources = [
            source
            for source in self.project.merge_sources
            if clear or _source_supports_secondary_analysis(source)
        ]
        primary_source_count = 1 if primary_is_trimmable else 0
        total_source_count = primary_source_count + len(trimmable_sources)
        if total_source_count == 0:
            return
        stage = self.project.active_stage
        stage_label = stage.label if stage is not None else "Active stage"
        completed_count = 0

        def report_file(path: str) -> None:
            nonlocal completed_count
            completed_count += 1
            if progress_callback is None:
                return
            progress_callback(
                {
                    "progress": min(0.99, completed_count / total_source_count),
                    "file_index": completed_count,
                    "file_count": total_source_count,
                    "stage_index": 1,
                    "stage_count": 1,
                    "stage_label": stage_label,
                    "media_label": Path(path).name,
                    "phase": "file",
                    "action": "clear" if clear else "trim",
                }
            )

        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 0.0,
                    "file_index": 0,
                    "file_count": total_source_count,
                    "stage_index": 1,
                    "stage_count": 1,
                    "stage_label": stage_label,
                    "media_label": "",
                    "phase": "start",
                    "action": "clear" if clear else "trim",
                }
            )
        self._set_status(
            "Clearing trim derivatives..."
            if clear
            else f"Trimming {total_source_count} stage media file{'s' if total_source_count != 1 else ''}."
        )
        primary_start_s = start_s
        primary_end_s = end_s
        if not clear and (keep_before_beep_s is not None or keep_after_last_shot_s is not None):
            primary_start_s, primary_end_s = self._primary_trim_window_from_buffers(
                keep_before_beep_s=keep_before_beep_s,
                keep_after_last_shot_s=keep_after_last_shot_s,
            )
        if primary_is_trimmable:
            self._apply_primary_trim(
                start_s=primary_start_s,
                end_s=primary_end_s,
                clear=clear,
                log_callback=log_callback,
            )
            report_file(self.project.primary_video.path)
        for source in trimmable_sources:
            next_start_s = start_s
            next_end_s = end_s
            if not clear and (keep_before_beep_s is not None or keep_after_last_shot_s is not None):
                next_start_s, next_end_s = self._source_trim_window_from_buffers(
                    source,
                    keep_before_beep_s=keep_before_beep_s,
                    keep_after_last_shot_s=keep_after_last_shot_s,
                )
            self._apply_merge_source_trim(
                source,
                start_s=next_start_s,
                end_s=next_end_s,
                clear=clear,
                log_callback=log_callback,
            )
            report_file(source.asset.path)
        active_stage_id = self.project.active_stage_id
        self._mark_stage_queue_stale(active_stage_id)
        if self.project.primary_video.path:
            self.analyze_primary()
        for source in self.project.merge_sources:
            if _source_supports_secondary_analysis(source):
                self.analyze_secondary(source.id)
        self._sync_project_to_active_stage()
        self._set_status(
            "Cleared trim for all stage media." if clear else "Applied trim to all stage media."
        )
        self.project.touch()
        self.project_changed.emit()
        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 1.0,
                    "file_index": total_source_count,
                    "file_count": total_source_count,
                    "stage_index": 1,
                    "stage_count": 1,
                    "stage_label": stage_label,
                    "media_label": "",
                    "phase": "complete",
                    "action": "clear" if clear else "trim",
                }
            )

    def trim_selected_stages(
        self,
        stage_ids: Iterable[str],
        *,
        start_s: float | None = None,
        end_s: float | None = None,
        keep_before_beep_s: float | None = None,
        keep_after_last_shot_s: float | None = None,
        clear: bool = False,
        progress_callback: Callable[[dict[str, Any]], None] | None = None,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        requested_ids = list(dict.fromkeys(str(stage_id) for stage_id in stage_ids))
        selected_stages = [
            stage
            for stage in self.project.stages
            if stage.id in requested_ids and stage.primary_media.path
        ]
        if not selected_stages:
            raise ValueError("Select at least one stage with primary media.")

        self._sync_project_to_active_stage()
        original_active_stage_id = self.project.active_stage_id
        processed_count = 0
        total_file_count = sum(
            (
                1
                if stage.primary_media.path
                and not stage.primary_media.is_still_image
                and stage.primary_media.media_kind != "animated_gif"
                else 0
            )
            + sum(
                1
                for source in stage.added_media
                if clear or _source_supports_secondary_analysis(source)
            )
            for stage in selected_stages
        )
        completed_file_count = 0
        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 0.0,
                    "file_index": 0,
                    "file_count": total_file_count,
                    "stage_index": 0,
                    "stage_count": len(selected_stages),
                    "stage_label": "",
                    "media_label": "",
                    "phase": "start",
                    "action": "clear" if clear else "trim",
                }
            )
        try:
            for stage_index, stage in enumerate(selected_stages, start=1):
                self.project.active_stage_id = stage.id
                self._sync_active_stage_to_project()

                def report_stage_file(
                    detail: dict[str, Any],
                    *,
                    current_stage_index: int = stage_index,
                    current_stage: ProjectStage = stage,
                ) -> None:
                    nonlocal completed_file_count
                    if detail.get("phase") != "file":
                        return
                    completed_file_count += 1
                    if progress_callback is None:
                        return
                    progress_callback(
                        {
                            **detail,
                            "progress": min(
                                0.99,
                                completed_file_count / max(1, total_file_count),
                            ),
                            "file_index": completed_file_count,
                            "file_count": total_file_count,
                            "stage_index": current_stage_index,
                            "stage_count": len(selected_stages),
                            "stage_label": current_stage.label,
                        }
                    )

                self.trim_all_merge_sources(
                    start_s=start_s,
                    end_s=end_s,
                    keep_before_beep_s=keep_before_beep_s,
                    keep_after_last_shot_s=keep_after_last_shot_s,
                    clear=clear,
                    progress_callback=report_stage_file,
                    log_callback=log_callback,
                )
                processed_count += 1
        finally:
            if any(stage.id == original_active_stage_id for stage in self.project.stages):
                self.project.active_stage_id = original_active_stage_id
            else:
                self.project.active_stage_id = self.project.stages[0].id
            self._sync_active_stage_to_project()
            self._refresh_practiscore_comparison_for_active_stage()

        action = "Cleared trim for" if clear else "Applied trim to"
        self._set_status(
            f"{action} {processed_count} selected stage{'s' if processed_count != 1 else ''}."
        )
        self.project.touch()
        self.project_changed.emit()
        if progress_callback is not None:
            progress_callback(
                {
                    "progress": 1.0,
                    "file_index": total_file_count,
                    "file_count": total_file_count,
                    "stage_index": len(selected_stages),
                    "stage_count": len(selected_stages),
                    "stage_label": "",
                    "media_label": "",
                    "phase": "complete",
                    "action": "clear" if clear else "trim",
                }
            )

    def set_detection_threshold(self, value: float) -> None:
        self.set_shotml_settings({"detection_threshold": value}, rerun=True)

    def set_shotml_settings(
        self,
        updates: dict[str, object],
        *,
        rerun: bool = False,
        update_app_defaults: bool = False,
    ) -> None:
        settings = self.project.analysis.shotml_settings
        changed = False
        valid_fields = {item.name: item for item in fields(ShotMLSettings)}
        for key, raw_value in updates.items():
            field_info = valid_fields.get(str(key))
            if field_info is None:
                continue
            current_value = getattr(settings, field_info.name)
            try:
                if isinstance(current_value, bool):
                    next_value = bool(raw_value)
                elif isinstance(current_value, int) and not isinstance(current_value, bool):
                    next_value = int(raw_value)
                elif isinstance(current_value, float):
                    next_value = float(raw_value)
                else:
                    next_value = str(raw_value)
            except (TypeError, ValueError):
                continue
            if current_value != next_value:
                setattr(settings, field_info.name, next_value)
                changed = True

        self.project.analysis.detection_threshold = settings.detection_threshold
        if update_app_defaults:
            persisted_defaults = ShotMLSettings(**asdict(settings))
            persisted_defaults.detection_threshold = ShotMLSettings().detection_threshold
            self.settings.detection_threshold = persisted_defaults.detection_threshold
            self.settings.shotml_defaults = persisted_defaults
            save_settings(self.settings)
            self.settings_changed.emit()
        if rerun and self.project.primary_video.path:
            if changed:
                self.project.analysis.timing_change_proposals = []
            self.analyze_primary()
            for source in self.project.merge_sources:
                if _source_supports_secondary_analysis(source):
                    self.analyze_secondary(source.id)
            return
        if changed:
            self.project.analysis.timing_change_proposals = []
            self._set_status("Updated ShotML settings.")
        else:
            self._set_status("ShotML settings unchanged.")
        self.project.touch()
        self.project_changed.emit()

    def reset_shotml_settings(self) -> None:
        self.project.analysis.shotml_settings = ShotMLSettings()
        self.project.analysis.detection_threshold = (
            self.project.analysis.shotml_settings.detection_threshold
        )
        self.project.analysis.timing_change_proposals = []
        self.settings.detection_threshold = (
            self.project.analysis.shotml_settings.detection_threshold
        )
        self.settings.shotml_defaults = ShotMLSettings()
        save_settings(self.settings)
        self.settings_changed.emit()
        self._set_status("Reset ShotML settings to factory defaults.")
        self.project.touch()
        self.project_changed.emit()

    def rerun_shotml(self) -> None:
        if self.project.primary_video.path:
            self.analyze_primary()
        analyzed_any = False
        for source in self.project.merge_sources:
            if _source_supports_secondary_analysis(source):
                self.analyze_secondary(source.id)
                analyzed_any = True
        if analyzed_any:
            return
        self.project.touch()
        self._set_status("ShotML settings saved.")
        self.project_changed.emit()

    def _review_suggestion_objects(self) -> list[TimingReviewSuggestion]:
        suggestions: list[TimingReviewSuggestion] = []
        for item in self.project.analysis.detection_review_suggestions:
            if not isinstance(item, dict):
                continue
            suggestions.append(
                TimingReviewSuggestion(
                    kind=str(item.get("kind", "")),
                    severity=str(item.get("severity", "review")),
                    message=str(item.get("message", "")),
                    suggested_action=str(item.get("suggested_action", "")),
                    shot_number=None
                    if item.get("shot_number") in {None, ""}
                    else int(item["shot_number"]),
                    shot_time_ms=None
                    if item.get("shot_time_ms") in {None, ""}
                    else int(item["shot_time_ms"]),
                    confidence=None
                    if item.get("confidence") in {None, ""}
                    else float(item["confidence"]),
                    support_confidence=None
                    if item.get("support_confidence") in {None, ""}
                    else float(item["support_confidence"]),
                    interval_ms=None
                    if item.get("interval_ms") in {None, ""}
                    else int(item["interval_ms"]),
                )
            )
        return suggestions

    def generate_timing_change_proposals(self) -> None:
        proposals = timing_change_proposals_from_review_suggestions(
            self.project.analysis.shots,
            self.project.analysis.beep_time_ms_primary,
            self._review_suggestion_objects(),
        )
        existing_restore_ids = {
            proposal.shot_id
            for proposal in self.project.analysis.timing_change_proposals
            if proposal.proposal_type == "restore_shot" and proposal.status == "pending"
        }
        for shot in self.project.analysis.shots:
            original = self._original_shot_state_by_id.get(shot.id)
            if (
                original is None
                or original.time_ms == shot.time_ms
                or shot.id in existing_restore_ids
            ):
                continue
            proposals.append(
                TimingChangeProposal(
                    proposal_type="restore_shot",
                    shot_id=shot.id,
                    shot_number=next(
                        (
                            index + 1
                            for index, candidate in enumerate(
                                sort_shots(self.project.analysis.shots)
                            )
                            if candidate.id == shot.id
                        ),
                        None,
                    ),
                    source_time_ms=shot.time_ms,
                    target_time_ms=original.time_ms,
                    message=f"Restore ShotML's original timestamp for this edited shot ({original.time_ms} ms).",
                    evidence={"original_source": original.source.value},
                )
            )
        self.project.analysis.timing_change_proposals = proposals
        self._set_status(
            f"Generated {len(proposals)} ShotML timing proposal{'s' if len(proposals) != 1 else ''}."
        )
        self.project.touch()
        self.project_changed.emit()

    def _pending_proposal(self, proposal_id: str) -> TimingChangeProposal:
        for proposal in self.project.analysis.timing_change_proposals:
            if proposal.id == proposal_id and proposal.status == "pending":
                return proposal
        raise ValueError("Pending proposal not found")

    def apply_timing_change_proposal(self, proposal_id: str) -> None:
        proposal = self._pending_proposal(proposal_id)
        proposal.status = "applied"
        if proposal.proposal_type == "move_beep":
            if proposal.target_time_ms is None:
                raise ValueError("Proposal target time is required")
            self.project.analysis.beep_time_ms_primary = max(0, int(proposal.target_time_ms))
        elif proposal.proposal_type == "move_shot":
            if proposal.shot_id is None or proposal.target_time_ms is None:
                raise ValueError("Proposal shot and target time are required")
            self.move_shot(proposal.shot_id, int(proposal.target_time_ms))
            return
        elif proposal.proposal_type in {"suppress_shot", "choose_close_pair_survivor"}:
            if proposal.shot_id is None:
                raise ValueError("Proposal shot is required")
            self.delete_shot(proposal.shot_id)
            return
        elif proposal.proposal_type == "restore_shot":
            if proposal.shot_id is None:
                raise ValueError("Proposal shot is required")
            self.restore_original_shot_timing(proposal.shot_id)
            proposal.status = "applied"
            return
        else:
            raise ValueError(f"Unsupported proposal type: {proposal.proposal_type}")
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project)
        self.update_hit_factor()
        self._set_status("Applied ShotML timing proposal.")
        self.project.touch()
        self.project_changed.emit()

    def discard_timing_change_proposal(self, proposal_id: str) -> None:
        proposal = self._pending_proposal(proposal_id)
        proposal.status = "discarded"
        self._set_status("Discarded ShotML timing proposal.")
        self.project.touch()
        self.project_changed.emit()

    def set_beep_time(self, time_ms: int | None) -> None:
        self.project.analysis.beep_time_ms_primary = time_ms
        self.project.touch()
        self.project_changed.emit()

    def add_shot(self, time_ms: int) -> None:
        shot = ShotEvent(
            time_ms=time_ms,
            shotml_time_ms=time_ms,
            source=ShotSource.MANUAL,
            confidence=None,
            score=default_score_mark_for_ruleset(self.project.scoring.ruleset),
            user_added=True,
        )
        self.project.analysis.shots.append(shot)
        self.project.sort_shots()
        self._remember_original_shot(shot)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def move_shot(
        self, shot_id: str, time_ms: int, *, preserve_following_splits: bool = False
    ) -> None:
        if preserve_following_splits:
            shots = sort_shots(self.project.analysis.shots)
            shot_index = next(
                (index for index, shot in enumerate(shots) if shot.id == shot_id), None
            )
            if shot_index is None:
                raise ValueError("Shot not found")
            shot = shots[shot_index]
            if shot.shotml_time_ms is None:
                shot.shotml_time_ms = shot.time_ms
            if shot.shotml_confidence is None:
                original = self._original_shot_state_by_id.get(shot.id)
                shot.shotml_confidence = (
                    original.confidence if original is not None else shot.confidence
                )
            lower_bound_ms = (
                self.project.analysis.beep_time_ms_primary
                if shot_index == 0 and self.project.analysis.beep_time_ms_primary is not None
                else (shots[shot_index - 1].time_ms if shot_index > 0 else 0)
            )
            target_time_ms = max(lower_bound_ms, time_ms)
            delta_ms = target_time_ms - shot.time_ms
            if delta_ms:
                for shifted_shot in shots[shot_index:]:
                    if shifted_shot.shotml_time_ms is None:
                        shifted_shot.shotml_time_ms = shifted_shot.time_ms
                    if shifted_shot.shotml_confidence is None:
                        original = self._original_shot_state_by_id.get(shifted_shot.id)
                        shifted_shot.shotml_confidence = (
                            original.confidence if original is not None else shifted_shot.confidence
                        )
                    shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
        else:
            for shot in self.project.analysis.shots:
                if shot.id == shot_id:
                    if shot.shotml_time_ms is None:
                        shot.shotml_time_ms = shot.time_ms
                    if shot.shotml_confidence is None:
                        original = self._original_shot_state_by_id.get(shot.id)
                        shot.shotml_confidence = (
                            original.confidence if original is not None else shot.confidence
                        )
                    shot.time_ms = max(0, time_ms)
                    if shot.source == ShotSource.AUTO:
                        shot.source = ShotSource.MANUAL
                        shot.confidence = None
                    break
        self.project.sort_shots()
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def delete_shot(self, shot_id: str) -> None:
        selection_context = (
            _shot_selection_context(self.project, shot_id, fallback_mode="index")
            if self.project.ui_state.selected_shot_id == shot_id
            else None
        )
        self.project.analysis.shots = [
            shot for shot in self.project.analysis.shots if shot.id != shot_id
        ]
        self._forget_original_shot(shot_id)
        normalize_project_timing_events(self.project)
        _revalidate_timing_ui_state(self.project, selection_context)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def nudge_shot(self, shot_id: str, delta_ms: int) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                self.move_shot(shot.id, shot.time_ms + delta_ms)
                return

    def select_shot(self, shot_id: str | None) -> None:
        if shot_id is not None and not any(
            shot.id == shot_id for shot in self.project.analysis.shots
        ):
            shot_id = None
        self.project.ui_state.selected_shot_id = shot_id
        self.project_changed.emit()

    def set_ui_state(self, payload: dict[str, object]) -> None:
        ui_state = self.project.ui_state
        changed = False
        valid_shot_ids = {shot.id for shot in self.project.analysis.shots}

        if "selected_shot_id" in payload:
            next_shot_id = (
                None
                if payload.get("selected_shot_id") in {None, ""}
                else str(payload["selected_shot_id"])
            )
            if next_shot_id is not None and next_shot_id not in valid_shot_ids:
                next_shot_id = None
            if ui_state.selected_shot_id != next_shot_id:
                ui_state.selected_shot_id = next_shot_id
                changed = True
        if "timeline_zoom" in payload:
            next_zoom = max(1.0, min(200.0, float(payload["timeline_zoom"])))
            if ui_state.timeline_zoom != next_zoom:
                ui_state.timeline_zoom = next_zoom
                changed = True
        if "timeline_offset_ms" in payload:
            next_offset = max(0, int(payload["timeline_offset_ms"]))
            if ui_state.timeline_offset_ms != next_offset:
                ui_state.timeline_offset_ms = next_offset
                changed = True
        if "active_tool" in payload:
            next_active_tool = str(payload["active_tool"])
            if next_active_tool == "popup":
                next_active_tool = "markers"
            if next_active_tool not in _VALID_BROWSER_UI_TOOLS:
                next_active_tool = "project"
            if ui_state.active_tool != next_active_tool:
                ui_state.active_tool = next_active_tool
                changed = True
        if "waveform_mode" in payload:
            next_waveform_mode = str(payload["waveform_mode"])
            if next_waveform_mode not in _VALID_WAVEFORM_MODES:
                next_waveform_mode = "select"
            if ui_state.waveform_mode != next_waveform_mode:
                ui_state.waveform_mode = next_waveform_mode
                changed = True
        if "waveform_expanded" in payload:
            next_waveform_expanded = bool(payload["waveform_expanded"])
            if ui_state.waveform_expanded != next_waveform_expanded:
                ui_state.waveform_expanded = next_waveform_expanded
                changed = True
            if next_waveform_expanded and ui_state.timing_expanded:
                ui_state.timing_expanded = False
                changed = True
            if next_waveform_expanded and ui_state.metrics_expanded:
                ui_state.metrics_expanded = False
                changed = True
            if next_waveform_expanded and ui_state.scoring_expanded:
                ui_state.scoring_expanded = False
                changed = True
        if "timing_expanded" in payload:
            next_timing_expanded = bool(payload["timing_expanded"])
            if ui_state.timing_expanded != next_timing_expanded:
                ui_state.timing_expanded = next_timing_expanded
                changed = True
            if next_timing_expanded and ui_state.waveform_expanded:
                ui_state.waveform_expanded = False
                changed = True
            if next_timing_expanded and ui_state.metrics_expanded:
                ui_state.metrics_expanded = False
                changed = True
            if next_timing_expanded and ui_state.scoring_expanded:
                ui_state.scoring_expanded = False
                changed = True
        if "timing_enabled" in payload:
            next_timing_enabled = bool(payload["timing_enabled"])
            if ui_state.timing_enabled != next_timing_enabled:
                ui_state.timing_enabled = next_timing_enabled
                changed = True
        if "review_show_markers" in payload:
            next_review_show_markers = bool(payload["review_show_markers"])
            if ui_state.review_show_markers != next_review_show_markers:
                ui_state.review_show_markers = next_review_show_markers
                changed = True
        if "review_show_pip" in payload:
            next_review_show_pip = bool(payload["review_show_pip"])
            if ui_state.review_show_pip != next_review_show_pip:
                ui_state.review_show_pip = next_review_show_pip
                changed = True
        if "metrics_expanded" in payload:
            next_metrics_expanded = bool(payload["metrics_expanded"])
            if ui_state.metrics_expanded != next_metrics_expanded:
                ui_state.metrics_expanded = next_metrics_expanded
                changed = True
            if next_metrics_expanded and ui_state.waveform_expanded:
                ui_state.waveform_expanded = False
                changed = True
            if next_metrics_expanded and ui_state.timing_expanded:
                ui_state.timing_expanded = False
                changed = True
            if next_metrics_expanded and ui_state.scoring_expanded:
                ui_state.scoring_expanded = False
                changed = True
        if "markers_expanded" in payload:
            next_markers_expanded = bool(payload["markers_expanded"])
            if ui_state.markers_expanded != next_markers_expanded:
                ui_state.markers_expanded = next_markers_expanded
                changed = True
        if "scoring_expanded" in payload:
            next_scoring_expanded = bool(payload["scoring_expanded"])
            if ui_state.scoring_expanded != next_scoring_expanded:
                ui_state.scoring_expanded = next_scoring_expanded
                changed = True
            if next_scoring_expanded and ui_state.waveform_expanded:
                ui_state.waveform_expanded = False
                changed = True
            if next_scoring_expanded and ui_state.timing_expanded:
                ui_state.timing_expanded = False
                changed = True
            if next_scoring_expanded and ui_state.metrics_expanded:
                ui_state.metrics_expanded = False
                changed = True
        if "layout_locked" in payload:
            next_layout_locked = bool(payload["layout_locked"])
            if ui_state.layout_locked != next_layout_locked:
                ui_state.layout_locked = next_layout_locked
                changed = True
        for field_name, minimum, maximum in (
            ("rail_width", 84, 104),
            ("inspector_width", 280, 4096),
            ("waveform_height", 112, 4096),
        ):
            if field_name not in payload:
                continue
            next_value = max(minimum, min(maximum, int(payload[field_name])))
            if getattr(ui_state, field_name) != next_value:
                setattr(ui_state, field_name, next_value)
                changed = True
        if "scoring_shot_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("scoring_shot_expansion")
            if isinstance(raw_expansion, dict):
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_shot_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.scoring_shot_expansion != next_expansion:
                ui_state.scoring_shot_expansion = next_expansion
                changed = True
            next_scoring_edit_ids = [
                shot_id for shot_id, expanded in next_expansion.items() if expanded
            ]
            if ui_state.scoring_edit_shot_ids != next_scoring_edit_ids:
                ui_state.scoring_edit_shot_ids = next_scoring_edit_ids
                changed = True
        if "scoring_edit_shot_ids" in payload:
            next_scoring_edit_ids: list[str] = []
            raw_scoring_edit_ids = payload.get("scoring_edit_shot_ids")
            if isinstance(raw_scoring_edit_ids, list):
                for value in raw_scoring_edit_ids:
                    clean_value = str(value).strip()
                    if (
                        clean_value
                        and clean_value in valid_shot_ids
                        and clean_value not in next_scoring_edit_ids
                    ):
                        next_scoring_edit_ids.append(clean_value)
            if ui_state.scoring_edit_shot_ids != next_scoring_edit_ids:
                ui_state.scoring_edit_shot_ids = next_scoring_edit_ids
                changed = True
            next_scoring_shot_expansion = {shot_id: True for shot_id in next_scoring_edit_ids}
            if ui_state.scoring_shot_expansion != next_scoring_shot_expansion:
                ui_state.scoring_shot_expansion = next_scoring_shot_expansion
                changed = True
        if "waveform_shot_amplitudes" in payload:
            next_amplitudes: dict[str, float] = {}
            raw_amplitudes = payload.get("waveform_shot_amplitudes")
            if isinstance(raw_amplitudes, dict):
                for key, value in raw_amplitudes.items():
                    clean_key = str(key).strip()
                    if not clean_key:
                        continue
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        continue
                    next_amplitudes[clean_key] = max(0.25, min(12.0, numeric))
            if ui_state.waveform_shot_amplitudes != next_amplitudes:
                ui_state.waveform_shot_amplitudes = next_amplitudes
                changed = True
        if "timing_edit_shot_ids" in payload:
            next_timing_edit_ids: list[str] = []
            raw_timing_edit_ids = payload.get("timing_edit_shot_ids")
            if isinstance(raw_timing_edit_ids, list):
                for value in raw_timing_edit_ids:
                    clean_value = str(value).strip()
                    if clean_value and clean_value in valid_shot_ids:
                        next_timing_edit_ids.append(clean_value)
            if ui_state.timing_edit_shot_ids != next_timing_edit_ids:
                ui_state.timing_edit_shot_ids = next_timing_edit_ids
                changed = True
        if "timing_column_widths" in payload:
            next_timing_column_widths: dict[str, float] = {}
            raw_timing_column_widths = payload.get("timing_column_widths")
            if isinstance(raw_timing_column_widths, dict):
                minimums = {
                    "lock": 60,
                    "segment": 104,
                    "split": 92,
                    "total": 88,
                    "action": 140,
                    "score": 68,
                    "confidence": 92,
                    "adjustment": 112,
                    "final": 88,
                    "delete": 76,
                    "restore": 88,
                }
                for key, value in raw_timing_column_widths.items():
                    clean_key = str(key).strip()
                    if clean_key not in minimums:
                        continue
                    try:
                        numeric = float(value)
                    except (TypeError, ValueError):
                        continue
                    next_timing_column_widths[clean_key] = max(minimums[clean_key], round(numeric))
            if ui_state.timing_column_widths != next_timing_column_widths:
                ui_state.timing_column_widths = next_timing_column_widths
                changed = True
        if "review_text_box_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("review_text_box_expansion")
            if isinstance(raw_expansion, dict):
                valid_box_ids = {box.id for box in self.project.overlay.text_boxes}
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_box_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.review_text_box_expansion != next_expansion:
                ui_state.review_text_box_expansion = next_expansion
                changed = True
        if "popup_bubble_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("popup_bubble_expansion")
            if isinstance(raw_expansion, dict):
                valid_bubble_ids = {bubble.id for bubble in self.project.popups}
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_bubble_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.popup_bubble_expansion != next_expansion:
                ui_state.popup_bubble_expansion = next_expansion
                changed = True
        if "popup_authoring_collapsed" in payload:
            next_popup_authoring_collapsed = bool(payload["popup_authoring_collapsed"])
            if ui_state.popup_authoring_collapsed != next_popup_authoring_collapsed:
                ui_state.popup_authoring_collapsed = next_popup_authoring_collapsed
                changed = True
        if "merge_source_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("merge_source_expansion")
            if isinstance(raw_expansion, dict):
                valid_source_ids = {source.id for source in self.project.merge_sources}
                valid_source_ids.add("pip-defaults")
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_source_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.merge_source_expansion != next_expansion:
                ui_state.merge_source_expansion = next_expansion
                changed = True
        if "shotml_section_expansion" in payload:
            next_expansion: dict[str, bool] = {}
            raw_expansion = payload.get("shotml_section_expansion")
            if isinstance(raw_expansion, dict):
                valid_section_ids = {
                    "threshold",
                    "beep_detection",
                    "shot_candidate_detection",
                    "shot_refinement",
                    "false_positive_suppression",
                    "confidence_review",
                    "timing_changer",
                    "advanced_runtime",
                }
                for key, value in raw_expansion.items():
                    clean_key = str(key).strip()
                    if clean_key and clean_key in valid_section_ids:
                        next_expansion[clean_key] = bool(value)
            if ui_state.shotml_section_expansion != next_expansion:
                ui_state.shotml_section_expansion = next_expansion
                changed = True

        if changed:
            self.project.touch()
            self.project_changed.emit()

    def assign_score(
        self,
        shot_id: str,
        letter: ScoreLetter | None = None,
        penalty_counts: dict[str, float] | None = None,
    ) -> None:
        normalized_penalty_counts = (
            None
            if penalty_counts is None
            else {
                str(key): max(0.0, float(value))
                for key, value in penalty_counts.items()
                if max(0.0, float(value)) > 0
            }
        )
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = default_score_mark_for_ruleset(self.project.scoring.ruleset)
                elif letter is not None:
                    shot.score.letter = letter
                if normalized_penalty_counts is not None:
                    shot.score.penalty_counts = normalized_penalty_counts
                break
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def restore_original_shot_timing(
        self, shot_id: str, *, preserve_following_splits: bool = False
    ) -> None:
        original = self._original_shot_state_by_id.get(shot_id)
        if original is None:
            raise ValueError("Original split not found")
        shots = sort_shots(self.project.analysis.shots)
        for shot_index, shot in enumerate(shots):
            if shot.id != shot_id:
                continue
            restored_time_ms = max(
                0, shot.shotml_time_ms if shot.shotml_time_ms is not None else original.time_ms
            )
            if preserve_following_splits:
                delta_ms = restored_time_ms - shot.time_ms
                if delta_ms:
                    for shifted_shot in shots[shot_index:]:
                        if shifted_shot.shotml_time_ms is None:
                            shifted_shot.shotml_time_ms = shifted_shot.time_ms
                        if shifted_shot.shotml_confidence is None:
                            original_shifted = self._original_shot_state_by_id.get(shifted_shot.id)
                            shifted_shot.shotml_confidence = (
                                original_shifted.confidence
                                if original_shifted is not None
                                else shifted_shot.confidence
                            )
                        shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
            else:
                shot.time_ms = restored_time_ms
            shot.source = original.source
            shot.confidence = (
                shot.shotml_confidence
                if shot.shotml_confidence is not None
                else original.confidence
            )
            self.project.sort_shots()
            self.update_hit_factor()
            self._set_status("Restored original split.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Shot not found")

    def restore_original_shot_score(self, shot_id: str) -> None:
        original = self._original_shot_state_by_id.get(shot_id)
        if original is None:
            raise ValueError("Original score not found")
        for shot in self.project.analysis.shots:
            if shot.id != shot_id:
                continue
            shot.score = (
                default_score_mark_for_ruleset(self.project.scoring.ruleset)
                if original.score is None
                else deepcopy(original.score)
            )
            self.update_hit_factor()
            self._set_status("Restored original score.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Shot not found")

    def set_scoring_preset(self, ruleset: str) -> None:
        apply_scoring_preset(self.project, ruleset)
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_score_position(self, shot_id: str, x_norm: float, y_norm: float) -> None:
        for shot in self.project.analysis.shots:
            if shot.id == shot_id:
                if shot.score is None:
                    shot.score = ScoreMark()
                shot.score.x_norm = x_norm
                shot.score.y_norm = y_norm
                break
        self.project.touch()
        self.project_changed.emit()

    def set_penalties(self, penalties: float) -> None:
        self.project.scoring.penalties = max(0.0, float(penalties))
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_penalty_counts(self, penalty_counts: dict[str, float]) -> None:
        self.project.scoring.penalty_counts = {
            str(key): max(0.0, float(value)) for key, value in penalty_counts.items()
        }
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_scoring_enabled(self, enabled: bool) -> None:
        self.project.scoring.enabled = enabled
        self.update_hit_factor()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_position(self, position: OverlayPosition) -> None:
        self.project.overlay.position = position
        self.settings.overlay_position = position
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_badge_size(self, size: BadgeSize) -> None:
        self.project.overlay.badge_size = size
        if size != BadgeSize.CUSTOM:
            self.project.overlay.font_size = _badge_font_size_from_enum(size)
        self.settings.badge_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_layout(self, style_type: str, spacing: int, margin: int) -> None:
        self.project.overlay.style_type = (
            style_type if style_type in {"square", "bubble", "rounded"} else "square"
        )
        self.project.overlay.spacing = max(0, min(40, int(spacing)))
        self.project.overlay.margin = max(0, min(40, int(margin)))
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_display_options(self, payload: dict[str, object]) -> None:
        self._set_overlay_display_options(payload, self.project.overlay, cascade=True)

    def set_intro_outro_overlay(self, kind: str, payload: dict[str, object]) -> None:
        normalized_kind = str(kind or "").strip().lower()
        if normalized_kind not in {"intro", "outro"}:
            raise ValueError("Intro/Outro overlay kind must be intro or outro.")
        clip = getattr(self.project, f"{normalized_kind}_clip")
        self._set_overlay_display_options(payload, clip.overlay, cascade=False)

    def set_intro_outro_fades(
        self, kind: str, *, fade_in_s: float, fade_out_s: float
    ) -> None:
        normalized_kind = str(kind or "").strip().lower()
        if normalized_kind not in {"intro", "outro"}:
            raise ValueError("Intro / Outro fade kind must be intro or outro.")
        values = (float(fade_in_s), float(fade_out_s))
        if any(value < 0 or not math.isfinite(value) for value in values):
            raise ValueError("Fade durations must be finite nonnegative seconds.")
        clip = getattr(self.project, f"{normalized_kind}_clip")
        clip.fade_in_s, clip.fade_out_s = values
        self.project.touch()
        self.project_changed.emit()

    def _set_overlay_display_options(
        self,
        payload: dict[str, object],
        overlay: OverlaySettings,
        *,
        cascade: bool,
    ) -> None:
        existing_text_boxes = list(overlay.text_boxes)
        valid_quadrants = {
            "above_final",
            "top_left",
            "top_middle",
            "top_right",
            "middle_left",
            "middle_middle",
            "middle_right",
            "bottom_left",
            "bottom_middle",
            "bottom_right",
        }
        valid_shot_quadrants = {*valid_quadrants, "custom"}
        valid_custom_box_quadrants = {*valid_quadrants, "custom"}
        valid_directions = {"right", "left", "down", "up"}
        valid_custom_box_modes = {"manual", "imported_summary", "match_summary"}
        if "max_visible_shots" in payload:
            overlay.max_visible_shots = max(1, min(40, int(payload["max_visible_shots"])))
        if "shot_quadrant" in payload:
            value = str(payload["shot_quadrant"])
            overlay.shot_quadrant = value if value in valid_shot_quadrants else "bottom_left"
        if "shot_direction" in payload:
            value = str(payload["shot_direction"])
            overlay.shot_direction = value if value in valid_directions else "right"
        if "custom_x" in payload:
            value = payload["custom_x"]
            overlay.custom_x = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_y" in payload:
            value = payload["custom_y"]
            overlay.custom_y = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        for field_name in ("timer_x", "timer_y", "draw_x", "draw_y", "score_x", "score_y"):
            if field_name in payload:
                value = payload[field_name]
                setattr(
                    overlay,
                    field_name,
                    None if value in {"", None} else max(0.0, min(1.0, float(value))),
                )
        if "bubble_width" in payload:
            overlay.bubble_width = max(0, min(400, int(payload["bubble_width"])))
        if "bubble_height" in payload:
            overlay.bubble_height = max(0, min(220, int(payload["bubble_height"])))
        if "font_family" in payload:
            overlay.font_family = str(payload["font_family"])[:80]
        if "font_size" in payload:
            overlay.font_size = max(8, min(72, int(payload["font_size"])))
        if "font_bold" in payload:
            overlay.font_bold = bool(payload["font_bold"])
        if "font_italic" in payload:
            overlay.font_italic = bool(payload["font_italic"])
        for field_name in (
            "show_timer",
            "show_draw",
            "show_shots",
            "show_shot_scores",
            "show_score",
            "timer_lock_to_stack",
            "draw_lock_to_stack",
            "score_lock_to_stack",
        ):
            if field_name in payload:
                setattr(overlay, field_name, bool(payload[field_name]))
        if "custom_box_enabled" in payload:
            overlay.custom_box_enabled = bool(payload["custom_box_enabled"])
        if "custom_box_mode" in payload:
            value = str(payload["custom_box_mode"])
            overlay.custom_box_mode = value if value in valid_custom_box_modes else "manual"
        if "custom_box_text" in payload:
            overlay.custom_box_text = str(payload["custom_box_text"])[:500]
        if "custom_box_quadrant" in payload:
            value = str(payload["custom_box_quadrant"])
            overlay.custom_box_quadrant = (
                value if value in valid_custom_box_quadrants else "top_right"
            )
        if "custom_box_x" in payload:
            value = payload["custom_box_x"]
            overlay.custom_box_x = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if "custom_box_y" in payload:
            value = payload["custom_box_y"]
            overlay.custom_box_y = None if value in {"", None} else max(0.0, min(1.0, float(value)))
        if overlay.custom_box_x is not None or overlay.custom_box_y is not None:
            overlay.custom_box_quadrant = "custom"
        if "custom_box_background_color" in payload:
            overlay.custom_box_background_color = str(payload["custom_box_background_color"])
        if "custom_box_text_color" in payload:
            overlay.custom_box_text_color = str(payload["custom_box_text_color"])
        if "custom_box_opacity" in payload:
            overlay.custom_box_opacity = max(0.0, min(1.0, float(payload["custom_box_opacity"])))
        if "custom_box_width" in payload:
            overlay.custom_box_width = max(0, int(payload["custom_box_width"]))
        if "custom_box_height" in payload:
            overlay.custom_box_height = max(0, int(payload["custom_box_height"]))
        if "text_boxes" in payload:
            parsed_boxes: list[OverlayTextBox] = []
            for item in payload.get("text_boxes", []):
                if not isinstance(item, dict):
                    continue
                source = str(item.get("source", "manual"))
                quadrant = str(item.get("quadrant", "top_right"))
                box = OverlayTextBox(
                    id=str(item.get("id") or OverlayTextBox().id),
                    enabled=bool(item.get("enabled", False)),
                    lock_to_stack=bool(item.get("lock_to_stack", False)),
                    source=source if source in valid_custom_box_modes else "manual",
                    text=str(item.get("text", ""))[:500],
                    quadrant=quadrant if quadrant in valid_custom_box_quadrants else "top_right",
                    x=None if item.get("x") in {None, ""} else max(0.0, min(1.0, float(item["x"]))),
                    y=None if item.get("y") in {None, ""} else max(0.0, min(1.0, float(item["y"]))),
                    background_color=str(
                        item.get("background_color", overlay.custom_box_background_color)
                    ),
                    text_color=str(item.get("text_color", overlay.custom_box_text_color)),
                    opacity=max(
                        0.0, min(1.0, float(item.get("opacity", overlay.custom_box_opacity)))
                    ),
                    width=max(0, int(item.get("width", 0))),
                    height=max(0, int(item.get("height", 0))),
                    summary_metric_ids=[
                        str(value).strip()
                        for value in item.get("summary_metric_ids", [])
                        if str(value).strip()
                    ],
                    style_type=str(
                        item.get("style_type", overlay.style_type) or overlay.style_type
                    ),
                    font_family=str(
                        item.get("font_family", overlay.font_family) or overlay.font_family
                    )[:80],
                    font_size=max(
                        8,
                        min(72, int(item.get("font_size", overlay.font_size) or overlay.font_size)),
                    ),
                    font_bold=bool(item.get("font_bold", overlay.font_bold)),
                    font_italic=bool(item.get("font_italic", overlay.font_italic)),
                )
                if box.x is not None or box.y is not None:
                    box.quadrant = "custom"
                if box.quadrant == "custom":
                    if box.x is None:
                        box.x = 0.5
                    if box.y is None:
                        box.y = 0.5
                if box.source == "imported_summary" and box.text.strip():
                    auto_texts = {
                        format_imported_stage_overlay_text(
                            self.project.scoring.imported_stage
                        ).strip(),
                        format_review_summary_overlay_text(
                            self.project, box.summary_metric_ids
                        ).strip(),
                    }
                    if box.text.strip() in auto_texts:
                        box.text = ""
                parsed_boxes.append(box)
            overlay.text_boxes = parsed_boxes
            sync_overlay_legacy_custom_box_fields(overlay)
        else:
            if existing_text_boxes:
                overlay.text_boxes = existing_text_boxes
            else:
                legacy_box = legacy_custom_box_as_text_box(overlay)
                overlay.text_boxes = [] if legacy_box is None else [legacy_box]
        styles_payload = payload.get("styles")
        if isinstance(styles_payload, dict):
            for badge_name, badge_payload in styles_payload.items():
                normalized_badge_name = str(badge_name or "").strip()
                if normalized_badge_name not in VALID_OVERLAY_BADGE_NAMES:
                    continue
                badge_style = getattr(overlay, normalized_badge_name, None)
                if isinstance(badge_style, BadgeStyle):
                    _badge_style_from_payload(badge_style, badge_payload)
        scoring_colors_payload = payload.get("scoring_colors")
        if isinstance(scoring_colors_payload, dict):
            for score_key, color in scoring_colors_payload.items():
                normalized_score_key = str(score_key or "").strip()
                normalized_color = str(color or "").strip()
                if normalized_score_key and normalized_color:
                    overlay.scoring_colors[normalized_score_key] = normalized_color
        if cascade:
            self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_popups(self, payload: dict[str, object]) -> None:
        parsed_popups: list[PopupBubble] = []
        for item in payload.get("popups", []):
            if not isinstance(item, dict):
                continue
            popup = _popup_bubble_from_dict(item)
            if popup.image_path and self.project_path is not None:
                popup.image_path = copy_path_to_project_subdir(
                    self.project_path,
                    popup.image_path,
                    POPUP_DIRNAME,
                )
            parsed_popups.append(popup)
        self.project.popups = parsed_popups
        template_payload = payload.get("popup_template")
        if isinstance(template_payload, dict):
            _popup_template_from_payload(self.project.popup_template, template_payload)
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_merge_enabled(self, enabled: bool) -> None:
        self.project.merge.enabled = enabled
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_merge_layout(self, layout: MergeLayout) -> None:
        self.project.merge.layout = layout
        self.settings.merge_layout = layout
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size(self, size: PipSize) -> None:
        self.project.merge.pip_size = size
        self.project.merge.pip_size_percent = _pip_size_percent_from_enum(size)
        self.settings.pip_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size_percent(self, percent: int) -> None:
        self.project.merge.pip_size_percent = max(1, min(95, int(percent)))
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_position(self, pip_x: float | None = None, pip_y: float | None = None) -> None:
        if pip_x is not None:
            self.project.merge.pip_x = max(0.0, min(1.0, float(pip_x)))
        if pip_y is not None:
            self.project.merge.pip_y = max(0.0, min(1.0, float(pip_y)))
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def set_merge_source_position(
        self,
        source_id: str,
        pip_size_percent: int | None = None,
        pip_x: float | None = None,
        pip_y: float | None = None,
        opacity: float | None = None,
        camera_role: str | None = None,
        placement_mode: str | None = None,
    ) -> None:
        from splitshot.domain.models import (
            _normalize_merge_source_angle_role,
            _normalize_merge_source_placement_mode,
        )

        for source in self.project.merge_sources:
            if source.id != source_id:
                continue
            if pip_size_percent is not None:
                source.pip_size_percent = max(1, min(95, int(pip_size_percent)))
            if pip_x is not None:
                source.pip_x = max(0.0, min(1.0, float(pip_x)))
            if pip_y is not None:
                source.pip_y = max(0.0, min(1.0, float(pip_y)))
            if opacity is not None:
                source.opacity = max(0.0, min(1.0, float(opacity)))
            if camera_role not in {None, ""}:
                source.angle_role = _normalize_merge_source_angle_role(camera_role, source.asset)
            if placement_mode not in {None, ""}:
                source.placement.mode = _normalize_merge_source_placement_mode(placement_mode)
            self._sync_project_to_active_stage()
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def set_merge_source_sync_offset(self, source_id: str, offset_ms: int) -> None:
        for index, source in enumerate(self.project.merge_sources):
            if source.id != source_id:
                continue
            source.sync_offset_ms = int(offset_ms)
            if _source_supports_secondary_analysis(source):
                entry = _secondary_analysis_entry_for_source(self.project, source_id, create=True)
                if entry is not None:
                    entry.sync_offset_ms = source.sync_offset_ms
                    entry.sync_source = "manual"
                    if entry.analysis_status == "idle":
                        entry.analysis_message = ""
            if self.project.analysis.analyzed_secondary_source_id == source_id or index == 0:
                self.project.analysis.sync_offset_ms = source.sync_offset_ms
                self.project.analysis.secondary_sync_source = "manual"
                _refresh_secondary_analysis_projection(self.project, preferred_source_id=source_id)
            self._set_status(f"Adjusted merge source sync to {source.sync_offset_ms} ms.")
            self._sync_project_to_active_stage()
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def reset_merge_defaults(self) -> None:
        self.project.merge.enabled = False
        _reset_project_merge_defaults(self.project)
        self._cascade_active_presentation_settings()
        self.project.touch()
        self._set_status("Restored PiP defaults.")
        self.project_changed.emit()

    def adjust_merge_source_sync_offset(self, source_id: str, delta_ms: int) -> None:
        for source in self.project.merge_sources:
            if source.id == source_id:
                self.set_merge_source_sync_offset(source_id, source.sync_offset_ms + int(delta_ms))
                return
        raise ValueError("Merge source not found")

    def add_timing_event(
        self,
        kind: str,
        after_shot_id: str | None = None,
        before_shot_id: str | None = None,
        label: str | None = None,
        note: str = "",
    ) -> None:
        from splitshot.domain.models import TimingEvent

        event_label = label or kind.replace("_", " ").title()
        event = TimingEvent(
            kind=kind,
            label=event_label,
            after_shot_id=after_shot_id,
            before_shot_id=before_shot_id,
            note=note,
        )
        normalized_event = normalized_timing_event_for_shots(
            event,
            sort_shots(self.project.analysis.shots),
        )
        if normalized_event is None:
            raise ValueError("Timing event anchor is invalid")
        self.project.analysis.events.append(normalized_event)
        self.project.touch()
        self.project_changed.emit()

    def delete_timing_event(self, event_id: str) -> None:
        remaining_events = [event for event in self.project.analysis.events if event.id != event_id]
        if len(remaining_events) == len(self.project.analysis.events):
            raise ValueError("Timing event not found")
        self.project.analysis.events = remaining_events
        self.project.touch()
        self.project_changed.emit()

    def set_export_quality(self, quality: ExportQuality) -> None:
        self.project.export.quality = quality
        self.settings.export_quality = quality
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def apply_export_preset(self, preset: str) -> None:
        if preset == ExportPreset.CUSTOM.value:
            self.project.export.preset = ExportPreset.CUSTOM
            self._cascade_active_presentation_settings()
            self.project.touch()
            self.project_changed.emit()
            return
        apply_export_preset_settings(self.project, preset)
        self.settings.export_quality = self.project.export.quality
        save_settings(self.settings)
        self.settings_changed.emit()
        self._cascade_active_presentation_settings()
        self.project_changed.emit()

    def set_export_settings(self, payload: dict[str, object]) -> None:
        export = self.project.export
        manual_override_keys = {
            "quality",
            "aspect_ratio",
            "crop_center_x",
            "crop_center_y",
            "target_width",
            "target_height",
            "frame_rate",
            "video_codec",
            "video_bitrate_mbps",
            "audio_codec",
            "audio_sample_rate",
            "audio_bitrate_kbps",
            "color_space",
            "two_pass",
            "multi_track",
            "ffmpeg_preset",
        }
        if "quality" in payload:
            export.quality = ExportQuality(str(payload["quality"]))
            self.settings.export_quality = export.quality
            save_settings(self.settings)
            self.settings_changed.emit()
        if "aspect_ratio" in payload:
            export.aspect_ratio = AspectRatio(str(payload["aspect_ratio"]))
        if "crop_center_x" in payload:
            export.crop_center_x = float(payload["crop_center_x"])
        if "crop_center_y" in payload:
            export.crop_center_y = float(payload["crop_center_y"])
        if "target_width" in payload:
            value = payload["target_width"]
            export.target_width = None if value in {"", None} else max(2, int(value))
        if "target_height" in payload:
            value = payload["target_height"]
            export.target_height = None if value in {"", None} else max(2, int(value))
        if "frame_rate" in payload:
            export.frame_rate = ExportFrameRate(str(payload["frame_rate"]))
        if "video_codec" in payload:
            export.video_codec = ExportVideoCodec(str(payload["video_codec"]))
        if "video_bitrate_mbps" in payload:
            export.video_bitrate_mbps = max(0.1, float(payload["video_bitrate_mbps"]))
        if "audio_codec" in payload:
            export.audio_codec = ExportAudioCodec(str(payload["audio_codec"]))
        if "audio_sample_rate" in payload:
            export.audio_sample_rate = max(8000, int(payload["audio_sample_rate"]))
        if "audio_bitrate_kbps" in payload:
            export.audio_bitrate_kbps = max(32, int(payload["audio_bitrate_kbps"]))
        if "color_space" in payload:
            export.color_space = ExportColorSpace(str(payload["color_space"]))
        if "two_pass" in payload:
            export.two_pass = bool(payload["two_pass"])
        if "multi_track" in payload:
            export.multi_track = bool(payload["multi_track"])
        if "ffmpeg_preset" in payload:
            export.ffmpeg_preset = str(payload["ffmpeg_preset"])
        if "output_path" in payload:
            next_output_path = str(payload["output_path"]).strip()
            if next_output_path:
                export.output_path = next_output_path
                self.project.output_root = str(Path(next_output_path).expanduser().resolve().parent)
            else:
                export.output_path = None
        if manual_override_keys.intersection(payload):
            export.preset = ExportPreset.CUSTOM
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()

    def adjust_sync_offset(self, delta_ms: int) -> None:
        self.project.analysis.sync_offset_ms += delta_ms
        source_id = self.project.analysis.analyzed_secondary_source_id
        if source_id:
            for source in self.project.merge_sources:
                if source.id == source_id:
                    source.sync_offset_ms = self.project.analysis.sync_offset_ms
                    entry = _secondary_analysis_entry_for_source(
                        self.project, source_id, create=True
                    )
                    if entry is not None:
                        entry.sync_offset_ms = source.sync_offset_ms
                        entry.sync_source = "manual"
                    break
        elif self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
        self.project.analysis.secondary_sync_source = "manual"
        _refresh_secondary_analysis_projection(self.project, preferred_source_id=source_id)
        self._set_status(f"Adjusted sync offset to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def set_sync_offset(self, offset_ms: int) -> None:
        self.project.analysis.sync_offset_ms = offset_ms
        source_id = self.project.analysis.analyzed_secondary_source_id
        if source_id:
            for source in self.project.merge_sources:
                if source.id == source_id:
                    source.sync_offset_ms = self.project.analysis.sync_offset_ms
                    entry = _secondary_analysis_entry_for_source(
                        self.project, source_id, create=True
                    )
                    if entry is not None:
                        entry.sync_offset_ms = source.sync_offset_ms
                        entry.sync_source = "manual"
                    break
        elif self.project.merge_sources:
            self.project.merge_sources[0].sync_offset_ms = self.project.analysis.sync_offset_ms
        self.project.analysis.secondary_sync_source = "manual"
        _refresh_secondary_analysis_projection(self.project, preferred_source_id=source_id)
        self._set_status(f"Sync offset set to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def swap_videos(self) -> None:
        if self.project.merge_sources:
            first_source = self.project.merge_sources[0].asset
            first_trim_derivative = deepcopy(self.project.merge_sources[0].trim_derivative)
            self.project.merge_sources[0].asset = self.project.primary_video
            self.project.merge_sources[0].trim_derivative = deepcopy(
                self.project.primary_trim_derivative
            )
            self.project.primary_video = first_source
            self.project.primary_trim_derivative = first_trim_derivative
            _sync_secondary_video_from_merge_sources(self.project)
        elif self.project.secondary_video is None:
            return
        else:
            self.project.primary_video, self.project.secondary_video = (
                self.project.secondary_video,
                self.project.primary_video,
            )
        self.project.analysis.beep_time_ms_primary, self.project.analysis.beep_time_ms_secondary = (
            self.project.analysis.beep_time_ms_secondary,
            self.project.analysis.beep_time_ms_primary,
        )
        analyzed_source = _first_analyzable_merge_source(self.project)
        self.project.analysis.analyzed_secondary_source_id = (
            None if analyzed_source is None else analyzed_source.id
        )
        self.project.analysis.sync_offset_ms *= -1
        if analyzed_source is not None:
            analyzed_source.sync_offset_ms = self.project.analysis.sync_offset_ms
        self._set_status("Swapped primary and secondary videos.")
        self.project.touch()
        self.project_changed.emit()

    def save_project(self, path: str | None = None) -> None:
        previous_project_path = self.project_path
        target_path = Path(path) if path else self.project_path
        if target_path is None:
            raise ValueError("Project path is required")
        self._sync_project_to_active_stage()
        self.project.touch()
        self.project_path = ensure_project_suffix(target_path)
        self.folder_settings = self._load_folder_settings_safe(self.project_path)
        self._stage_existing_practiscore_source_for_project()
        self._ensure_project_output_path(previous_project_path=previous_project_path)
        save_project(self.project, self.project_path)
        self._restore_practiscore_source_from_project()
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self._remember_project(self.project_path)
        self._set_status(f"Project folder ready at {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def open_project(self, path: str) -> None:
        self.project = load_project(path)
        self.project_path = ensure_project_suffix(path)
        self.folder_settings = self._load_folder_settings_safe(self.project_path)
        self._ensure_project_output_path()
        self._reload_output_profiles_cache()
        loaded_snapshot = project_to_dict(self.project)
        recovered_media = self._restore_media_sources_from_project()
        recovered_practiscore = self._restore_practiscore_source_from_project(emit_change=False)
        if recovered_media or recovered_practiscore:
            self.project.touch()
        self._saved_snapshot = (
            loaded_snapshot
            if (recovered_media or recovered_practiscore)
            else project_to_dict(self.project)
        )
        self._remember_original_shots()
        self._remember_project(self.project_path)
        if recovered_media and recovered_practiscore and self._practiscore_source_name:
            self._set_status(
                f"Opened project folder {self.project_path} and restored renamed project media and PractiScore from {self._practiscore_source_name}."
            )
        elif recovered_media:
            self._set_status(
                f"Opened project folder {self.project_path} and restored renamed project media."
            )
        elif recovered_practiscore and self._practiscore_source_name:
            self._set_status(
                f"Opened project folder {self.project_path} and restored PractiScore from {self._practiscore_source_name}."
            )
        else:
            self._set_status(f"Opened project folder {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def delete_current_project(self) -> None:
        if self.project_path is None:
            return
        delete_project(self.project_path)
        self.new_project()
        self._set_status("Deleted the saved project metadata file.")

    def effective_settings(self) -> AppSettings:
        if self.folder_settings is None:
            return AppSettings.from_dict(self.settings.to_dict())
        merged = self.settings.config_dict()
        folder_payload = self.folder_settings.config_dict()
        for key, value in folder_payload.items():
            merged[key] = value
        merged["recent_projects"] = self.settings.recent_projects
        merged["active_template_name"] = self.settings.active_template_name
        merged["settings_templates"] = deepcopy(self.settings.settings_templates)
        return AppSettings.from_dict(merged)

    def settings_layers(self) -> dict[str, object]:
        return {
            "app": self.settings.config_dict(),
            "folder": {} if self.folder_settings is None else self.folder_settings.config_dict(),
            "effective": self.effective_settings().config_dict(),
            "project": {
                "path": "" if self.project_path is None else str(self.project_path),
                "folder_settings_error": self.folder_settings_error or "",
                "popup_template": {
                    "enabled": self.project.popup_template.enabled,
                    "content_type": self.project.popup_template.content_type,
                    "text_source": self.project.popup_template.text_source,
                    "duration_ms": self.project.popup_template.duration_ms,
                    "use_shot_split_duration": self.project.popup_template.use_shot_split_duration,
                    "quadrant": self.project.popup_template.quadrant,
                    "width": self.project.popup_template.width,
                    "height": self.project.popup_template.height,
                    "motion_mode": self.project.popup_template.motion_mode,
                    "follow_motion": self.project.popup_template.follow_motion,
                    "background_color": self.project.popup_template.background_color,
                    "text_color": self.project.popup_template.text_color,
                    "opacity": self.project.popup_template.opacity,
                    "style_type": self.project.popup_template.style_type,
                    "font_family": self.project.popup_template.font_family,
                    "font_size": self.project.popup_template.font_size,
                    "font_bold": self.project.popup_template.font_bold,
                    "font_italic": self.project.popup_template.font_italic,
                },
                "review_text_boxes": _overlay_text_boxes_to_payload(
                    self.project.overlay.text_boxes
                ),
            },
        }

    def set_settings_defaults(self, payload: dict[str, object], *, scope: str = "app") -> None:
        template_action = str(payload.get("template_action") or "").strip().lower()
        if template_action:
            template_name = (
                str(
                    payload.get("template_name") or self.settings.active_template_name or "Default"
                ).strip()
                or "Default"
            )
            if template_action == "select":
                self.select_settings_template(template_name)
                return
            if template_action == "save":
                self.save_settings_template(template_name)
                return
            if template_action == "save_section":
                section = str(payload.get("section") or "").strip().lower()
                if not section:
                    raise ValueError("section is required")
                self.save_settings_template(template_name, section=section)
                return
            if template_action == "duplicate":
                duplicate_name = str(payload.get("duplicate_name") or "").strip()
                if not duplicate_name:
                    raise ValueError("duplicate_name is required")
                self.duplicate_settings_template(template_name, duplicate_name)
                return
            if template_action == "delete":
                self.delete_settings_template(template_name)
                return
        base = (
            self.folder_settings
            if scope == "folder" and self.folder_settings is not None
            else self.settings
        )
        target = AppSettings.from_dict(base.to_dict())
        if "default_match_type" in payload:
            default_match_type = str(payload["default_match_type"] or "").strip().lower()
            if default_match_type:
                try:
                    target.default_match_type = normalize_match_type(default_match_type)
                except ValueError:
                    pass
        if "default_stage_number" in payload:
            raw_stage_number = payload.get("default_stage_number")
            if raw_stage_number in {None, ""}:
                target.default_stage_number = None
            else:
                target.default_stage_number = max(1, int(raw_stage_number))
        if "default_competitor_name" in payload:
            target.default_competitor_name = str(
                payload.get("default_competitor_name", target.default_competitor_name)
                or target.default_competitor_name
            )
        if "default_competitor_place" in payload:
            raw_competitor_place = payload.get("default_competitor_place")
            if raw_competitor_place in {None, ""}:
                target.default_competitor_place = None
            else:
                target.default_competitor_place = int(raw_competitor_place)
        if "overlay_position" in payload:
            target.overlay_position = OverlayPosition(str(payload["overlay_position"]))
        if "timer_badge" in payload:
            _badge_style_from_payload(target.timer_badge, payload.get("timer_badge"))
        if "shot_badge" in payload:
            _badge_style_from_payload(target.shot_badge, payload.get("shot_badge"))
        if "current_shot_badge" in payload:
            _badge_style_from_payload(target.current_shot_badge, payload.get("current_shot_badge"))
        if "hit_factor_badge" in payload:
            _badge_style_from_payload(target.hit_factor_badge, payload.get("hit_factor_badge"))
        if "overlay_custom_box_background_color" in payload:
            target.overlay_custom_box_background_color = str(
                payload.get(
                    "overlay_custom_box_background_color",
                    target.overlay_custom_box_background_color,
                )
                or target.overlay_custom_box_background_color
            )
        if "overlay_custom_box_text_color" in payload:
            target.overlay_custom_box_text_color = str(
                payload.get("overlay_custom_box_text_color", target.overlay_custom_box_text_color)
                or target.overlay_custom_box_text_color
            )
        if "overlay_custom_box_opacity" in payload:
            raw_opacity = payload.get("overlay_custom_box_opacity")
            if raw_opacity not in {None, ""}:
                target.overlay_custom_box_opacity = max(0.0, min(1.0, float(raw_opacity)))
        if "badge_size" in payload:
            target.badge_size = BadgeSize(str(payload["badge_size"]))
        if "merge_layout" in payload:
            target.merge_layout = MergeLayout(str(payload["merge_layout"]))
        if "merge_pip_x" in payload:
            raw_pip_x = payload.get("merge_pip_x")
            if raw_pip_x not in {None, ""}:
                target.merge_pip_x = float(raw_pip_x)
        if "merge_pip_y" in payload:
            raw_pip_y = payload.get("merge_pip_y")
            if raw_pip_y not in {None, ""}:
                target.merge_pip_y = float(raw_pip_y)
        if "pip_size" in payload:
            target.pip_size = PipSize(str(payload["pip_size"]))
        if "merge_source_defaults" in payload:
            target.merge_source_defaults = [
                deepcopy(item)
                for item in payload.get("merge_source_defaults", [])
                if isinstance(item, dict)
            ]
        if "export_quality" in payload:
            target.export_quality = ExportQuality(str(payload["export_quality"]))
        if "export_preset" in payload:
            target.export_preset = ExportPreset(str(payload["export_preset"]))
        if "export_frame_rate" in payload:
            target.export_frame_rate = ExportFrameRate(str(payload["export_frame_rate"]))
        if "export_video_codec" in payload:
            target.export_video_codec = ExportVideoCodec(str(payload["export_video_codec"]))
        if "export_audio_codec" in payload:
            target.export_audio_codec = ExportAudioCodec(str(payload["export_audio_codec"]))
        if "export_color_space" in payload:
            target.export_color_space = ExportColorSpace(str(payload["export_color_space"]))
        if "export_two_pass" in payload:
            target.export_two_pass = bool(payload["export_two_pass"])
        if "export_ffmpeg_preset" in payload:
            target.export_ffmpeg_preset = str(payload["export_ffmpeg_preset"] or "medium")
        if "default_tool" in payload:
            target.default_tool = str(payload["default_tool"] or "project")
        if "reopen_last_tool" in payload:
            target.reopen_last_tool = bool(payload["reopen_last_tool"])
        if bool(payload.get("clear_layout_defaults", False)):
            target.layout_locked = None
            target.layout_rail_width = None
            target.layout_inspector_width = None
            target.layout_waveform_height = None
        else:
            if "layout_locked" in payload:
                target.layout_locked = _optional_payload_bool(payload.get("layout_locked"))
            if "layout_rail_width" in payload:
                target.layout_rail_width = _optional_layout_dimension(
                    payload.get("layout_rail_width"), 84, 104
                )
            if "layout_inspector_width" in payload:
                target.layout_inspector_width = _optional_layout_dimension(
                    payload.get("layout_inspector_width"), 280, 4096
                )
            if "layout_waveform_height" in payload:
                target.layout_waveform_height = _optional_layout_dimension(
                    payload.get("layout_waveform_height"), 112, 4096
                )
        if "detection_threshold" in payload:
            threshold = float(payload["detection_threshold"])
            target.detection_threshold = threshold
            target.shotml_defaults.detection_threshold = threshold
        marker_template_payload = payload.get("marker_template")
        if isinstance(marker_template_payload, dict):
            _popup_template_from_payload(target.marker_template, marker_template_payload)
        if scope == "folder":
            if self.project_path is None:
                raise ValueError("Save the project before writing folder defaults.")
            self.folder_settings = target
            self.folder_settings_error = None
            save_folder_settings(self.project_path, target)
        else:
            target.recent_projects = self.settings.recent_projects
            target.active_template_name = self.settings.active_template_name
            target.settings_templates = deepcopy(self.settings.settings_templates)
            self.settings = target
            self._sync_active_settings_template()
            save_settings(self.settings)
        self.settings_changed.emit()
        self._set_status(f"Updated {'folder' if scope == 'folder' else 'app'} defaults.")

    def reset_settings_defaults(self, *, scope: str = "app", section: str | None = None) -> None:
        if not section:
            self.restore_defaults()
            return

        section_name = str(section or "").strip().lower()
        base = (
            self.folder_settings
            if scope == "folder" and self.folder_settings is not None
            else self.settings
        )
        target = AppSettings.from_dict(base.to_dict())
        fallback = self.settings if scope == "folder" else AppSettings()

        def rebuild_with_updates(updates: dict[str, object]) -> None:
            nonlocal target
            payload = target.to_dict()
            payload.update({key: deepcopy(value) for key, value in updates.items()})
            refreshed = AppSettings.from_dict(payload)
            refreshed.active_template_name = target.active_template_name
            refreshed.settings_templates = deepcopy(target.settings_templates)
            refreshed.recent_projects = target.recent_projects
            target = refreshed

        fallback_config = fallback.config_dict()
        section_keys = {
            "global-template": ("default_tool", "reopen_last_tool"),
            "layout": (
                "layout_locked",
                "layout_rail_width",
                "layout_inspector_width",
                "layout_waveform_height",
            ),
            "scoring": (
                "default_match_type",
                "default_stage_number",
                "default_competitor_name",
                "default_competitor_place",
            ),
            "pip": (
                "merge_layout",
                "pip_size",
                "merge_pip_x",
                "merge_pip_y",
                "merge_source_defaults",
            ),
            "overlay": (
                "overlay_position",
                "badge_size",
                "overlay_custom_box_background_color",
                "overlay_custom_box_text_color",
                "overlay_custom_box_opacity",
                "timer_badge",
                "shot_badge",
                "current_shot_badge",
                "hit_factor_badge",
                "review_text_boxes",
            ),
            "markers": ("marker_template",),
            "export": (
                "export_quality",
                "export_preset",
                "export_frame_rate",
                "export_video_codec",
                "export_audio_codec",
                "export_color_space",
                "export_two_pass",
                "export_ffmpeg_preset",
            ),
            "shotml": ("detection_threshold", "shotml_defaults"),
        }
        keys = section_keys.get(section_name)
        if keys is None:
            raise ValueError("Unknown settings section.")
        rebuild_with_updates({key: fallback_config.get(key) for key in keys})

        if scope == "folder":
            if self.project_path is None:
                raise ValueError("Save the project before writing folder defaults.")
            if target.config_dict() == self.settings.config_dict():
                delete_folder_settings(self.project_path)
                self.folder_settings = None
            else:
                self.folder_settings = target
                save_folder_settings(self.project_path, target)
            self.folder_settings_error = None
        else:
            target.recent_projects = self.settings.recent_projects
            target.active_template_name = self.settings.active_template_name
            target.settings_templates = deepcopy(self.settings.settings_templates)
            self.settings = target
            self._sync_active_settings_template()
            save_settings(self.settings)
        self.settings_changed.emit()
        self._set_status(
            f"Reset {section_name} defaults for {'folder' if scope == 'folder' else 'app'} scope."
        )

    def restore_defaults(self) -> None:
        self.settings = AppSettings()
        self.settings.settings_templates = {
            self.settings.active_template_name: self.settings.template_snapshot()
        }
        save_settings(self.settings)
        delete_folder_settings(self.project_path)
        self.folder_settings = None
        self.folder_settings_error = None
        self._apply_effective_settings_to_project(
            self.project, self.effective_settings(), reset_tool=False
        )
        self.project.touch()
        self._set_status("Restored SplitShot defaults.")
        self.settings_changed.emit()
        self.project_changed.emit()

    def update_hit_factor(self) -> None:
        self.project.sort_shots()
        self.project.scoring.hit_factor = calculate_hit_factor(self.project)

    def _remember_original_shots(self) -> None:
        self._original_shot_state_by_id = {
            shot.id: _OriginalShotState(
                time_ms=shot.shotml_time_ms if shot.shotml_time_ms is not None else shot.time_ms,
                source=shot.source,
                confidence=shot.shotml_confidence
                if shot.shotml_confidence is not None
                else shot.confidence,
                score=None if shot.score is None else deepcopy(shot.score),
            )
            for shot in self.project.analysis.shots
        }

    def _remember_original_shot(self, shot: ShotEvent) -> None:
        self._original_shot_state_by_id[shot.id] = _OriginalShotState(
            time_ms=shot.shotml_time_ms if shot.shotml_time_ms is not None else shot.time_ms,
            source=shot.source,
            confidence=shot.shotml_confidence
            if shot.shotml_confidence is not None
            else shot.confidence,
            score=None if shot.score is None else deepcopy(shot.score),
        )

    def _forget_original_shot(self, shot_id: str) -> None:
        self._original_shot_state_by_id.pop(shot_id, None)

    def _remember_project(self, path: Path) -> None:
        entries = [
            str(path),
            *[item for item in self.settings.recent_projects if item != str(path)],
        ]
        next_entries = entries[:10]
        if self.settings.recent_projects == next_entries:
            return
        self.settings.recent_projects = next_entries
        save_settings(self.settings)
        self.settings_changed.emit()

    def _autosave_project_if_needed(self) -> None:
        if self._autosave_in_progress or self.project_path is None:
            return
        self._sync_project_to_active_stage()
        current_snapshot = project_to_dict(self.project)
        if current_snapshot == self._saved_snapshot:
            return
        try:
            self._autosave_in_progress = True
            save_project(self.project, self.project_path)
            if self.project.scoring.practiscore_source_path:
                self._restore_practiscore_source_from_project()
            self._saved_snapshot = project_to_dict(self.project)
            self._remember_project(self.project_path)
        except Exception as exc:  # noqa: BLE001
            self._set_status(f"Project autosave failed: {exc}")
        finally:
            self._autosave_in_progress = False

    def autosave_project_if_needed(self) -> None:
        self._autosave_project_if_needed()

    def _profiles_path(self) -> Path | None:
        if self.project_path is None:
            return None
        return self.project_path / "profiles.json"

    def _load_output_profiles(self) -> list[OutputProfile]:
        profiles_path = self._profiles_path()
        if profiles_path is None or not profiles_path.exists():
            return []
        try:
            raw = profiles_path.read_text(encoding="utf-8")
            return _deserialize_output_profiles(raw)
        except (OSError, ValueError):
            return []

    def _sync_output_profiles_to_disk(self) -> None:
        profiles_path = self._profiles_path()
        if profiles_path is None:
            return
        try:
            raw = _serialize_output_profiles(self._output_profiles)
            profiles_path.write_text(raw, encoding="utf-8")
        except OSError:
            pass

    def _reload_output_profiles_cache(self) -> None:
        self._output_profiles = self._load_output_profiles()
        self._output_profiles_cache_dirty = False

    def list_output_profiles(self) -> list[dict[str, Any]]:
        from splitshot.domain.models import output_profile_to_dict

        return [output_profile_to_dict(p) for p in self._output_profiles]

    def create_output_profile(
        self,
        profile_name: str,
        profile_kind: str = "stage_output",
        export_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        from splitshot.domain.models import OutputProfileKind, output_profile_to_dict

        kind = (
            OutputProfileKind(profile_kind.strip().lower())
            if profile_kind.strip().lower() in {"stage_output", "stage_composite"}
            else OutputProfileKind.STAGE_OUTPUT
        )
        profile = OutputProfile(
            scope_type="stage",
            scope_id=Path(self.project_path or "").name,
            profile_name=profile_name or "New Profile",
            profile_kind=kind,
            export_settings=_normalize_output_profile_export_settings(
                export_settings if export_settings is not None else asdict(self.project.export)
            ),
        )
        self._output_profiles.append(profile)
        self._sync_output_profiles_to_disk()
        return output_profile_to_dict(profile)

    def update_output_profile(self, output_id: str, **updates: Any) -> dict[str, Any] | None:
        from splitshot.domain.models import output_profile_to_dict

        profile = next((p for p in self._output_profiles if p.output_id == output_id), None)
        if profile is None:
            return None
        for key, value in updates.items():
            if value is None:
                continue
            if key == "profile_name":
                profile.profile_name = str(value)
            elif key == "profile_kind":
                normalized = str(value).strip().lower()
                if normalized in {"stage_output", "stage_composite"}:
                    profile.profile_kind = OutputProfileKind(normalized)
            elif key == "frame_profile":
                profile.frame_profile = _normalize_frame_profile(str(value))
            elif key == "metric_caption_preset":
                profile.metric_caption_preset = str(value)
            elif key == "lead_in_card":
                profile.lead_in_card = str(value)
            elif key == "brand_mark":
                profile.brand_mark = str(value)
            elif key == "visibility_recipe":
                profile.visibility_recipe = str(value)
            elif key == "review_source_id":
                profile.review_source_id = str(value)
            elif key == "last_rendered_at":
                profile.last_rendered_at = str(value)
            elif key == "export_settings":
                profile.export_settings = _normalize_output_profile_export_settings(value)
        self._sync_output_profiles_to_disk()
        return output_profile_to_dict(profile)

    def apply_output_profile(self, output_id: str) -> dict[str, Any]:
        from splitshot.domain.models import output_profile_to_dict

        profile = next((p for p in self._output_profiles if p.output_id == output_id), None)
        if profile is None:
            raise ValueError(f"Output profile {output_id} not found")
        if profile.export_settings:
            self.set_export_settings(profile.export_settings)
            preset = profile.export_settings.get("preset")
            if preset is not None:
                self.project.export.preset = ExportPreset(str(preset))
        frame_aspect = {
            "16:9": AspectRatio.LANDSCAPE,
            "9:16": AspectRatio.PORTRAIT,
            "1:1": AspectRatio.SQUARE,
            "4:5": AspectRatio.PORTRAIT_45,
        }.get(profile.frame_profile)
        if frame_aspect is not None:
            self.project.export.aspect_ratio = frame_aspect
        self._cascade_active_presentation_settings()
        self.project.touch()
        self.project_changed.emit()
        self._set_status(f"Applied output profile {profile.profile_name}.")
        return output_profile_to_dict(profile)

    def delete_output_profile(self, output_id: str) -> bool:
        profile = next((p for p in self._output_profiles if p.output_id == output_id), None)
        if profile is None:
            return False
        self._output_profiles.remove(profile)
        self._sync_output_profiles_to_disk()
        return True

    def render_output_profile(self, output_id: str) -> dict[str, Any]:
        from splitshot.domain.models import output_profile_to_dict

        profile = next((p for p in self._output_profiles if p.output_id == output_id), None)
        if profile is None:
            raise ValueError(f"Output profile {output_id} not found")
        return {"profile": output_profile_to_dict(profile), "status": "render_planned"}

    def _stage_project_input_path(self, path: str, source_name: str | None = None) -> str:
        if self.project_path is None:
            return path
        return copy_path_to_project_subdir(
            self.project_path,
            path,
            INPUT_DIRNAME,
            preferred_name=source_name,
        )

    def _stage_practiscore_source_path(self, path: str, source_name: str | None = None) -> str:
        if self.project_path is None:
            return path
        return copy_path_to_project_subdir(
            self.project_path,
            path,
            PRACTISCORE_DIRNAME,
            preferred_name=source_name,
        )

    def _stage_existing_practiscore_source_for_project(self) -> None:
        source_path = self._practiscore_source_path
        if source_path is None:
            stored_path = self.project.scoring.practiscore_source_path.strip()
            if not stored_path:
                return
            source_path = Path(stored_path)
        if not source_path.is_file():
            return

        source_name = self._practiscore_source_name or source_path.name
        staged_path = Path(
            self._stage_practiscore_source_path(
                str(source_path),
                source_name=source_name,
            )
        )
        staged_value = str(staged_path)
        self._practiscore_source_path = staged_path
        self.project.practiscore_source_file = staged_value

        scoring_states = [
            self.project.scoring,
            *(stage.scoring for stage in self.project.stages),
        ]
        for scoring in scoring_states:
            scoring.practiscore_source_path = staged_value
            scoring.practiscore_source_name = source_name
            if scoring.imported_stage is not None:
                scoring.imported_stage.source_path = staged_value
                scoring.imported_stage.source_name = source_name

    def project_folder_has_project_file(self, path: str | Path) -> bool:
        return project_has_metadata(normalize_project_path(path))

    def normalize_project_folder_path(self, path: str | Path) -> Path:
        return normalize_project_path(path)

    def _new_project_with_settings_defaults(self) -> Project:
        effective = self.effective_settings()
        project = Project()
        self._apply_effective_settings_to_project(project, effective, reset_tool=True)
        return project

    def _apply_effective_settings_to_project(
        self, project: Project, effective: AppSettings, *, reset_tool: bool
    ) -> None:
        project.analysis.shotml_settings = ShotMLSettings(**asdict(effective.shotml_defaults))
        project.analysis.detection_threshold = project.analysis.shotml_settings.detection_threshold
        project.scoring.match_type = ""
        try:
            normalized_match_type = normalize_match_type(effective.default_match_type)
        except ValueError:
            normalized_match_type = ""
        if normalized_match_type:
            project.scoring.match_type = normalized_match_type
            apply_scoring_preset(project, default_ruleset_for_match_type(normalized_match_type))
        project.scoring.stage_number = effective.default_stage_number
        project.scoring.competitor_name = effective.default_competitor_name
        project.scoring.competitor_place = effective.default_competitor_place
        project.overlay.position = effective.overlay_position
        project.overlay.badge_size = effective.badge_size
        if effective.badge_size != BadgeSize.CUSTOM:
            project.overlay.font_size = _badge_font_size_from_enum(effective.badge_size)
        project.overlay.timer_badge = deepcopy(effective.timer_badge)
        project.overlay.shot_badge = deepcopy(effective.shot_badge)
        project.overlay.current_shot_badge = deepcopy(effective.current_shot_badge)
        project.overlay.hit_factor_badge = deepcopy(effective.hit_factor_badge)
        project.overlay.custom_box_background_color = effective.overlay_custom_box_background_color
        project.overlay.custom_box_text_color = effective.overlay_custom_box_text_color
        project.overlay.custom_box_opacity = effective.overlay_custom_box_opacity
        project.merge.layout = effective.merge_layout
        project.merge.pip_size = effective.pip_size
        project.merge.pip_size_percent = _pip_size_percent_from_enum(effective.pip_size)
        project.merge.pip_x = effective.merge_pip_x
        project.merge.pip_y = effective.merge_pip_y
        project.merge_sources = [
            _merge_source_from_dict(item)
            for item in effective.merge_source_defaults
            if isinstance(item, dict)
        ]
        _sync_secondary_video_from_merge_sources(project)
        analyzed_source = _first_analyzable_merge_source(project)
        if analyzed_source is not None:
            project.analysis.analyzed_secondary_source_id = analyzed_source.id
            project.analysis.sync_offset_ms = int(analyzed_source.sync_offset_ms)
        project.export.quality = effective.export_quality
        project.export.preset = effective.export_preset
        project.export.frame_rate = effective.export_frame_rate
        project.export.video_codec = effective.export_video_codec
        project.export.audio_codec = effective.export_audio_codec
        project.export.color_space = effective.export_color_space
        project.export.two_pass = effective.export_two_pass
        project.export.ffmpeg_preset = effective.export_ffmpeg_preset
        project.popup_template = deepcopy(effective.marker_template)
        project.overlay.text_boxes = [
            OverlayTextBox(**box) for box in effective.review_text_boxes if isinstance(box, dict)
        ]
        if effective.layout_locked is not None:
            project.ui_state.layout_locked = bool(effective.layout_locked)
        if effective.layout_rail_width is not None:
            project.ui_state.rail_width = max(84, min(104, int(effective.layout_rail_width)))
        if effective.layout_inspector_width is not None:
            project.ui_state.inspector_width = max(
                320, min(4096, int(effective.layout_inspector_width))
            )
        if effective.layout_waveform_height is not None:
            project.ui_state.waveform_height = max(
                112, min(4096, int(effective.layout_waveform_height))
            )
        if reset_tool:
            project.ui_state.active_tool = (
                effective.default_tool if effective.reopen_last_tool else "project"
            )

    def _load_folder_settings_safe(self, project_path: str | Path | None) -> AppSettings | None:
        self.folder_settings_error = None
        try:
            return load_folder_settings(project_path)
        except Exception as exc:  # noqa: BLE001
            self.folder_settings_error = f"Folder defaults were ignored: {exc}"
            return None

    def _ensure_project_output_path(self, previous_project_path: Path | None = None) -> None:
        if self.project_path is None:
            return
        current_output_root = str(self.project.output_root or "").strip()
        project_output_root = str(default_project_output_path(self.project_path).parent)
        previous_output_root = (
            str(default_project_output_path(previous_project_path).parent)
            if previous_project_path is not None
            else ""
        )
        if not current_output_root or (
            previous_output_root and current_output_root == previous_output_root
        ):
            self.project.output_root = project_output_root
        current_output_path = str(self.project.export.output_path or "").strip()
        expected_output_path = str(Path(self.project.output_root) / "output.mp4")
        if not current_output_path or (
            previous_output_root
            and current_output_path == str(Path(previous_output_root) / "output.mp4")
        ):
            self.project.export.output_path = expected_output_path

    def _ensure_output_dir(self) -> Path:
        if self.project_path is None:
            raise ValueError("Project path is required before exporting.")
        output_root = str(self.project.output_root or "").strip()
        output_dir = (
            Path(output_root)
            if output_root
            else default_project_output_path(self.project_path).parent
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        self.project.output_root = str(output_dir)
        return output_dir

    def output_dir(self) -> Path:
        return self._ensure_output_dir()

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_changed.emit(message)
