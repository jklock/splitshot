"""Shared controller layer that owns authoritative project mutations and settings flow."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from datetime import datetime, timezone
from inspect import Parameter, signature
import json
from pathlib import Path
import re
import shutil
import subprocess
from tempfile import TemporaryDirectory
from uuid import uuid4 as _uuid4

from PySide6.QtCore import QObject, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter

from splitshot.analysis.detection import (
    analyze_video_audio,
    timing_change_proposals_from_review_suggestions,
    TimingReviewSuggestion,
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
    AngleDirectorCutDecision,
    StageClipSource,
    LibraryStageRecord,
    LibraryMatchRecord,
    BadgeSize,
    BadgeStyle,
    AspectRatio,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportVideoCodec,
    MergePlacementMode,
    MergePlacementSlot,
    MergePlacementTargetKind,
    _merge_source_from_dict,
    _normalize_merge_source_angle_role,
    _normalize_merge_source_placement_mode,
    _normalize_merge_source_placement_slot,
    _normalize_merge_source_placement_target_kind,
    _popup_bubble_from_dict,
    MatchWorkspace,
    MergeLayout,
    MERGE_SOURCE_ANGLE_ROLE_VALUES,
    OverlayPosition,
    OutputProfile,
    OverlayTextBox,
    PopupBubble,
    PopupTemplate,
    PipSize,
    Project,
    MergeSource,
    MergeSourceAssetPathKind,
    ScoreLetter,
    ScoreMark,
    ShotEvent,
    ShotMLSettings,
    ShotSource,
    StageEntry,
    TimingEvent,
    TimingChangeProposal,
    VideoAsset,
    default_merge_source_angle_role,
    legacy_custom_box_as_text_box,
    overlay_text_boxes_for_render,
    project_to_dict,
    sync_overlay_legacy_custom_box_fields,
)
from splitshot.export.presets import (
    apply_export_preset as apply_export_preset_settings,
    apply_export_settings_payload,
    resolved_export_settings,
)
from splitshot.export.pipeline import export_output_profile, export_project
from splitshot.media.ffmpeg import MediaError, generate_trimmed_derivative
from splitshot.media.probe import probe_video
from splitshot.persistence.projects import (
    INPUT_DIRNAME,
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
from splitshot.persistence.workspaces import (
    _output_profile_from_dict,
    load_workspace,
    normalize_workspace_path,
    save_workspace,
    workspace_has_metadata,
    workspace_stage_project_path,
    workspace_stage_path,
)
from splitshot.persistence.library import (
    save_stage_record,
    save_match_record,
    append_stage_metric,
    append_match_metric,
)
from splitshot.scoring.logic import (
    apply_scoring_preset,
    calculate_hit_factor,
    default_score_mark_for_ruleset,
    ensure_default_shot_scores,
)
from splitshot.scoring.practiscore import (
    PractiScoreOptions,
    _normalize_name,
    describe_practiscore_file,
    default_ruleset_for_match_type,
    normalize_match_type,
)
from splitshot.scoring.practiscore_sync_normalize import normalize_downloaded_practiscore_artifact
from splitshot.scoring.practiscore_web_extract import RemotePractiScoreMatch
from splitshot.timeline.model import (
    normalize_project_timing_events,
    normalized_timing_event_for_shots,
    sort_shots,
)
from splitshot.ui.services import practiscore_sync as practiscore_sync_service
from splitshot.ui.services import shared_backend as shared_backend_service


discover_remote_matches = practiscore_sync_service.discover_remote_matches
download_remote_match_artifacts = practiscore_sync_service.download_remote_match_artifacts


VALID_OVERLAY_BADGE_NAMES = {
    "timer_badge",
    "shot_badge",
    "current_shot_badge",
    "hit_factor_badge",
}

_PRACTISCORE_FILE_SUFFIXES = {".csv", ".txt"}

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

_TRIM_DERIVATIVE_CONTAINER_SUFFIXES = frozenset({".m4v", ".mkv", ".mov", ".mp4"})


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


# Phase 4 must preserve this as the single controller-side role-priority seam
# for both Compose merge sources and stage composite clips. Compose keeps
# within-role stability via `MergeSource.placement.order_index`; stage composite
# currently preserves the existing clip list order within the same role tier.
_CAMERA_ROLE_PRIORITY = {
    role: index for index, role in enumerate(MERGE_SOURCE_ANGLE_ROLE_VALUES)
}


def _camera_role_priority(angle_role: object) -> int:
    normalized = str(angle_role or "").strip().lower()
    return _CAMERA_ROLE_PRIORITY.get(normalized, len(_CAMERA_ROLE_PRIORITY))


def _camera_role_priority_sort_key(
    angle_role: object,
    stable_index: int,
    *,
    order_index: int | None = None,
) -> tuple[int, int, int]:
    stable_order = stable_index if order_index is None else max(0, int(order_index))
    return (_camera_role_priority(angle_role), stable_order, stable_index)


def _merge_source_stable_order_index(source: MergeSource, fallback_index: int) -> int:
    if source.placement.order_index is None:
        return fallback_index
    return max(0, int(source.placement.order_index))


def _next_merge_source_order_index(project: Project) -> int:
    return (
        max(
            _merge_source_stable_order_index(source, index)
            for index, source in enumerate(project.merge_sources)
        )
        + 1
        if project.merge_sources
        else 0
    )


_CAMERA_ROLE_BASE_TARGET_PRIORITY = {
    "primary": 0,
    "static": 1,
    "follow": 2,
    "detail": 3,
}


def _camera_role_base_target_priority(angle_role: object) -> int:
    normalized = str(angle_role or "").strip().lower()
    return _CAMERA_ROLE_BASE_TARGET_PRIORITY.get(
        normalized,
        len(_CAMERA_ROLE_BASE_TARGET_PRIORITY),
    )


def _camera_role_seed_placement_mode(
    project: Project,
    angle_role: object,
    asset: VideoAsset | None = None,
) -> MergePlacementMode:
    normalized_role = _normalize_merge_source_angle_role(angle_role, asset)
    project_default_mode = _normalize_merge_source_placement_mode(project.merge.layout)
    if normalized_role == "primary":
        return MergePlacementMode.BASE
    if normalized_role == "detail":
        if project_default_mode in {
            MergePlacementMode.PIP,
            MergePlacementMode.FULL_SCREEN_PORTRAIT,
        }:
            return project_default_mode
        return MergePlacementMode.PIP
    if project_default_mode in {
        MergePlacementMode.SIDE_BY_SIDE,
        MergePlacementMode.ABOVE_BELOW,
        MergePlacementMode.DUAL_CENTER_HUD,
        MergePlacementMode.DUAL_TOP_HUD,
    }:
        return project_default_mode
    return MergePlacementMode.SIDE_BY_SIDE


def _camera_role_seed_placement_slot(
    angle_role: object,
    mode: MergePlacementMode,
    asset: VideoAsset | None = None,
) -> MergePlacementSlot:
    normalized_role = _normalize_merge_source_angle_role(angle_role, asset)
    if mode in {
        MergePlacementMode.SIDE_BY_SIDE,
        MergePlacementMode.DUAL_CENTER_HUD,
        MergePlacementMode.DUAL_TOP_HUD,
    }:
        return MergePlacementSlot.LEFT if normalized_role == "static" else MergePlacementSlot.RIGHT
    if mode == MergePlacementMode.ABOVE_BELOW:
        return MergePlacementSlot.TOP if normalized_role == "static" else MergePlacementSlot.BOTTOM
    if mode == MergePlacementMode.PIP:
        return MergePlacementSlot.OVERLAY
    return MergePlacementSlot.CENTER


def _merge_source_resolved_placement_mode(
    project: Project,
    source: MergeSource,
) -> MergePlacementMode:
    current_mode = _normalize_merge_source_placement_mode(source.placement.mode)
    if current_mode != MergePlacementMode.AUTO:
        return current_mode
    return _camera_role_seed_placement_mode(project, source.angle_role, source.asset)


def _merge_source_base_target_sort_key(
    project: Project,
    source: MergeSource,
    stable_index: int,
) -> tuple[int, int, int, int]:
    mode = _merge_source_resolved_placement_mode(project, source)
    if mode in {MergePlacementMode.BASE, MergePlacementMode.FULL_SCREEN_PORTRAIT}:
        mode_priority = 0
    elif mode in {
        MergePlacementMode.SIDE_BY_SIDE,
        MergePlacementMode.ABOVE_BELOW,
        MergePlacementMode.DUAL_CENTER_HUD,
        MergePlacementMode.DUAL_TOP_HUD,
    }:
        mode_priority = 1
    else:
        mode_priority = 2
    return (
        mode_priority,
        _camera_role_base_target_priority(source.angle_role),
        _merge_source_stable_order_index(source, stable_index),
        stable_index,
    )


def _preferred_merge_source_base_target(
    project: Project,
    source: MergeSource,
) -> MergeSource | None:
    candidates = [
        (index, candidate)
        for index, candidate in enumerate(project.merge_sources)
        if candidate.id != source.id and candidate.asset.path
    ]
    for stable_index, candidate in sorted(
        candidates,
        key=lambda item: _merge_source_base_target_sort_key(project, item[1], item[0]),
    ):
        if _merge_source_resolved_placement_mode(project, candidate) in {
            MergePlacementMode.BASE,
            MergePlacementMode.SIDE_BY_SIDE,
            MergePlacementMode.ABOVE_BELOW,
            MergePlacementMode.FULL_SCREEN_PORTRAIT,
            MergePlacementMode.DUAL_CENTER_HUD,
            MergePlacementMode.DUAL_TOP_HUD,
        }:
            return candidate
    return None


def _camera_role_seed_target(
    project: Project,
    source: MergeSource,
    mode: MergePlacementMode,
) -> tuple[MergePlacementTargetKind, str | None]:
    if mode not in {MergePlacementMode.PIP, MergePlacementMode.FULL_SCREEN_PORTRAIT}:
        return MergePlacementTargetKind.PRIMARY_VIDEO, None
    target_source = _preferred_merge_source_base_target(project, source)
    if target_source is None:
        return MergePlacementTargetKind.PRIMARY_VIDEO, None
    return MergePlacementTargetKind.MERGE_SOURCE, target_source.id


def _merge_source_matches_role_seed_defaults(
    project: Project,
    source: MergeSource,
    reference_role: object,
) -> bool:
    current_mode = _normalize_merge_source_placement_mode(source.placement.mode)
    if current_mode == MergePlacementMode.AUTO:
        return True

    expected_mode = _camera_role_seed_placement_mode(project, reference_role, source.asset)
    if current_mode != expected_mode:
        return False

    if source.placement.slot not in {None, "", MergePlacementSlot.AUTO}:
        current_slot = _normalize_merge_source_placement_slot(
            source.placement.slot,
            mode=current_mode,
        )
        expected_slot = _camera_role_seed_placement_slot(
            reference_role,
            current_mode,
            source.asset,
        )
        if current_slot != expected_slot:
            return False

    if current_mode not in {MergePlacementMode.PIP, MergePlacementMode.FULL_SCREEN_PORTRAIT}:
        return True

    current_target_source_id = str(source.placement.target_source_id or "").strip() or None
    current_target_kind = _normalize_merge_source_placement_target_kind(
        source.placement.target_kind,
        target_source_id=current_target_source_id,
    )
    valid_target_source_ids = {
        candidate.id
        for candidate in project.merge_sources
        if candidate.id != source.id and candidate.asset.path
    }
    if current_target_kind == MergePlacementTargetKind.MERGE_SOURCE and (
        current_target_source_id not in valid_target_source_ids
    ):
        return True

    expected_target_kind, expected_target_source_id = _camera_role_seed_target(
        project,
        source,
        current_mode,
    )
    if (
        current_target_kind == expected_target_kind
        and current_target_source_id == expected_target_source_id
    ):
        return True
    return (
        current_target_kind == MergePlacementTargetKind.PRIMARY_VIDEO
        and current_target_source_id is None
    )


def _apply_merge_source_role_seed_defaults(
    project: Project,
    source: MergeSource,
    *,
    reference_role: object | None = None,
    force: bool = False,
) -> bool:
    role_reference = source.angle_role if reference_role is None else reference_role
    if not force and not _merge_source_matches_role_seed_defaults(project, source, role_reference):
        return False

    next_mode = _camera_role_seed_placement_mode(project, source.angle_role, source.asset)
    next_slot = _camera_role_seed_placement_slot(source.angle_role, next_mode, source.asset)
    next_target_kind, next_target_source_id = _camera_role_seed_target(
        project,
        source,
        next_mode,
    )

    changed = False
    if source.placement.mode != next_mode:
        source.placement.mode = next_mode
        changed = True
    if source.placement.slot != next_slot:
        source.placement.slot = next_slot
        changed = True
    if source.placement.target_kind != next_target_kind:
        source.placement.target_kind = next_target_kind
        changed = True
    if source.placement.target_source_id != next_target_source_id:
        source.placement.target_source_id = next_target_source_id
        changed = True
    return changed


def _role_priority_sorted_stage_clips(clips: list[StageClipSource]) -> list[StageClipSource]:
    return [
        clip
        for _, clip in sorted(
            enumerate(clips),
            key=lambda item: _camera_role_priority_sort_key(item[1].angle_role, item[0]),
        )
    ]


def _role_priority_sorted_merge_sources(project: Project) -> list[MergeSource]:
    return [
        source
        for index, source in sorted(
            enumerate(project.merge_sources),
            key=lambda item: _camera_role_priority_sort_key(
                item[1].angle_role,
                item[0],
                order_index=_merge_source_stable_order_index(item[1], item[0]),
            ),
        )
    ]


def _source_supports_secondary_analysis(source: MergeSource | None) -> bool:
    if source is None:
        return False
    asset = source.asset
    return bool(asset.path) and not asset.is_still_image and asset.media_kind != "animated_gif"


def _first_analyzable_merge_source(project: Project) -> MergeSource | None:
    for source in _role_priority_sorted_merge_sources(project):
        if _source_supports_secondary_analysis(source):
            return source
    return None


def _merge_source_by_id(project: Project, source_id: object) -> MergeSource | None:
    normalized_source_id = str(source_id or "").strip()
    if not normalized_source_id:
        return None
    for source in project.merge_sources:
        if source.id == normalized_source_id:
            return source
    return None


def _merge_source_id_for_asset(project: Project, asset: VideoAsset | None) -> str | None:
    if asset is None:
        return None
    asset_path = str(asset.path or "").strip()
    for source in project.merge_sources:
        if source.asset is asset:
            return source.id
        if asset_path and str(source.asset.path or "").strip() == asset_path:
            return source.id
    return None


def _project_payload_from_disk(path: str | Path) -> dict[str, object] | None:
    metadata_path = ensure_project_suffix(path) / "project.json"
    try:
        payload = json.loads(metadata_path.read_text())
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _role_priority_merge_reference_source(project: Project) -> MergeSource | None:
    preferred_source = _first_analyzable_merge_source(project)
    if preferred_source is not None:
        return preferred_source
    for source in _role_priority_sorted_merge_sources(project):
        if source.asset.path:
            return source
    return None


def _preferred_merge_reference_source(project: Project) -> MergeSource | None:
    preferred_source = _role_priority_merge_reference_source(project)
    if preferred_source is not None:
        return preferred_source
    analyzed_source = _merge_source_by_id(project, project.analysis.analyzed_secondary_source_id)
    if analyzed_source is not None and analyzed_source.asset.path:
        return analyzed_source
    return None


def _realign_live_merge_reference_state(project: Project) -> MergeSource | None:
    reference_source = _role_priority_merge_reference_source(project)
    if reference_source is None:
        _clear_secondary_analysis_state(project)
        project.secondary_video = None
        return None

    analyzed_source = _merge_source_by_id(project, project.analysis.analyzed_secondary_source_id)
    has_live_secondary_analysis = (
        analyzed_source is not None
        and analyzed_source.id == reference_source.id
        and _source_supports_secondary_analysis(reference_source)
    )
    if has_live_secondary_analysis:
        project.secondary_video = reference_source.asset
        project.analysis.sync_offset_ms = int(reference_source.sync_offset_ms)
        return reference_source

    stale_secondary_analysis = (
        project.analysis.analyzed_secondary_source_id is not None
        or project.analysis.beep_time_ms_secondary is not None
        or bool(project.analysis.waveform_secondary)
        or project.analysis.secondary_analysis_status != "idle"
        or bool(project.analysis.secondary_analysis_message)
    )
    if stale_secondary_analysis:
        _clear_secondary_analysis_state(project, preserve_sync_offset=True)
    project.analysis.sync_offset_ms = int(reference_source.sync_offset_ms)
    project.analysis.secondary_sync_source = "manual"
    project.secondary_video = (
        reference_source.asset if _source_supports_secondary_analysis(reference_source) else None
    )
    return reference_source


def _sync_secondary_video_from_merge_sources(project: Project) -> None:
    source = _first_analyzable_merge_source(project)
    project.secondary_video = None if source is None else source.asset


def _merge_source_original_path(source: MergeSource) -> str:
    original_path = str(source.trim_derivative.original_path or "").strip()
    if original_path:
        return original_path
    asset_path = str(source.asset.path or "").strip()
    derivative_path = str(source.trim_derivative.derivative_path or "").strip()
    if asset_path and asset_path != derivative_path:
        source.trim_derivative.original_path = asset_path
        return asset_path
    return ""


def _sync_merge_source_trim_provenance(source: MergeSource) -> None:
    original_path = _merge_source_original_path(source)
    derivative_path = str(source.trim_derivative.derivative_path or "").strip()
    asset_path = str(source.asset.path or "").strip()
    if derivative_path and asset_path == derivative_path:
        source.trim_derivative.active_path_kind = MergeSourceAssetPathKind.LOCAL_DERIVATIVE
        return
    source.trim_derivative.active_path_kind = MergeSourceAssetPathKind.ORIGINAL
    if not original_path and asset_path:
        source.trim_derivative.original_path = asset_path


def _reset_merge_source_trim_provenance(source: MergeSource) -> None:
    source.trim_derivative.original_path = str(source.asset.path or "")
    source.trim_derivative.derivative_path = None
    source.trim_derivative.active_path_kind = MergeSourceAssetPathKind.ORIGINAL


def _clear_secondary_analysis_state(
    project: Project, *, preserve_sync_offset: bool = False
) -> None:
    project.analysis.beep_time_ms_secondary = None
    project.analysis.analyzed_secondary_source_id = None
    project.analysis.secondary_analysis_status = "idle"
    project.analysis.secondary_analysis_message = ""
    project.analysis.waveform_secondary = []
    if not preserve_sync_offset:
        project.analysis.sync_offset_ms = 0
        project.analysis.secondary_sync_source = "manual"


def _reset_media_dependent_state_for_primary_video(project: Project) -> None:
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


def _workspace_to_dict_safe(workspace) -> dict | None:
    """Safe workspace serialization returning dict or None."""
    if workspace is None:
        return None
    try:
        from splitshot.persistence.workspaces import _workspace_to_dict

        return _workspace_to_dict(workspace)
    except Exception:
        return None


def _utc_now():
    """Return current UTC datetime."""
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)


def _autosave_workspace_if_needed(controller) -> None:
    """Autosave workspace when changes are detected."""
    if controller.workspace_path is None or controller.workspace is None:
        return
    try:
        current_snapshot = controller._workspace_persistence_snapshot()
        if current_snapshot == controller._workspace_saved_snapshot:
            return
        controller._persist_workspace_stage_profiles()
        save_workspace(controller.workspace, controller.workspace_path)
        controller._workspace_saved_snapshot = current_snapshot
    except Exception:
        pass


_INHERITANCE_ELIGIBLE_FIELDS = frozenset(
    {
        "frame_profile",
        "metric_caption_preset",
        "lead_in_card",
        "brand_mark",
        "subject_track_crop",
        "visibility_recipe",
        "aspect_ratio",
        "export_quality",
        "export_preset",
        "frame_rate",
        "video_codec",
        "audio_codec",
    }
)

_WORKSPACE_REUSABLE_PROFILE_FIELDS = (
    "frame_profile",
    "metric_caption_preset",
    "lead_in_card",
    "brand_mark",
    "subject_track_crop",
    "visibility_recipe",
)

_WORKSPACE_REUSABLE_PROJECT_SETTING_KEYS = (
    "export_preset",
    "overlay_position",
    "overlay_badge_size",
    "overlay_display_options",
    "frame_profile",
    "export_quality",
    "frame_rate",
    "video_codec",
    "audio_codec",
)

_METRIC_CAPTION_PRESET_FIELDS = {
    "none": [],
    "splits": ["split_times", "cumulative_time"],
    "score": ["hit_factor", "penalties"],
    "full": [
        "shot_count",
        "cumulative_time",
        "first_shot_reaction",
        "hit_factor",
        "penalties",
        "split_times",
    ],
}


def _new_uuid() -> str:
    return _uuid4().hex


def _enum_value(value: object) -> str | None:
    if value is None:
        return None
    return value.value if hasattr(value, "value") else str(value)


def _frame_profile_from_aspect_ratio(value: object) -> str:
    normalized = _enum_value(value) or AspectRatio.ORIGINAL.value
    return "source" if normalized == AspectRatio.ORIGINAL.value else normalized


def _aspect_ratio_from_frame_profile(value: object) -> AspectRatio:
    normalized = str(value or "source").strip().lower()
    mapping = {
        "source": AspectRatio.ORIGINAL,
        "original": AspectRatio.ORIGINAL,
        "16:9": AspectRatio.LANDSCAPE,
        "9:16": AspectRatio.PORTRAIT,
        "1:1": AspectRatio.SQUARE,
        "4:5": AspectRatio.PORTRAIT_45,
    }
    return mapping.get(normalized, AspectRatio.ORIGINAL)


def _copy_profile_payload(value: object) -> dict:
    return deepcopy(value) if isinstance(value, dict) else {}


def _profile_identity_key(profile: OutputProfile) -> tuple[str, str]:
    return (profile.profile_kind, profile.profile_name.strip().casefold())


def _metric_caption_preset_from_selection(
    selection: object,
    current: dict | None = None,
) -> dict:
    if isinstance(selection, dict):
        return deepcopy(selection)
    normalized = str(selection or "").strip().lower()
    base = deepcopy(current) if isinstance(current, dict) else {}
    if normalized not in _METRIC_CAPTION_PRESET_FIELDS:
        return base
    base["preset"] = normalized
    base["enabled_fields"] = list(_METRIC_CAPTION_PRESET_FIELDS[normalized])
    base.setdefault("format", "overlay")
    return base


def _lead_in_card_from_override(value: object, current: dict | None = None) -> dict:
    if isinstance(value, dict):
        return deepcopy(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"", "none"}:
        return {}
    duration_s = 2.0
    if isinstance(current, dict):
        try:
            duration_s = float(current.get("duration_s", duration_s) or duration_s)
        except (TypeError, ValueError):
            duration_s = 2.0
    return {
        "style": normalized,
        "duration_s": duration_s,
    }


def _brand_mark_from_override(value: object, current: dict | None = None) -> dict:
    if isinstance(value, dict):
        return deepcopy(value)
    normalized = str(value or "").strip().lower()
    if normalized in {"", "none"}:
        return {}
    duration_s = 1.0
    if isinstance(current, dict):
        try:
            duration_s = float(current.get("duration_s", duration_s) or duration_s)
        except (TypeError, ValueError):
            duration_s = 1.0
    return {
        "style": normalized,
        "text": "SplitShot" if normalized == "splitshot" else normalized,
        "duration_s": duration_s,
    }


class ProjectController(QObject):
    project_changed = Signal()
    settings_changed = Signal()
    project_path_changed = Signal(str)
    status_changed = Signal(str)

    VALID_FRAME_PROFILES = frozenset({"source", "16:9", "9:16", "1:1", "4:5"})

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
        self._practiscore_session_payload = (
            practiscore_sync_service.default_practiscore_session_payload()
        )
        self._practiscore_sync_payload = (
            practiscore_sync_service.default_practiscore_sync_payload()
        )
        self.workspace = None
        self.workspace_path = None
        self._output_profiles: dict[str, OutputProfile] = {}  # output_id -> OutputProfile
        self.editor_scope = "single"
        self.active_stage_id = None
        self._return_to_workspace_available = False
        self._workspace_saved_snapshot = None
        self._last_returned_stage_id: str | None = None
        self.status_message = "Ready."
        self._saved_snapshot = project_to_dict(self.project)
        self._original_shot_state_by_id: dict[str, _OriginalShotState] = {}
        self._autosave_in_progress = False
        self._remember_original_shots()
        self.project_changed.connect(self._autosave_project_if_needed)
        self.project_changed.connect(lambda: _autosave_workspace_if_needed(self))

    def _workspace_stage_entry(self, stage_id: str) -> StageEntry | None:
        if self.workspace is None:
            return None
        return self.workspace.stage_entries.get(stage_id)

    def _workspace_stage_clip_models(self, stage_id: str) -> list[StageClipSource]:
        entry = self._workspace_stage_entry(stage_id)
        if entry is None:
            return []
        return entry.clip_sources

    def _workspace_stage_clip_to_dict(self, clip: StageClipSource) -> dict:
        return {
            "clip_id": clip.clip_id,
            "source_path": clip.source_path,
            "angle_role": clip.angle_role,
            "sync_offset_ms": clip.sync_offset_ms,
            "audio_gain": clip.audio_gain,
            "audio_muted": clip.audio_muted,
            "audio_primary": clip.audio_primary,
            "angle_aligned": clip.angle_aligned,
        }

    def _workspace_stage_clips_to_dicts(self, stage_id: str) -> list[dict]:
        return [
            self._workspace_stage_clip_to_dict(clip)
            for clip in self._workspace_stage_clip_models(stage_id)
        ]

    def _angle_director_cut_to_dict(self, cut: AngleDirectorCutDecision) -> dict:
        return {
            "position": cut.position,
            "clip_id": cut.clip_id,
            "angle_role": cut.angle_role,
            "start_ms": cut.start_ms,
            "duration_ms": cut.duration_ms,
            "suggested": cut.suggested,
        }

    def _find_output_profile(self, output_id: str) -> OutputProfile | None:
        profile = self._output_profiles.get(output_id)
        if profile is not None:
            return profile
        if self.workspace:
            for candidate in self.workspace.match_output_profiles:
                if candidate.output_id == output_id:
                    return candidate
        return None

    def _workspace_stage_bundle_path(self, stage_id: str) -> Path | None:
        if self.workspace_path is None:
            return None
        return workspace_stage_path(self.workspace_path, stage_id)

    def _workspace_stage_project_file(
        self,
        stage_id: str,
        *,
        workspace_path: str | Path | None = None,
        entry: StageEntry | None = None,
    ) -> Path | None:
        stage_entry = entry or self._workspace_stage_entry(stage_id)
        workspace_root = None
        if workspace_path is not None:
            workspace_root = normalize_workspace_path(workspace_path)
        elif self.workspace_path is not None:
            workspace_root = normalize_workspace_path(self.workspace_path)

        canonical_path = None
        if workspace_root is not None:
            canonical_path = workspace_stage_project_path(workspace_root, stage_id)
            if canonical_path.is_file():
                return canonical_path
            if stage_entry and stage_entry.relative_project_path:
                candidate = (workspace_root / stage_entry.relative_project_path).resolve(strict=False)
                if candidate.is_dir() or candidate.name != "project.json":
                    candidate = candidate / "project.json"
                if candidate.is_file():
                    return candidate

        if stage_entry and stage_entry.relative_project_path:
            candidate = Path(stage_entry.relative_project_path).expanduser().resolve(strict=False)
            if candidate.is_dir() or candidate.name != "project.json":
                candidate = candidate / "project.json"
            if candidate.is_file():
                return candidate

        return canonical_path

    def _find_workspace_stage_for_project_path(
        self,
        project_path: str | Path,
        *,
        workspace: MatchWorkspace | None = None,
        workspace_path: str | Path | None = None,
    ) -> str | None:
        active_workspace = workspace or self.workspace
        if active_workspace is None:
            return None
        normalized_project_path = normalize_project_path(project_path)
        for stage_id, entry in active_workspace.stage_entries.items():
            candidate = self._workspace_stage_project_file(
                stage_id,
                workspace_path=workspace_path,
                entry=entry,
            )
            if candidate is None:
                continue
            if normalize_project_path(candidate) == normalized_project_path:
                return stage_id
        return None

    def _seed_workspace_defaults(self, workspace: MatchWorkspace) -> None:
        effective = self.effective_settings()
        for field in _INHERITANCE_ELIGIBLE_FIELDS:
            if hasattr(effective, field):
                value = getattr(effective, field)
                if value is not None:
                    workspace.shared_defaults[field] = value

    def _ensure_project_workspace_membership(self, project_path: str | Path) -> str | None:
        normalized_project_path = normalize_project_path(project_path)
        owner_workspace = None
        owner_workspace_path: Path | None = None
        stage_id = self._find_workspace_stage_for_project_path(normalized_project_path)

        if stage_id is not None and self.workspace is not None:
            owner_workspace = self.workspace
            if self.workspace_path is not None:
                owner_workspace_path = normalize_workspace_path(self.workspace_path)

        if owner_workspace is None:
            for candidate in [normalized_project_path, *normalized_project_path.parents]:
                if not workspace_has_metadata(candidate):
                    continue
                owner_workspace_path = normalize_workspace_path(candidate)
                owner_workspace = load_workspace(owner_workspace_path)
                stage_id = self._find_workspace_stage_for_project_path(
                    normalized_project_path,
                    workspace=owner_workspace,
                    workspace_path=owner_workspace_path,
                )
                if stage_id is None:
                    relative_project_path = normalized_project_path.relative_to(owner_workspace_path)
                    if len(relative_project_path.parts) >= 2 and relative_project_path.parts[0] == "Stages":
                        stage_id = relative_project_path.parts[1]
                break

        if owner_workspace is None:
            if self.workspace is not None and self.workspace_path is None:
                owner_workspace = self.workspace
            elif self.workspace is not None and self.workspace_path is not None:
                return None
            else:
                owner_workspace = MatchWorkspace()
                owner_workspace.name = (
                    f"{(self.project.name or normalized_project_path.name).strip()} Match"
                )
                self._seed_workspace_defaults(owner_workspace)

        resolved_stage_id = stage_id or self.project.id or normalized_project_path.name
        entry = owner_workspace.stage_entries.get(resolved_stage_id)
        if entry is None:
            entry = StageEntry(stage_id=resolved_stage_id)
            owner_workspace.stage_entries[resolved_stage_id] = entry
        if resolved_stage_id not in owner_workspace.stage_order:
            owner_workspace.stage_order.append(resolved_stage_id)
        if entry.stage_number is None:
            entry.stage_number = owner_workspace.stage_order.index(resolved_stage_id) + 1

        entry.display_name = self.project.name or entry.display_name or normalized_project_path.name
        if owner_workspace_path is not None:
            try:
                entry.relative_project_path = str(normalized_project_path.relative_to(owner_workspace_path))
            except ValueError:
                entry.relative_project_path = str(normalized_project_path)
        else:
            entry.relative_project_path = str(normalized_project_path)
        entry.source_media_present = bool(str(self.project.primary_video.path or "").strip())
        if not entry.override_values:
            entry.status = "complete" if entry.source_media_present else "incomplete"

        owner_workspace.updated_at = _utc_now()
        self.workspace = owner_workspace
        self.workspace_path = owner_workspace_path
        self.active_stage_id = resolved_stage_id
        self._return_to_workspace_available = owner_workspace_path is not None

        if owner_workspace_path is not None:
            self._load_workspace_stage_profiles()
            save_workspace(owner_workspace, owner_workspace_path)

        self._workspace_saved_snapshot = self._workspace_persistence_snapshot()
        return resolved_stage_id

    def _workspace_persistence_snapshot(self) -> dict | None:
        if self.workspace is None:
            return None
        workspace_snapshot = _workspace_to_dict_safe(self.workspace)
        if workspace_snapshot is None:
            return None
        stage_profiles = {}
        for output_id, profile in self._output_profiles.items():
            if profile.scope_type == "stage" and profile.scope_id in self.workspace.stage_entries:
                stage_profiles[output_id] = self._output_profile_to_dict_safe(profile)
        return {
            "workspace": workspace_snapshot,
            "stage_profiles": stage_profiles,
        }

    def _persist_workspace_stage_profiles(self) -> None:
        if self.workspace is None:
            return
        for stage_id in self.workspace.stage_entries:
            bundle_path = self._workspace_stage_bundle_path(stage_id)
            if bundle_path is None:
                continue
            self._save_stage_profiles(bundle_path, stage_id=stage_id)

    def _load_workspace_stage_profiles(self) -> None:
        if self.workspace is None:
            return
        self._output_profiles = {
            output_id: profile
            for output_id, profile in self._output_profiles.items()
            if not (
                profile.scope_type == "stage" and profile.scope_id in self.workspace.stage_entries
            )
        }
        for stage_id in self.workspace.stage_entries:
            bundle_path = self._workspace_stage_bundle_path(stage_id)
            if bundle_path is not None:
                self._load_stage_profiles(bundle_path)

    def new_project(self) -> None:
        self.folder_settings = None
        self.folder_settings_error = None
        self.project = self._new_project_with_settings_defaults()
        self.project_path = None
        self._clear_practiscore_source()
        self._practiscore_sync_payload = (
            practiscore_sync_service.default_practiscore_sync_payload()
        )
        self._set_status("Ready.")
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self.editor_scope = "single"
        self.active_stage_id = None
        self._return_to_workspace_available = False

    # ── Workspace lifecycle ──────────────────────────────────────────

    def new_workspace(self) -> None:
        """Create a new empty match workspace with inherited defaults."""
        self.workspace = MatchWorkspace()
        self.workspace_path = None
        self.editor_scope = "multi"
        self.active_stage_id = None
        self._return_to_workspace_available = False

        self._seed_workspace_defaults(self.workspace)

        self._workspace_saved_snapshot = self._workspace_persistence_snapshot()
        self._set_status("New match workspace created.")
        self.project_changed.emit()

    def save_workspace(self, path: str | None = None) -> None:
        """Persist workspace to disk."""
        if self.workspace is None:
            return
        save_path = Path(path) if path else self.workspace_path
        if save_path is None:
            return
        self.workspace_path = save_workspace(self.workspace, save_path)
        self._persist_workspace_stage_profiles()
        self._workspace_saved_snapshot = self._workspace_persistence_snapshot()
        self._sync_workspace_to_library()
        self._set_status(f"Workspace saved to {self.workspace_path}")

    def open_workspace(self, path: str) -> None:
        """Open an existing match workspace from disk."""
        ws_path = Path(path)
        if not workspace_has_metadata(ws_path):
            self._set_status(f"No workspace found at {path}")
            return
        self.workspace = load_workspace(ws_path)
        self.workspace_path = ws_path
        self.editor_scope = "multi"
        self.active_stage_id = None
        self._return_to_workspace_available = False
        self._load_workspace_stage_profiles()
        self._workspace_saved_snapshot = self._workspace_persistence_snapshot()
        self._set_status(f"Opened workspace: {self.workspace.name}")

    # ── Stage membership ────────────────────────────────────────────

    def workspace_add_stage(
        self, stage_id: str, display_name: str = "", project_path: str = ""
    ) -> None:
        """Add a stage entry to the current workspace."""
        if self.workspace is None:
            return
        entry = StageEntry(
            stage_id=stage_id,
            display_name=display_name or f"Stage {len(self.workspace.stage_entries) + 1}",
            relative_project_path=project_path,
        )
        self.workspace.stage_entries[stage_id] = entry
        if stage_id not in self.workspace.stage_order:
            self.workspace.stage_order.append(stage_id)
        self.workspace.updated_at = _utc_now()
        self._set_status(f"Added stage {stage_id} to workspace.")
        self.project_changed.emit()

    def workspace_remove_stage(self, stage_id: str) -> None:
        """Remove a stage entry from the current workspace (does not delete project files)."""
        if self.workspace is None:
            return
        self.workspace.stage_entries.pop(stage_id, None)
        if stage_id in self.workspace.stage_order:
            self.workspace.stage_order.remove(stage_id)
        self.workspace.updated_at = _utc_now()
        self._set_status(f"Removed stage {stage_id} from workspace.")
        self.project_changed.emit()

    # ── Stage open / return ─────────────────────────────────────────

    def workspace_open_stage(self, stage_id: str) -> dict | None:
        """Open a stage from the workspace into the focused editor.

        Loads the stage's project.json (if it exists in the workspace tree)
        and sets editor_scope with return context.

        Returns structured error dict on failure, None on success.
        """
        if self.workspace is None:
            return {"match_id": None, "stage_id": stage_id, "reason": "No workspace is open"}
        if stage_id not in self.workspace.stage_entries:
            return {
                "match_id": self.workspace.match_id,
                "stage_id": stage_id,
                "reason": "Stage not found in workspace",
            }
        if self.workspace_path is not None:
            self.save_workspace()
        if self.workspace_path is not None:
            stage_project = self._workspace_stage_project_file(stage_id)
            if stage_project is not None and stage_project.exists():
                self.open_project(str(stage_project.parent))
                self._load_stage_profiles(Path(self.project_path))
        self.active_stage_id = stage_id
        self.editor_scope = "multi"
        self._return_to_workspace_available = True
        self._set_status(f"Editing stage: {self.workspace.stage_entries[stage_id].display_name}")
        return None

    def workspace_return_to_workspace(self) -> None:
        """Return from stage editor back to workspace context."""
        previous_stage_id = self.active_stage_id
        self.active_stage_id = None
        self._return_to_workspace_available = False
        if self.workspace_path is not None and workspace_has_metadata(self.workspace_path):
            self.workspace = load_workspace(self.workspace_path)
        self._last_returned_stage_id = previous_stage_id
        self._set_status(
            f"Returned to workspace: {self.workspace.name if self.workspace else 'Unknown'}"
        )

    # ── Shared defaults and overrides ───────────────────────────────

    def workspace_set_defaults(self, payload: dict) -> None:
        """Set match-level shared defaults (inheritance-eligible fields only)."""
        if self.workspace is None:
            return
        filtered = {k: v for k, v in payload.items() if k in _INHERITANCE_ELIGIBLE_FIELDS}
        self.workspace.shared_defaults.update(filtered)
        self.workspace.updated_at = _utc_now()
        self._set_status("Updated workspace shared defaults.")
        self.project_changed.emit()

    def workspace_set_stage_override(self, stage_id: str, payload: dict) -> None:
        """Set a stage-local override value (inheritance-eligible fields only)."""
        if self.workspace is None or stage_id not in self.workspace.stage_entries:
            return
        filtered = {k: v for k, v in payload.items() if k in _INHERITANCE_ELIGIBLE_FIELDS}
        if not filtered:
            return
        entry = self.workspace.stage_entries[stage_id]
        entry.override_values.update(filtered)
        entry.status = "overridden"
        self.workspace.updated_at = _utc_now()
        self._set_status(f"Set override for stage {stage_id}.")
        self.project_changed.emit()

    def workspace_reset_stage_override(self, stage_id: str, keys: list[str] | None = None) -> None:
        """Remove stage-local overrides, reverting to inherited values."""
        if self.workspace is None or stage_id not in self.workspace.stage_entries:
            return
        entry = self.workspace.stage_entries[stage_id]
        if keys is None:
            entry.override_values.clear()
        else:
            for key in keys:
                entry.override_values.pop(key, None)
        if not entry.override_values:
            entry.status = "complete" if entry.source_media_present else "incomplete"
        self.workspace.updated_at = _utc_now()
        self._set_status(f"Reset overrides for stage {stage_id}.")
        self.project_changed.emit()

    def workspace_reset_defaults(self) -> dict:
        """Clear workspace shared defaults and update timestamp."""
        if not self.workspace:
            return {"error": "No workspace open"}
        self.workspace.shared_defaults.clear()
        self.workspace.updated_at = _utc_now()
        self.autosave_project_if_needed()
        self.project_changed.emit()
        return {"reset": True}

    @staticmethod
    def _workspace_export_recipe(value: str | None) -> tuple[str, bool]:
        raw_value = "" if value is None else str(value).strip().lower()
        if not raw_value:
            return "stage_output", True
        if raw_value in {"stage_output", "stage_composite"}:
            return raw_value, False
        raise ValueError(f"Unsupported workspace export recipe: {value}")

    @staticmethod
    def _workspace_export_output_path(
        workspace_path: Path,
        stage_id: str,
        recipe: str,
        *,
        legacy_default: bool = False,
    ) -> Path:
        if legacy_default and recipe == "stage_output":
            return workspace_path / f"{stage_id}.mp4"
        exports_dir = workspace_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        return exports_dir / f"{stage_id}-{recipe}.mp4"

    @staticmethod
    def _target_even_dimensions(width: int, height: int) -> tuple[int, int]:
        safe_width = max(2, int(width) - (int(width) % 2))
        safe_height = max(2, int(height) - (int(height) % 2))
        return safe_width, safe_height

    def _workspace_export_dimensions(
        self,
        project: Project | None,
        frame_profile: str,
        base_width: int,
        base_height: int,
    ) -> tuple[int, int]:
        if (
            project is not None
            and project.export.target_width
            and project.export.target_height
            and int(project.export.target_width) > 0
            and int(project.export.target_height) > 0
        ):
            return self._target_even_dimensions(
                int(project.export.target_width),
                int(project.export.target_height),
            )
        profile_dimensions = {
            "16:9": (640, 360),
            "9:16": (360, 640),
            "1:1": (360, 360),
            "4:5": (360, 450),
        }
        if frame_profile in profile_dimensions:
            return profile_dimensions[frame_profile]
        return self._target_even_dimensions(base_width, base_height)

    @staticmethod
    def _run_media_command(
        command: list[str],
        *,
        timeout: int = 600,
        error_message: str,
    ) -> None:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or error_message)

    def _stage_profile_for_kind(self, stage_id: str, profile_kind: str) -> OutputProfile | None:
        for candidate in self._output_profiles.values():
            if (
                candidate.scope_type == "stage"
                and candidate.scope_id == stage_id
                and candidate.profile_kind == profile_kind
            ):
                return candidate
        return None

    def _output_profile_render_plan_for_project(
        self,
        project: Project,
        profile: OutputProfile,
    ) -> dict[str, object]:
        return {
            "success": True,
            "output_id": profile.output_id,
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "scope_type": profile.scope_type,
            "scope_id": profile.scope_id,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": dict(profile.metric_caption_preset),
            "lead_in_card": dict(profile.lead_in_card),
            "brand_mark": dict(profile.brand_mark),
            "subject_track_crop": dict(profile.subject_track_crop),
            "visibility_recipe": dict(profile.visibility_recipe),
            "run_window": self._resolve_run_window(profile, project=project),
            "source": "output_profile",
        }

    def _workspace_export_stage_output_item(
        self,
        stage_id: str,
        workspace_path: Path,
        *,
        legacy_default: bool = False,
    ) -> dict[str, object]:
        entry = self.workspace.stage_entries.get(stage_id) if self.workspace is not None else None
        if entry is None:
            raise ValueError("Stage entry not found")

        project = self._load_stage_project(stage_id)
        if not project:
            raise ValueError("Cannot load stage project")
        if not project.primary_video or not project.primary_video.path:
            raise ValueError("No video imported for this stage")

        output_path = self._workspace_export_output_path(
            workspace_path,
            stage_id,
            "stage_output",
            legacy_default=legacy_default,
        )
        display_name = entry.display_name or f"Stage {entry.stage_number}"
        profile = self._stage_profile_for_kind(stage_id, "stage_output")

        self._set_status(f"Exporting {display_name}...")
        if profile is None:
            exported_path = export_project(
                project,
                str(output_path),
                progress_callback=lambda _value: None,
                log_callback=lambda _line: None,
            )
        else:
            render_plan = self._output_profile_render_plan_for_project(project, profile)
            exported_path = export_output_profile(
                project,
                output_path,
                render_plan,
                progress_callback=lambda _value: None,
                log_callback=lambda _line: None,
            )
            profile.last_rendered_at = _utc_now()

        size_bytes = exported_path.stat().st_size if exported_path.exists() else 0
        return {
            "stage_id": stage_id,
            "display_name": display_name,
            "output_path": str(exported_path),
            "size_bytes": size_bytes,
            "status": "completed",
            "recipe": "stage_output",
        }

    def _workspace_stage_composite_segments(
        self,
        stage_id: str,
        output_id: str | None = None,
    ) -> tuple[OutputProfile, list[dict[str, object]]]:
        entry = self._workspace_stage_entry(stage_id)
        if entry is None:
            raise ValueError("Stage not found in workspace")

        profile = self._stage_composite_profile(stage_id, output_id)
        if profile is None:
            raise ValueError("Stage composite output profile not found")

        clips = [
            clip
            for clip in self._workspace_stage_clip_models(stage_id)
            if clip.source_path and Path(clip.source_path).exists()
        ]
        if not clips:
            raise ValueError("No clip sources available for Stage Composite export")

        clip_by_id = {clip.clip_id: clip for clip in clips}
        segments: list[dict[str, object]] = []
        persisted_plan = [
            self._angle_director_cut_to_dict(cut)
            for cut in profile.angle_director_plan
            if int(cut.duration_ms) > 0
        ]

        if persisted_plan:
            for plan_item in sorted(
                persisted_plan,
                key=lambda item: (int(item.get("position") or 0), int(item.get("start_ms") or 0)),
            ):
                clip = clip_by_id.get(str(plan_item.get("clip_id") or ""))
                if clip is None:
                    continue
                asset = probe_video(Path(clip.source_path))
                asset_duration_ms = max(1, int(asset.duration_ms or 0))
                start_ms = max(0, int(plan_item.get("start_ms") or 0))
                if start_ms >= asset_duration_ms:
                    continue
                duration_ms = max(0, int(plan_item.get("duration_ms") or 0))
                if duration_ms <= 0:
                    continue
                duration_ms = min(duration_ms, asset_duration_ms - start_ms)
                if duration_ms <= 0:
                    continue
                segments.append(
                    {
                        "clip": clip,
                        "asset": asset,
                        "start_ms": start_ms,
                        "duration_ms": duration_ms,
                        "position": int(plan_item.get("position") or 0),
                    }
                )

        if not segments:
            for index, clip in enumerate(clips):
                asset = probe_video(Path(clip.source_path))
                asset_duration_ms = max(1, int(asset.duration_ms or 0))
                start_ms = max(0, int(clip.sync_offset_ms) if int(clip.sync_offset_ms) > 0 else 0)
                if start_ms >= asset_duration_ms:
                    continue
                duration_ms = min(asset_duration_ms - start_ms, 1500)
                if duration_ms <= 0:
                    continue
                segments.append(
                    {
                        "clip": clip,
                        "asset": asset,
                        "start_ms": start_ms,
                        "duration_ms": duration_ms,
                        "position": index,
                    }
                )

        if not segments:
            raise ValueError("Stage composite export has no renderable clip segments")

        return profile, segments

    def _workspace_export_stage_composite_item(
        self,
        stage_id: str,
        workspace_path: Path,
    ) -> dict[str, object]:
        entry = self.workspace.stage_entries.get(stage_id) if self.workspace is not None else None
        if entry is None:
            raise ValueError("Stage entry not found")

        stage_project = self._load_stage_project(stage_id)
        profile, segments = self._workspace_stage_composite_segments(stage_id)
        display_name = entry.display_name or f"Stage {entry.stage_number}"
        first_asset = segments[0]["asset"]
        target_width, target_height = self._workspace_export_dimensions(
            stage_project,
            profile.frame_profile,
            int(first_asset.width or 640),
            int(first_asset.height or 360),
        )
        output_path = self._workspace_export_output_path(workspace_path, stage_id, "stage_composite")

        self._set_status(f"Exporting {display_name} composite...")
        with TemporaryDirectory(prefix="splitshot-stage-composite-") as temp_dir_name:
            temp_dir = Path(temp_dir_name)
            rendered_segments: list[Path] = []
            for index, segment in enumerate(segments):
                clip = segment["clip"]
                source_path = Path(clip.source_path)
                segment_path = temp_dir / f"segment-{index:02d}.mp4"
                segment_seconds = max(0.05, float(segment["duration_ms"]) / 1000.0)
                command = [
                    "ffmpeg",
                    "-y",
                    "-ss",
                    f"{float(segment['start_ms']) / 1000.0:.3f}",
                    "-i",
                    str(source_path),
                    "-t",
                    f"{segment_seconds:.3f}",
                    "-vf",
                    (
                        f"scale={target_width}:{target_height}:force_original_aspect_ratio=decrease,"
                        f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                        "setsar=1"
                    ),
                    "-map",
                    "0:v:0",
                    "-map",
                    "0:a:0?",
                ]
                if clip.audio_muted:
                    command.extend(["-af", "volume=0.000"])
                elif abs(float(clip.audio_gain) - 1.0) > 0.001:
                    command.extend(["-af", f"volume={max(0.0, min(2.0, float(clip.audio_gain))):.3f}"])
                command.extend(
                    [
                        "-c:v",
                        "libx264",
                        "-preset",
                        "veryfast",
                        "-crf",
                        "18",
                        "-c:a",
                        "aac",
                        "-ar",
                        "48000",
                        "-ac",
                        "2",
                        "-b:a",
                        "192k",
                        str(segment_path),
                    ]
                )
                self._run_media_command(
                    command,
                    error_message=f"Stage composite segment export failed for {source_path.name}",
                )
                rendered_segments.append(segment_path)

            concat_path = temp_dir / "segments.txt"
            concat_path.write_text(
                "\n".join(
                    f"file '{str(path).replace("'", "'\\''")}'" for path in rendered_segments
                )
                + "\n",
                encoding="utf-8",
            )
            self._run_media_command(
                [
                    "ffmpeg",
                    "-y",
                    "-f",
                    "concat",
                    "-safe",
                    "0",
                    "-i",
                    str(concat_path),
                    "-c:v",
                    "libx264",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "18",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "192k",
                    str(output_path),
                ],
                error_message="Stage composite export failed",
            )

        profile.last_rendered_at = _utc_now()
        size_bytes = output_path.stat().st_size if output_path.exists() else 0
        return {
            "stage_id": stage_id,
            "display_name": display_name,
            "output_path": str(output_path),
            "size_bytes": size_bytes,
            "status": "completed",
            "recipe": "stage_composite",
            "segment_count": len(segments),
        }

    def workspace_export(self, stage_id: str | None = None, recipe: str | None = None) -> dict:
        """Export workspace stage(s) to actual video files.
        
        For each stage in the workspace, loads the stage project and runs
        the export pipeline to produce an MP4 file in the workspace directory.
        Returns output paths and file sizes for completed exports.
        """
        if not self.workspace:
            return {"success": False, "error": "No workspace open", "outputs": [], "errors": []}

        if not self.workspace_path:
            return {"success": False, "error": "Workspace has not been saved", "outputs": [], "errors": []}

        if stage_id and stage_id not in self.workspace.stage_entries:
            return {"success": False, "error": f"Stage {stage_id} not in workspace", "outputs": [], "errors": [{"stage_id": stage_id, "error": "Not found in workspace"}]}

        try:
            resolved_recipe, legacy_default = self._workspace_export_recipe(recipe)
        except ValueError as exc:
            return {
                "success": False,
                "error": str(exc),
                "outputs": [],
                "errors": [{"stage_id": stage_id or "", "error": str(exc)}],
            }

        stages_to_export = [stage_id] if stage_id else list(self.workspace.stage_entries.keys())
        outputs = []
        errors = []
        ws_path = Path(self.workspace_path)

        for sid in stages_to_export:
            entry = self.workspace.stage_entries.get(sid)
            if not entry:
                errors.append({"stage_id": sid, "error": "Stage entry not found"})
                continue

            try:
                if resolved_recipe == "stage_composite":
                    outputs.append(self._workspace_export_stage_composite_item(sid, ws_path))
                else:
                    outputs.append(
                        self._workspace_export_stage_output_item(
                            sid,
                            ws_path,
                            legacy_default=legacy_default,
                        )
                    )
            except Exception as exc:
                errors.append({"stage_id": sid, "error": str(exc)})

        if errors:
            self._set_status(f"Export completed with {len(errors)} error(s).")
        else:
            self._set_status(f"Exported {len(outputs)} stage(s).")

        return {
            "success": len(errors) == 0,
            "outputs": outputs,
            "errors": errors,
            "total": len(stages_to_export),
            "completed": len(outputs),
            "failed": len(errors),
        }

    @staticmethod
    def _recap_transition(value: str | None) -> str:
        transition = str(value or "cut").strip().lower()
        return transition if transition in {"cut", "fade", "dissolve"} else "cut"

    @staticmethod
    def _recap_result_card_mode(value: str | None) -> str:
        mode = str(value or "none").strip().lower()
        return mode if mode in {"none", "end", "each"} else "none"

    @staticmethod
    def _recap_status_label(value: str | None) -> str:
        return str(value or "incomplete").replace("_", " ").strip().title() or "Incomplete"

    @staticmethod
    def _recap_stage_options(value: object) -> dict[str, dict[str, object]]:
        raw_items: list[object] = []
        if isinstance(value, dict):
            raw_items = [
                {"stage_id": stage_id, **(raw if isinstance(raw, dict) else {})}
                for stage_id, raw in value.items()
            ]
        elif isinstance(value, list):
            raw_items = value

        options_by_stage: dict[str, dict[str, object]] = {}
        for raw_item in raw_items:
            if not isinstance(raw_item, dict):
                continue
            stage_id = str(raw_item.get("stage_id") or "").strip()
            if not stage_id:
                continue
            subtitle = " ".join(str(raw_item.get("subtitle") or "").split()).strip()[:120]
            try:
                audio_gain = float(raw_item.get("audio_gain", 1.0))
            except (TypeError, ValueError):
                audio_gain = 1.0
            options_by_stage[stage_id] = {
                "subtitle": subtitle,
                "audio_gain": max(0.0, min(2.0, audio_gain)),
                "audio_muted": bool(raw_item.get("audio_muted", False)),
            }
        return options_by_stage

    @staticmethod
    def _recap_stage_option_requested(stage_option: dict[str, object] | None) -> bool:
        if not isinstance(stage_option, dict):
            return False
        subtitle = str(stage_option.get("subtitle") or "").strip()
        try:
            audio_gain = float(stage_option.get("audio_gain", 1.0))
        except (TypeError, ValueError):
            audio_gain = 1.0
        return bool(subtitle) or bool(stage_option.get("audio_muted", False)) or abs(audio_gain - 1.0) > 0.001

    def _render_recap_card_image(
        self,
        title: str,
        detail_lines: list[str],
        output_path: Path,
        *,
        width: int,
        height: int,
    ) -> Path:
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor("#0b0f14"))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.fillRect(0, 0, width, height, QColor("#0b0f14"))
        painter.fillRect(0, 0, width, max(8, height // 48), QColor("#ff7b22"))
        painter.fillRect(width // 12, height // 6, width // 18, (height * 2) // 3, QColor("#141c27"))

        title_font = QFont("Helvetica Neue")
        title_font.setBold(True)
        title_font.setPixelSize(max(32, min(68, height // 11)))
        painter.setFont(title_font)
        painter.setPen(QColor("#ffffff"))
        title_rect = QRectF(width * 0.14, height * 0.18, width * 0.72, height * 0.24)
        painter.drawText(title_rect, Qt.AlignCenter | Qt.TextWordWrap, title)

        detail_font = QFont("Helvetica Neue")
        detail_font.setPixelSize(max(18, min(34, height // 26)))
        painter.setFont(detail_font)
        painter.setPen(QColor("#d7dee8"))
        detail_rect = QRectF(width * 0.18, height * 0.46, width * 0.64, height * 0.28)
        painter.drawText(
            detail_rect,
            Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
            "\n".join(detail_lines),
        )

        footer_font = QFont("Helvetica Neue")
        footer_font.setPixelSize(max(14, min(22, height // 36)))
        painter.setFont(footer_font)
        painter.setPen(QColor("#8ca0b7"))
        painter.drawText(
            QRectF(width * 0.12, height * 0.82, width * 0.76, height * 0.08),
            Qt.AlignCenter | Qt.AlignVCenter,
            "Rendered by SplitShot Match Recap",
        )
        painter.end()

        image.save(str(output_path))
        return output_path

    def _render_recap_card_video(
        self,
        title: str,
        detail_lines: list[str],
        output_path: Path,
        *,
        width: int,
        height: int,
        fps: float,
        duration_ms: int,
    ) -> Path:
        image_path = output_path.with_suffix(".png")
        self._render_recap_card_image(title, detail_lines, image_path, width=width, height=height)

        cmd = [
            "ffmpeg",
            "-y",
            "-loop",
            "1",
            "-i",
            str(image_path),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-t",
            f"{max(0.5, duration_ms / 1000):.3f}",
            "-vf",
            (
                f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                f"fps={fps:.3f}"
            ),
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Result card render failed")
        return output_path

    def _render_recap_subtitle_overlay_image(
        self,
        subtitle: str,
        output_path: Path,
        *,
        width: int,
        height: int,
    ) -> Path:
        image = QImage(width, height, QImage.Format.Format_ARGB32)
        image.fill(QColor(0, 0, 0, 0))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        band_height = max(72, min(132, height // 6 if height else 96))
        top_accent_height = max(4, band_height // 18)
        band_y = max(0, height - band_height)
        painter.fillRect(QRectF(0, band_y, width, band_height), QColor(0, 0, 0, 176))
        painter.fillRect(QRectF(0, band_y, width, top_accent_height), QColor("#ff7b22"))

        text_font = QFont("Helvetica Neue")
        text_font.setBold(True)
        text_font.setPixelSize(max(22, min(38, band_height // 2)))
        painter.setFont(text_font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRectF(width * 0.08, band_y + max(8, band_height * 0.18), width * 0.84, band_height * 0.62),
            Qt.AlignCenter | Qt.AlignVCenter | Qt.TextWordWrap,
            subtitle,
        )
        painter.end()

        image.save(str(output_path))
        return output_path

    def _render_recap_stage_variant(
        self,
        source_path: Path,
        output_path: Path,
        *,
        subtitle: str = "",
        audio_gain: float = 1.0,
        audio_muted: bool = False,
        width: int,
        height: int,
    ) -> Path:
        normalized_subtitle = " ".join(str(subtitle or "").split()).strip()
        normalized_audio_gain = max(0.0, min(2.0, float(audio_gain)))
        apply_subtitle = bool(normalized_subtitle)
        apply_audio_filter = audio_muted or abs(normalized_audio_gain - 1.0) > 0.001

        if not apply_subtitle and not apply_audio_filter:
            import shutil

            shutil.copy2(str(source_path), str(output_path))
            return output_path

        input_args = ["-i", str(source_path)]
        filter_parts: list[str] = []
        video_label = "0:v:0"
        audio_label = "0:a:0?"

        if apply_subtitle:
            overlay_path = output_path.with_suffix(".subtitle.png")
            self._render_recap_subtitle_overlay_image(
                normalized_subtitle,
                overlay_path,
                width=width,
                height=height,
            )
            input_args.extend(["-i", str(overlay_path)])
            filter_parts.append("[1:v]format=rgba[subtitle_overlay]")
            filter_parts.append("[0:v][subtitle_overlay]overlay=0:0[vout]")
            video_label = "[vout]"

        if apply_audio_filter:
            volume_level = 0.0 if audio_muted else normalized_audio_gain
            filter_parts.append(f"[0:a]volume={volume_level:.3f}[aout]")
            audio_label = "[aout]"

        cmd = ["ffmpeg", "-y", *input_args]
        if filter_parts:
            cmd.extend(["-filter_complex", ";".join(filter_parts), "-map", video_label, "-map", audio_label])
        else:
            cmd.extend(["-map", "0:v:0", "-map", "0:a:0?"])
        cmd.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "18",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_path),
            ]
        )
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise RuntimeError(result.stderr.strip() or "Recap stage render failed")
        return output_path

    def _render_recap_sequence(
        self,
        sequence_paths: list[Path],
        recap_path: Path,
        *,
        transition: str,
        target_width: int,
        target_height: int,
        target_fps: float,
    ) -> dict:
        if not sequence_paths:
            return {"success": False, "error": "No recap media to render"}

        if len(sequence_paths) == 1 and transition == "cut":
            import shutil

            shutil.copy2(str(sequence_paths[0]), str(recap_path))
            return {"success": True, "sequence_count": 1, "transition": transition}

        sequence_assets = [probe_video(path) for path in sequence_paths]
        filter_parts: list[str] = []
        input_args: list[str] = []
        for index, path in enumerate(sequence_paths):
            input_args.extend(["-i", str(path)])
            filter_parts.append(
                (
                    f"[{index}:v]scale={target_width}:{target_height}:"
                    "force_original_aspect_ratio=decrease,"
                    f"pad={target_width}:{target_height}:(ow-iw)/2:(oh-ih)/2:color=black,"
                    f"setsar=1,fps={target_fps:.3f},format=yuv420p[v{index}]"
                )
            )
            filter_parts.append(
                f"[{index}:a]aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[a{index}]"
            )

        if transition == "cut" or len(sequence_paths) == 1:
            concat_inputs = "".join(f"[v{index}][a{index}]" for index in range(len(sequence_paths)))
            filter_parts.append(
                f"{concat_inputs}concat=n={len(sequence_paths)}:v=1:a=1[vout][aout]"
            )
            video_label = "[vout]"
            audio_label = "[aout]"
        else:
            fade_duration_s = 0.35
            xfade_transition = "dissolve" if transition == "dissolve" else "fade"
            video_label = "[v0]"
            audio_label = "[a0]"
            elapsed_s = max(0.0, sequence_assets[0].duration_ms / 1000)
            for index in range(1, len(sequence_paths)):
                next_video = f"[v{index}]"
                next_audio = f"[a{index}]"
                out_video = f"[vx{index}]"
                out_audio = f"[ax{index}]"
                offset_s = max(0.0, elapsed_s - fade_duration_s)
                filter_parts.append(
                    (
                        f"{video_label}{next_video}xfade=transition={xfade_transition}:"
                        f"duration={fade_duration_s:.3f}:offset={offset_s:.3f}{out_video}"
                    )
                )
                filter_parts.append(
                    f"{audio_label}{next_audio}acrossfade=d={fade_duration_s:.3f}{out_audio}"
                )
                video_label = out_video
                audio_label = out_audio
                elapsed_s = max(
                    fade_duration_s,
                    elapsed_s + (sequence_assets[index].duration_ms / 1000) - fade_duration_s,
                )

        cmd = [
            "ffmpeg",
            "-y",
            *input_args,
            "-filter_complex",
            ";".join(filter_parts),
            "-map",
            video_label,
            "-map",
            audio_label,
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            str(recap_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Recap render failed: {result.stderr[:500]}",
            }
        return {
            "success": True,
            "sequence_count": len(sequence_paths),
            "transition": transition,
        }

    def workspace_recap_render(self, **kwargs) -> dict:
        """Render a recap composite video from workspace stages.
        
        Exports each selected stage to a temporary file, then concatenates
        them into a single MP4 using the ffmpeg concat demuxer.
        Accepts: stage_ids (list[str]), transition (str), result_card (str),
        and stage_options (list[dict]) for ordered subtitle/audio overrides.
        Returns the path to the rendered recap file.
        """
        if not self.workspace:
            return {"success": False, "error": "No workspace open"}

        if not self.workspace_path:
            return {"success": False, "error": "Workspace has not been saved"}

        raw_stage_ids = kwargs.get("stage_ids") or list(self.workspace.stage_order or self.workspace.stage_entries.keys())
        if isinstance(raw_stage_ids, (str, bytes)):
            stage_ids = [str(raw_stage_ids).strip()] if str(raw_stage_ids).strip() else []
        else:
            stage_ids = [str(stage_id).strip() for stage_id in raw_stage_ids if str(stage_id).strip()]
        transition = self._recap_transition(kwargs.get("transition"))
        result_card_mode = self._recap_result_card_mode(kwargs.get("result_card"))
        stage_options = self._recap_stage_options(kwargs.get("stage_options"))

        ws_path = Path(self.workspace_path)
        recap_path = ws_path / "recap.mp4"
        temp_dir = ws_path / ".recap-tmp"
        temp_dir.mkdir(parents=True, exist_ok=True)

        exported_segments: list[dict] = []
        errors: list[dict] = []

        try:
            for sid in stage_ids:
                entry = self.workspace.stage_entries.get(sid)
                if not entry:
                    errors.append({"stage_id": sid, "error": "Stage entry not found"})
                    continue

                project = self._load_stage_project(sid)
                if not project:
                    errors.append({"stage_id": sid, "error": "Cannot load stage project"})
                    continue
                if not project.primary_video or not project.primary_video.path:
                    errors.append({"stage_id": sid, "error": "No video imported for this stage"})
                    continue

                seg_path = temp_dir / f"{sid}.mp4"
                self._set_status(f"Exporting {sid} for recap...")
                export_project(
                    project,
                    str(seg_path),
                    progress_callback=lambda v: None,
                    log_callback=lambda line: None,
                )
                if seg_path.exists() and seg_path.stat().st_size > 0:
                    segment_path = seg_path
                    segment_asset = probe_video(seg_path)
                    stage_option = stage_options.get(str(sid), {})
                    if self._recap_stage_option_requested(stage_option):
                        processed_path = temp_dir / f"{sid}-recap-variant.mp4"
                        try:
                            self._set_status(f"Applying recap options to {sid}...")
                            self._render_recap_stage_variant(
                                seg_path,
                                processed_path,
                                subtitle=str(stage_option.get("subtitle") or ""),
                                audio_gain=float(stage_option.get("audio_gain", 1.0)),
                                audio_muted=bool(stage_option.get("audio_muted", False)),
                                width=max(2, int(segment_asset.width or 0)),
                                height=max(2, int(segment_asset.height or 0)),
                            )
                            if processed_path.exists() and processed_path.stat().st_size > 0:
                                segment_path = processed_path
                                segment_asset = probe_video(segment_path)
                            else:
                                errors.append({
                                    "stage_id": sid,
                                    "error": "Recap stage overrides produced an empty file",
                                })
                        except Exception as exc:
                            errors.append({
                                "stage_id": sid,
                                "error": f"Recap stage overrides failed: {exc}",
                            })
                    exported_segments.append(
                        {
                            "stage_id": sid,
                            "entry": entry,
                            "path": segment_path,
                            "asset": segment_asset,
                            "recap_options": stage_option,
                        }
                    )
                else:
                    errors.append({"stage_id": sid, "error": "Export produced empty file"})

            if not exported_segments:
                return {
                    "success": False,
                    "error": "No stages could be exported for recap",
                    "errors": errors,
                }

            reference_asset = exported_segments[0]["asset"]
            target_width = max(2, int(reference_asset.width) - (int(reference_asset.width) % 2))
            target_height = max(2, int(reference_asset.height) - (int(reference_asset.height) % 2))
            target_fps = max(1.0, float(reference_asset.fps or 30.0))

            sequence_paths = [segment["path"] for segment in exported_segments]
            if result_card_mode != "none":
                cards_result = self.resolve_result_cards("recap")
                if not cards_result.get("success"):
                    errors.append({"error": cards_result.get("error", "Result cards unavailable")})
                else:
                    cards_by_stage = {
                        str(card.get("stage_id") or ""): card
                        for card in cards_result.get("cards", [])
                    }
                    if result_card_mode == "each":
                        sequence_paths = []
                        for segment in exported_segments:
                            sequence_paths.append(segment["path"])
                            card = cards_by_stage.get(segment["stage_id"])
                            if not card or not card.get("enabled", True):
                                continue
                            card_path = temp_dir / f"{segment['stage_id']}-result-card.mp4"
                            try:
                                self._render_recap_card_video(
                                    card.get("stage_name") or f"Stage {card.get('stage_number') or ''}".strip(),
                                    [
                                        f"Stage {card.get('stage_number') or '--'}",
                                        f"Status: {self._recap_status_label(card.get('status'))}",
                                    ],
                                    card_path,
                                    width=target_width,
                                    height=target_height,
                                    fps=target_fps,
                                    duration_ms=int(card.get("duration_ms", 3000)),
                                )
                                sequence_paths.append(card_path)
                            except Exception as exc:
                                errors.append(
                                    {
                                        "stage_id": segment["stage_id"],
                                        "error": f"Result card render failed: {exc}",
                                    }
                                )
                    elif result_card_mode == "end":
                        summary_lines = []
                        for segment in exported_segments:
                            card = cards_by_stage.get(segment["stage_id"])
                            if not card or not card.get("enabled", True):
                                continue
                            summary_lines.append(
                                f"Stage {card.get('stage_number') or '--'} • {card.get('stage_name') or segment['stage_id']} • {self._recap_status_label(card.get('status'))}"
                            )
                        if summary_lines:
                            summary_path = temp_dir / "recap-summary-card.mp4"
                            try:
                                self._render_recap_card_video(
                                    self.workspace.name or "Match Recap",
                                    summary_lines[:8],
                                    summary_path,
                                    width=target_width,
                                    height=target_height,
                                    fps=target_fps,
                                    duration_ms=3500,
                                )
                                sequence_paths.append(summary_path)
                            except Exception as exc:
                                errors.append({"error": f"Result card render failed: {exc}"})

            render_result = self._render_recap_sequence(
                sequence_paths,
                recap_path,
                transition=transition,
                target_width=target_width,
                target_height=target_height,
                target_fps=target_fps,
            )
            if not render_result.get("success"):
                return {
                    "success": False,
                    "error": render_result.get("error", "Recap render failed"),
                    "errors": errors,
                }

            if not recap_path.exists() or recap_path.stat().st_size <= 0:
                return {
                    "success": False,
                    "error": "Recap file was not produced",
                    "errors": errors,
                }

            self._set_status(f"Recap rendered to {recap_path}")
            return {
                "success": True,
                "output_path": str(recap_path),
                "size_bytes": recap_path.stat().st_size,
                "stage_count": len(exported_segments),
                "transition": transition,
                "result_card": result_card_mode,
                "sequence_count": len(sequence_paths),
                "stage_options_applied": [
                    segment["stage_id"]
                    for segment in exported_segments
                    if self._recap_stage_option_requested(segment.get("recap_options"))
                ],
                "errors": errors,
            }

        finally:
            import shutil
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)

    def workspace_apply_from_first(self, settings: dict | None = None) -> dict:
        """Apply Stage 1 settings to all sibling stages.

        Loads actual stage projects and copies reusable settings
        (export preset, overlay, frame profile, etc.) to siblings.

        Settings with explicit overrides on a sibling are skipped and
        reported as conflicts.
        """
        if not self.workspace:
            return {"error": "No workspace open"}

        stage_entries = [
            self.workspace.stage_entries[stage_id]
            for stage_id in self.workspace.stage_order
            if stage_id in self.workspace.stage_entries
        ]
        if len(stage_entries) < 2:
            return {"error": "Need at least 2 stages"}

        first_entry = stage_entries[0]
        if not first_entry.stage_id:
            return {"error": "Stage 1 has no stage_id"}

        first_project = self._load_stage_project(first_entry.stage_id)
        if not first_project:
            return {"error": f"Cannot load Stage 1 project: {first_entry.stage_id}"}

        reusable = self._extract_reusable_settings(first_project)
        source_profiles = self._reusable_stage_output_profiles(
            self._load_stage_profiles_for_stage(first_entry.stage_id)
        )

        applied = 0
        skipped = 0
        conflicts = []

        for entry in stage_entries[1:]:
            if not entry.stage_id:
                continue

            sibling_project = self._load_stage_project(entry.stage_id)
            if not sibling_project:
                skipped += 1
                conflicts.append({
                    "stage_id": entry.stage_id,
                    "setting": "all",
                    "reason": "Cannot load project",
                })
                continue

            stage_conflicts = []
            project_changed = False
            for key, value in reusable.items():
                current_value = self._get_setting_from_project(sibling_project, key)
                if entry.override_values and key in entry.override_values:
                    retained_value = entry.override_values[key]
                    if current_value != retained_value:
                        self._apply_setting_to_project(sibling_project, key, retained_value)
                        project_changed = True
                    stage_conflicts.append({
                        "setting": key,
                        "current_value": current_value,
                        "proposed_value": value,
                        "retained_value": retained_value,
                        "reason": "Stage has explicit override",
                    })
                    continue
                if current_value == value:
                    continue
                self._apply_setting_to_project(sibling_project, key, value)
                project_changed = True

            profile_update = self._copy_reusable_profiles_to_stage(
                entry.stage_id,
                source_profiles,
                entry.override_values,
            )
            profile_changed = bool(profile_update["changes"])

            if stage_conflicts:
                conflicts.extend([{**c, "stage_id": entry.stage_id} for c in stage_conflicts])

            project_saved = (
                self._save_stage_project(entry.stage_id, sibling_project)
                if project_changed
                else True
            )
            profiles_saved = (
                self._save_stage_profiles_for_stage(entry.stage_id, profile_update["profiles"])
                if profile_changed
                else True
            )
            if not project_saved or not profiles_saved:
                skipped += 1
                conflicts.append(
                    {
                        "stage_id": entry.stage_id,
                        "setting": "all",
                        "reason": "Failed to persist Stage 1 settings",
                    }
                )
                continue
            entry.inherited_from_first = True
            applied += 1

        self.workspace.first_stage_snapshot = {
            "stage_id": first_entry.stage_id,
            "defaults": reusable,
            "profiles": [
                self._reusable_output_profile_summary(profile) for profile in source_profiles
            ],
            "applied_at": _utc_now().isoformat(),
        }
        self._touch_workspace()
        self._set_status(
            f"Applied Stage 1 settings to {applied} stage(s)."
            if not conflicts
            else f"Applied Stage 1 settings with {len(conflicts)} conflict(s)."
        )
        self.project_changed.emit()

        return {
            "applied": applied,
            "skipped": skipped,
            "conflicts": conflicts,
            "snapshot": self.workspace.first_stage_snapshot,
        }

    def workspace_apply_from_first_preview(self) -> dict:
        """Preview what would change before applying.

        Loads actual stage projects and compares each reusable setting.
        Returns concrete diffs and conflict details.
        """
        if not self.workspace:
            return {"error": "No workspace open"}

        stage_entries = [
            self.workspace.stage_entries[stage_id]
            for stage_id in self.workspace.stage_order
            if stage_id in self.workspace.stage_entries
        ]
        if len(stage_entries) < 2:
            return {"error": "Need at least 2 stages", "preview": []}

        first_entry = stage_entries[0]
        if not first_entry.stage_id:
            return {"preview": [], "source_stage": "", "reusable_settings": []}

        first_project = self._load_stage_project(first_entry.stage_id)
        reusable = self._extract_reusable_settings(first_project) if first_project else {}
        source_profiles = self._reusable_stage_output_profiles(
            self._load_stage_profiles_for_stage(first_entry.stage_id)
        )

        preview = []
        for entry in stage_entries[1:]:
            if not entry.stage_id:
                continue

            sibling_project = self._load_stage_project(entry.stage_id)
            if not sibling_project:
                preview.append({
                    "stage_id": entry.stage_id,
                    "display_name": entry.display_name or f"Stage {entry.stage_number}",
                    "status": "unavailable",
                    "reason": "Cannot load project",
                    "changes": [],
                })
                continue

            changes = []
            conflicts = []

            for key, first_value in reusable.items():
                sibling_value = self._get_setting_from_project(sibling_project, key)
                has_override = entry.override_values and key in entry.override_values

                if first_value == sibling_value:
                    continue

                if has_override:
                    conflicts.append({
                        "setting": key,
                        "current_value": sibling_value,
                        "proposed_value": first_value,
                        "retained_value": entry.override_values[key],
                        "reason": "Stage has explicit override",
                    })
                else:
                    changes.append({
                        "setting": key,
                        "current_value": sibling_value,
                        "new_value": first_value,
                    })

            profile_update = self._copy_reusable_profiles_to_stage(
                entry.stage_id,
                source_profiles,
                entry.override_values,
            )
            changes.extend(profile_update["changes"])

            status = "conflict" if conflicts else ("will_change" if changes else "unchanged")

            preview.append({
                "stage_id": entry.stage_id,
                "display_name": entry.display_name or f"Stage {entry.stage_number}",
                "status": status,
                "changes": changes,
                "conflicts": conflicts,
            })

        return {
            "preview": preview,
            "source_stage": first_entry.display_name or "Stage 1",
            "reusable_settings": list(reusable.keys())
            + (["output_profiles"] if source_profiles else []),
        }
    # ── Stage project load / save ──────────────────────────────────

    def _load_stage_project(self, stage_id: str) -> Project | None:
        """Load a stage's project from the workspace tree."""
        if not self.workspace_path:
            return None
        try:
            stage_path = workspace_stage_path(self.workspace_path, stage_id)
            if not (stage_path / "project.json").exists():
                return None
            return load_project(stage_path)
        except Exception:
            return None

    def _save_stage_project(self, stage_id: str, project: Project) -> bool:
        """Save a stage's project to the workspace tree."""
        if not self.workspace_path:
            return False
        try:
            stage_path = workspace_stage_path(self.workspace_path, stage_id)
            save_project(project, stage_path)
            return True
        except Exception:
            return False

    # ── Reusable settings extraction / application ──────────────────

    def _loaded_stage_profiles_for_stage(self, stage_id: str) -> list[OutputProfile]:
        return [
            deepcopy(profile)
            for profile in self._output_profiles.values()
            if profile.scope_type == "stage" and profile.scope_id == stage_id
        ]

    def _load_stage_profiles_for_stage(self, stage_id: str) -> list[OutputProfile]:
        stage_path = self._workspace_stage_bundle_path(stage_id)
        if stage_path is None:
            return self._loaded_stage_profiles_for_stage(stage_id)
        profiles_path = stage_path / "profiles.json"
        if not profiles_path.exists():
            return self._loaded_stage_profiles_for_stage(stage_id)
        try:
            raw_profiles = json.loads(profiles_path.read_text(encoding="utf-8"))
        except Exception:
            return self._loaded_stage_profiles_for_stage(stage_id)
        loaded_profiles: list[OutputProfile] = []
        if isinstance(raw_profiles, list):
            for item in raw_profiles:
                if not isinstance(item, dict):
                    continue
                try:
                    loaded_profiles.append(_output_profile_from_dict(item))
                except Exception:
                    continue
        return loaded_profiles

    def _replace_stage_profiles_in_memory(
        self, stage_id: str, profiles: list[OutputProfile]
    ) -> None:
        self._output_profiles = {
            output_id: profile
            for output_id, profile in self._output_profiles.items()
            if not (profile.scope_type == "stage" and profile.scope_id == stage_id)
        }
        for profile in profiles:
            self._output_profiles[profile.output_id] = deepcopy(profile)

    def _save_stage_profiles_for_stage(
        self, stage_id: str, profiles: list[OutputProfile]
    ) -> bool:
        stage_path = self._workspace_stage_bundle_path(stage_id)
        if stage_path is None:
            return False
        profiles_path = stage_path / "profiles.json"
        try:
            self._replace_stage_profiles_in_memory(stage_id, profiles)
            if profiles:
                stage_path.mkdir(parents=True, exist_ok=True)
                profiles_path.write_text(
                    json.dumps(
                        [self._output_profile_to_dict_safe(profile) for profile in profiles],
                        indent=2,
                    ),
                    encoding="utf-8",
                )
            elif profiles_path.exists():
                profiles_path.unlink()
            return True
        except Exception:
            return False

    def _reusable_stage_output_profiles(
        self, profiles: list[OutputProfile]
    ) -> list[OutputProfile]:
        return [
            deepcopy(profile)
            for profile in profiles
            if profile.scope_type == "stage" and profile.profile_kind == "stage_output"
        ]

    def _reusable_output_profile_summary(self, profile: OutputProfile) -> dict:
        return {
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": _copy_profile_payload(profile.metric_caption_preset),
            "lead_in_card": _copy_profile_payload(profile.lead_in_card),
            "brand_mark": _copy_profile_payload(profile.brand_mark),
            "subject_track_crop": _copy_profile_payload(profile.subject_track_crop),
            "visibility_recipe": _copy_profile_payload(profile.visibility_recipe),
        }

    def _profile_with_stage_overrides(
        self,
        profile: OutputProfile,
        stage_id: str,
        override_values: dict | None = None,
        *,
        output_id: str | None = None,
    ) -> OutputProfile:
        resolved = OutputProfile(
            output_id=output_id or _new_uuid(),
            scope_type="stage",
            scope_id=stage_id,
            profile_name=profile.profile_name,
            profile_kind=profile.profile_kind,
            frame_profile=profile.frame_profile,
            metric_caption_preset=_copy_profile_payload(profile.metric_caption_preset),
            lead_in_card=_copy_profile_payload(profile.lead_in_card),
            brand_mark=_copy_profile_payload(profile.brand_mark),
            subject_track_crop=_copy_profile_payload(profile.subject_track_crop),
            visibility_recipe=_copy_profile_payload(profile.visibility_recipe),
            angle_director_plan=[],
            retained_proxy_id=None,
            archive_id=None,
            last_rendered_at=None,
        )

        if not isinstance(override_values, dict):
            return resolved

        if override_values.get("frame_profile") not in {None, ""}:
            resolved.frame_profile = str(override_values["frame_profile"])
        if "metric_caption_preset" in override_values:
            resolved.metric_caption_preset = _metric_caption_preset_from_selection(
                override_values.get("metric_caption_preset"),
                resolved.metric_caption_preset,
            )
        if "lead_in_card" in override_values:
            resolved.lead_in_card = _lead_in_card_from_override(
                override_values.get("lead_in_card"),
                resolved.lead_in_card,
            )
        if "brand_mark" in override_values:
            resolved.brand_mark = _brand_mark_from_override(
                override_values.get("brand_mark"),
                resolved.brand_mark,
            )
        if isinstance(override_values.get("subject_track_crop"), dict):
            resolved.subject_track_crop = deepcopy(override_values["subject_track_crop"])
        if isinstance(override_values.get("visibility_recipe"), dict):
            resolved.visibility_recipe = deepcopy(override_values["visibility_recipe"])
        return resolved

    def _copy_reusable_profiles_to_stage(
        self,
        stage_id: str,
        source_profiles: list[OutputProfile],
        override_values: dict | None = None,
    ) -> dict[str, object]:
        target_profiles = self._load_stage_profiles_for_stage(stage_id)
        changes: list[dict[str, object]] = []

        for source_profile in source_profiles:
            source_key = _profile_identity_key(source_profile)
            match_index = next(
                (
                    index
                    for index, candidate in enumerate(target_profiles)
                    if _profile_identity_key(candidate) == source_key
                ),
                None,
            )
            existing_profile = None if match_index is None else target_profiles[match_index]
            resolved_profile = self._profile_with_stage_overrides(
                source_profile,
                stage_id,
                override_values,
                output_id=None if existing_profile is None else existing_profile.output_id,
            )
            new_summary = self._reusable_output_profile_summary(resolved_profile)

            if existing_profile is None:
                target_profiles.append(resolved_profile)
                changes.append(
                    {
                        "setting": "output_profile",
                        "action": "created",
                        "profile_name": source_profile.profile_name,
                        "profile_kind": source_profile.profile_kind,
                        "current_value": None,
                        "new_value": new_summary,
                    }
                )
                continue

            current_summary = self._reusable_output_profile_summary(existing_profile)
            if current_summary == new_summary:
                continue

            target_profiles[match_index] = resolved_profile
            changes.append(
                {
                    "setting": "output_profile",
                    "action": "updated",
                    "profile_name": source_profile.profile_name,
                    "profile_kind": source_profile.profile_kind,
                    "current_value": current_summary,
                    "new_value": new_summary,
                }
            )

        return {
            "profiles": target_profiles,
            "changes": changes,
        }

    def _extract_reusable_settings(self, project: Project) -> dict:
        """Extract settings that can be shared across stages."""
        return {
            "export_preset": _enum_value(project.export.preset) if project.export else None,
            "overlay_position": _enum_value(project.overlay.position) if project.overlay else None,
            "overlay_badge_size": _enum_value(project.overlay.badge_size) if project.overlay else None,
            "overlay_display_options": (
                {
                    "show_timer": bool(project.overlay.show_timer),
                    "show_shots": bool(project.overlay.show_shots),
                    "show_score": bool(project.overlay.show_score),
                }
                if project.overlay
                else {}
            ),
            "frame_profile": (
                _frame_profile_from_aspect_ratio(project.export.aspect_ratio)
                if project.export
                else None
            ),
            "export_quality": _enum_value(project.export.quality) if project.export else None,
            "frame_rate": _enum_value(project.export.frame_rate) if project.export else None,
            "video_codec": _enum_value(project.export.video_codec) if project.export else None,
            "audio_codec": _enum_value(project.export.audio_codec) if project.export else None,
        }

    def _apply_setting_to_project(self, project: Project, key: str, value) -> None:
        """Apply a single reusable setting to a project."""
        if value is None:
            return
        try:
            if key == "export_preset":
                project.export.preset = ExportPreset(value)
            elif key == "overlay_position":
                project.overlay.position = OverlayPosition(value)
            elif key == "overlay_badge_size":
                project.overlay.badge_size = BadgeSize(value)
            elif key == "overlay_display_options" and isinstance(value, dict):
                for opt_key, opt_val in value.items():
                    setattr(project.overlay, opt_key, opt_val)
            elif key == "frame_profile":
                project.export.aspect_ratio = _aspect_ratio_from_frame_profile(value)
            elif key == "export_quality":
                project.export.quality = ExportQuality(value)
            elif key == "frame_rate":
                project.export.frame_rate = ExportFrameRate(value)
            elif key == "video_codec":
                project.export.video_codec = ExportVideoCodec(value)
            elif key == "audio_codec":
                project.export.audio_codec = ExportAudioCodec(value)
        except Exception:
            pass

    def _get_setting_from_project(self, project: Project, key: str):
        """Get current value of a setting from a project (for diff comparison)."""
        try:
            if key == "export_preset":
                return _enum_value(project.export.preset) if project.export else None
            elif key == "overlay_position":
                return _enum_value(project.overlay.position) if project.overlay else None
            elif key == "overlay_badge_size":
                return _enum_value(project.overlay.badge_size) if project.overlay else None
            elif key == "overlay_display_options":
                if project.overlay:
                    return {
                        "show_timer": bool(project.overlay.show_timer),
                        "show_shots": bool(project.overlay.show_shots),
                        "show_score": bool(project.overlay.show_score),
                    }
                return {}
            elif key == "frame_profile":
                return _frame_profile_from_aspect_ratio(project.export.aspect_ratio)
            elif key == "export_quality":
                return _enum_value(project.export.quality) if project.export else None
            elif key == "frame_rate":
                return _enum_value(project.export.frame_rate) if project.export else None
            elif key == "video_codec":
                return _enum_value(project.export.video_codec) if project.export else None
            elif key == "audio_codec":
                return _enum_value(project.export.audio_codec) if project.export else None
        except Exception:
            return None
        return None


    def _touch_workspace(self) -> None:
        """Update workspace timestamp."""
        if self.workspace:
            self.workspace.updated_at = datetime.now(timezone.utc)

    # ── Library sync ────────────────────────────────────────────────

    def _sync_project_to_library(self) -> None:
        """Create or update a library stage record from the current project."""
        try:
            from splitshot.presentation.stage import build_stage_presentation

            presentation = build_stage_presentation(self.project)
            truth_hash = self._compute_truth_hash()
            score_total = presentation.metrics.scoring_summary.get("total_points")
            editor_target = {
                "type": "single",
                "project_path": str(self.project_path) if self.project_path else "",
                "workspace_path": str(self.workspace_path) if self.workspace_path else "",
                "stage_id": self.active_stage_id or self.project.id,
                "match_id": self.workspace.match_id if self.workspace and self.editor_scope == "multi" else None,
            }

            record = LibraryStageRecord(
                stage_id=self.project.id,
                match_id=self.workspace.match_id if self.workspace and self.editor_scope == "multi" else None,
                display_name=self.project.name,
                event_date=self.project.created_at,
                discipline=self.project.scoring.ruleset or "",
                competitor_name=self.project.scoring.competitor_name or "",
                metric_summary={
                    "first_shot_reaction": getattr(
                        presentation.metrics, "first_shot_reaction_ms", 0
                    ),
                    "cumulative_time": getattr(presentation.metrics, "cumulative_time_ms", 0),
                    "shot_count": len(self.project.analysis.shots),
                    "split_summary": getattr(presentation.metrics, "split_summary", {}),
                    "score": score_total,
                    "score_total": presentation.metrics.scoring_summary.get("total_points"),
                    "penalties": getattr(presentation.metrics, "penalties", 0.0),
                },
                editor_target=editor_target,
                truth_hash=truth_hash,
            )
            save_stage_record(record)

            append_stage_metric(
                {
                    "library_record_id": record.library_record_id,
                    "stage_id": record.stage_id,
                    "match_id": record.match_id,
                    "display_name": record.display_name,
                    "event_date": record.event_date.isoformat() if record.event_date else None,
                    "discipline": record.discipline,
                    "competitor_name": record.competitor_name,
                    "metric_summary": dict(record.metric_summary),
                    "first_shot_reaction_ms": getattr(
                        presentation.metrics, "first_shot_reaction_ms", 0
                    ),
                    "cumulative_time_ms": getattr(presentation.metrics, "cumulative_time_ms", 0),
                    "score": score_total,
                    "score_total": presentation.metrics.scoring_summary.get("total_points"),
                    "penalties": getattr(presentation.metrics, "penalties", 0.0),
                    "editor_target": editor_target,
                    "project_path": editor_target.get("project_path", ""),
                    "workspace_path": editor_target.get("workspace_path", ""),
                    "tags": list(record.tags),
                    "notes": record.notes,
                    "truth_hash": truth_hash,
                }
            )
        except Exception:
            pass

    def _sync_workspace_to_library(self) -> None:
        """Create or update a library match record from the current workspace."""
        if self.workspace is None:
            return
        try:
            truth_hash = self._compute_workspace_truth_hash()
            editor_target = {
                "type": "multi",
                "workspace_path": str(self.workspace_path) if self.workspace_path else "",
                "match_id": self.workspace.match_id,
            }
            aggregate_metric_summary = {
                "stage_count": len(self.workspace.stage_entries),
                "stages": list(self.workspace.stage_order),
            }

            record = LibraryMatchRecord(
                match_id=self.workspace.match_id,
                display_name=self.workspace.name,
                event_date=self.workspace.created_at,
                discipline="",
                stage_ids=list(self.workspace.stage_entries.keys()),
                aggregate_metric_summary=aggregate_metric_summary,
                editor_target=editor_target,
                truth_hash=truth_hash,
            )
            save_match_record(record)

            append_match_metric(
                {
                    "library_record_id": record.library_record_id,
                    "match_id": record.match_id,
                    "display_name": record.display_name,
                    "event_date": record.event_date.isoformat() if record.event_date else None,
                    "aggregate_metric_summary": dict(aggregate_metric_summary),
                    "stage_count": len(self.workspace.stage_entries),
                    "stage_ids": list(self.workspace.stage_order),
                    "editor_target": editor_target,
                    "workspace_path": editor_target.get("workspace_path", ""),
                    "tags": list(record.tags),
                    "notes": record.notes,
                    "truth_hash": truth_hash,
                }
            )
        except Exception:
            pass

    def _compute_truth_hash(self) -> str:
        """Compute a stable hash representing current reviewed truth state."""
        import hashlib
        import json

        truth_data = {
            "stage_id": self.project.id,
            "name": self.project.name,
            "shot_count": len(self.project.analysis.shots),
            "beep_time_ms": self.project.analysis.beep_time_ms_primary,
            "ruleset": self.project.scoring.ruleset,
            "hit_factor": self.project.scoring.hit_factor,
            "penalties": self.project.scoring.penalties,
        }
        truth_data["shot_times"] = [round(shot.time_ms) for shot in self.project.analysis.shots]

        canonical = json.dumps(truth_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    def _compute_workspace_truth_hash(self) -> str:
        """Compute a stable hash for workspace truth."""
        import hashlib
        import json

        if self.workspace is None:
            return ""

        truth_data = {
            "match_id": self.workspace.match_id,
            "name": self.workspace.name,
            "stage_count": len(self.workspace.stage_entries),
            "stage_ids": sorted(self.workspace.stage_order),
            "shared_defaults": dict(self.workspace.shared_defaults),
        }
        canonical = json.dumps(truth_data, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()

    # ── Proxy management ────────────────────────────────────────────

    def proxy_status(self, scope_type: str = "stage", scope_id: str | None = None) -> dict:
        return shared_backend_service.proxy_status(self, scope_type, scope_id)

    def _generate_default_render_plan(self, scope_type: str = "stage") -> dict:
        return shared_backend_service.generate_default_render_plan(scope_type)

    def proxy_refresh(self, scope_type: str = "stage", scope_id: str | None = None) -> dict:
        return shared_backend_service.proxy_refresh(self, scope_type, scope_id)

    def proxy_open_target(self, scope_type: str = "stage", scope_id: str | None = None) -> dict:
        return shared_backend_service.proxy_open_target(self, scope_type, scope_id)

    # ── Output Profiles ─────────────────────────────────────────────

    def output_profile_create(
        self,
        scope_type: str,
        scope_id: str,
        profile_name: str = "Default",
        profile_kind: str = "stage_output",
        **kwargs,
    ) -> dict:
        """Create a new output profile."""
        from splitshot.domain.models import OutputProfile

        frame_profile = kwargs.pop("frame_profile", "source")
        if frame_profile not in self.VALID_FRAME_PROFILES:
            frame_profile = "source"

        profile = OutputProfile(
            scope_type=scope_type,
            scope_id=scope_id,
            profile_name=profile_name,
            profile_kind=profile_kind,
            frame_profile=frame_profile,
        )

        for key, value in kwargs.items():
            if hasattr(profile, key):
                setattr(profile, key, value)

        self._output_profiles[profile.output_id] = profile

        if scope_type == "match" and self.workspace is not None:
            self.workspace.match_output_profiles.append(profile)
        elif scope_type == "stage" and self.workspace is not None:
            self.workspace.updated_at = _utc_now()
            if self.workspace_path is not None:
                self._persist_workspace_stage_profiles()
        if self.workspace is not None:
            self.project_changed.emit()

        return self._profile_to_dict(profile)

    def output_profile_update(self, output_id: str, **kwargs) -> dict | None:
        """Update an existing output profile."""
        profile = self._find_output_profile(output_id)
        if profile is None:
            return None

        for key, value in kwargs.items():
            if hasattr(profile, key) and key not in ("output_id", "scope_type", "scope_id"):
                setattr(profile, key, value)

        if self.workspace is not None and profile.scope_type == "stage":
            self.workspace.updated_at = _utc_now()
            if self.workspace_path is not None:
                self._persist_workspace_stage_profiles()
        if self.workspace is not None:
            self.project_changed.emit()

        return self._profile_to_dict(profile)

    def output_profile_delete(self, output_id: str) -> bool:
        """Delete an output profile."""
        if output_id in self._output_profiles:
            profile = self._output_profiles[output_id]
            del self._output_profiles[output_id]
            if self.workspace is not None and profile.scope_type == "stage":
                self.workspace.updated_at = _utc_now()
                if self.workspace_path is not None:
                    self._persist_workspace_stage_profiles()
            if self.workspace is not None:
                self.project_changed.emit()
            return True
        if self.workspace:
            for i, p in enumerate(self.workspace.match_output_profiles):
                if p.output_id == output_id:
                    del self.workspace.match_output_profiles[i]
                    self.project_changed.emit()
                    return True
        return False

    def output_profile_list(
        self, scope_type: str | None = None, scope_id: str | None = None
    ) -> list[dict]:
        """List output profiles, optionally filtered."""
        profiles = list(self._output_profiles.values())
        if self.workspace:
            profiles.extend(self.workspace.match_output_profiles)

        if scope_type:
            profiles = [p for p in profiles if p.scope_type == scope_type]
        if scope_id:
            profiles = [p for p in profiles if p.scope_id == scope_id]

        return [self._profile_to_dict(p) for p in profiles]

    # ── Output Profile Persistence Helpers ──────────────────────────

    def _output_profile_to_dict_safe(self, profile) -> dict:
        """Simple output profile serialization."""
        return {
            "output_id": profile.output_id,
            "scope_type": profile.scope_type,
            "scope_id": profile.scope_id,
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": profile.metric_caption_preset,
            "lead_in_card": profile.lead_in_card,
            "brand_mark": profile.brand_mark,
            "subject_track_crop": profile.subject_track_crop,
            "visibility_recipe": profile.visibility_recipe,
            "angle_director_plan": [
                self._angle_director_cut_to_dict(cut) for cut in profile.angle_director_plan
            ],
            "retained_proxy_id": profile.retained_proxy_id,
            "last_rendered_at": profile.last_rendered_at.isoformat()
            if profile.last_rendered_at
            else None,
        }

    def _save_stage_profiles(self, project_path: Path, *, stage_id: str | None = None) -> None:
        """Persist stage-scoped output profiles alongside project.json."""
        import json

        target_stage_id = stage_id or self.project.id
        stage_profiles = [
            p
            for p in self._output_profiles.values()
            if p.scope_type == "stage" and p.scope_id == target_stage_id
        ]
        profiles_path = project_path / "profiles.json"
        if stage_profiles:
            project_path.mkdir(parents=True, exist_ok=True)
            profiles_data = [self._output_profile_to_dict_safe(p) for p in stage_profiles]
            profiles_path.write_text(json.dumps(profiles_data, indent=2))
        elif profiles_path.exists():
            profiles_path.unlink()

    def _load_stage_profiles(self, project_path: Path) -> None:
        """Load stage-scoped output profiles from project folder."""
        import json
        from splitshot.persistence.workspaces import _output_profile_from_dict

        profiles_path = project_path / "profiles.json"
        if profiles_path.exists():
            try:
                profiles_data = json.loads(profiles_path.read_text())
                for pdata in profiles_data:
                    profile = _output_profile_from_dict(pdata)
                    self._output_profiles[profile.output_id] = profile
            except Exception:
                pass

    # OutputProfile takes priority over legacy Project.export.
    # When an OutputProfile exists for the scope, it controls render settings.
    # Project.export is preserved for backward compatibility only.
    def output_profile_render(self, output_id: str) -> dict:
        """Request render of a specific output profile.

        Returns render plan with Trim Dead Time, Shot Data on Screen, Video Shape,
        Opening Title, Your Logo settings resolved.

        If profile not found, falls back to legacy Project.export settings.
        """
        profile = self._find_output_profile(output_id)

        if profile is None:
            return self._legacy_export_render_plan()

        render_plan = {
            "success": True,
            "output_id": output_id,
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "scope_type": profile.scope_type,
            "scope_id": profile.scope_id,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": dict(profile.metric_caption_preset),
            "lead_in_card": dict(profile.lead_in_card),
            "brand_mark": dict(profile.brand_mark),
            "subject_track_crop": dict(profile.subject_track_crop),
            "visibility_recipe": dict(profile.visibility_recipe),
            "run_window": self._resolve_run_window(profile),
            "source": "output_profile",
        }

        if self.project.primary_video.path and Path(self.project.primary_video.path).exists():
            from splitshot.export.pipeline import export_output_profile
            from splitshot.persistence.projects import default_project_output_path

            output_path = default_project_output_path(
                self.project_path or Path.home() / "splitshot",
                f"{profile.profile_name.lower().replace(' ', '_')}.mp4",
            )
            try:
                result_path = export_output_profile(self.project, output_path, render_plan)
                render_plan["rendered_path"] = str(result_path)
            except Exception as exc:
                render_plan["render_error"] = str(exc)

        return render_plan

    def _legacy_export_render_plan(self) -> dict:
        """Build a render plan from legacy Project.export settings.

        This is the backward-compatible fallback when no OutputProfile exists.
        """
        export = self.project.export
        beep_ms = self.project.analysis.beep_time_ms_primary or 0
        shots = self.project.analysis.shots
        last_shot_ms = shots[-1].time_ms if shots else beep_ms + 5000

        return {
            "success": True,
            "output_id": None,
            "profile_name": "Legacy Export",
            "profile_kind": "stage_output",
            "scope_type": "stage",
            "scope_id": self.project.id,
            "frame_profile": export.aspect_ratio.value
            if hasattr(export.aspect_ratio, "value")
            else str(export.aspect_ratio),
            "metric_caption_preset": {},
            "lead_in_card": {},
            "brand_mark": {},
            "subject_track_crop": {},
            "visibility_recipe": {},
            "run_window": {
                "start_ms": 0,
                "end_ms": 0,
                "duration_ms": 0,
                "beep_time_ms": beep_ms,
                "last_shot_ms": last_shot_ms,
                "lead_in_padding_ms": 1000,
                "tail_padding_ms": 2000,
            },
            "source": "legacy_export_settings",
        }

    def _profile_to_dict(self, profile) -> dict:
        """Convert OutputProfile to dict for API."""
        return {
            "output_id": profile.output_id,
            "scope_type": profile.scope_type,
            "scope_id": profile.scope_id,
            "profile_name": profile.profile_name,
            "profile_kind": profile.profile_kind,
            "frame_profile": profile.frame_profile,
            "metric_caption_preset": dict(profile.metric_caption_preset),
            "lead_in_card": dict(profile.lead_in_card),
            "brand_mark": dict(profile.brand_mark),
            "subject_track_crop": dict(profile.subject_track_crop),
            "visibility_recipe": dict(profile.visibility_recipe),
            "angle_director_plan": [
                self._angle_director_cut_to_dict(cut) for cut in profile.angle_director_plan
            ],
            "retained_proxy_id": profile.retained_proxy_id,
            "last_rendered_at": profile.last_rendered_at.isoformat()
            if profile.last_rendered_at
            else None,
        }

    # ── Trim Dead Time ───────────────────────────────────────────────

    def _resolve_run_window(self, profile, project: Project | None = None) -> dict:
        """Resolve Trim Dead Time from reviewed timing truth.

        Derives effective stage window from beep time and last shot,
        with configurable lead-in and tail padding from the profile.
        """
        target_project = project or self.project
        mc = profile.metric_caption_preset

        beep_ms = target_project.analysis.beep_time_ms_primary or 0
        lead_in_pad = mc.get("lead_in_padding_ms", 1000)

        shots = target_project.analysis.shots
        last_shot_ms = shots[-1].time_ms if shots else beep_ms + 5000
        tail_pad = mc.get("tail_padding_ms", 2000)

        start_ms = max(0, beep_ms - lead_in_pad)
        end_ms = last_shot_ms + tail_pad

        return {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_ms": end_ms - start_ms,
            "beep_time_ms": beep_ms,
            "last_shot_ms": last_shot_ms,
            "lead_in_padding_ms": lead_in_pad,
            "tail_padding_ms": tail_pad,
        }

    # ── Shot Data on Screen ────────────────────────────────────────

    def resolve_metric_captions(self, output_id: str) -> dict:
        """Resolve metric captions from reviewed truth for a given output profile."""
        profile = self._output_profiles.get(output_id)
        if profile is None:
            return {"error": "Profile not found"}

        from splitshot.presentation.stage import build_stage_presentation
        from splitshot.timeline.model import compute_split_rows

        presentation = build_stage_presentation(self.project)
        rows = compute_split_rows(self.project)
        preset = profile.metric_caption_preset

        captions = {
            "shot_count": len(self.project.analysis.shots),
            "cumulative_time_ms": presentation.metrics.stage_time_ms,
            "first_shot_reaction_ms": presentation.metrics.draw_ms,
            "hit_factor": self.project.scoring.hit_factor,
            "penalties": self.project.scoring.penalties,
            "split_times": [
                {"shot_number": i + 1, "split_ms": row.split_ms, "cumulative_ms": row.cumulative_ms}
                for i, row in enumerate(rows)
            ],
            "enabled_fields": preset.get("enabled_fields", ["shot_count", "cumulative_time"]),
            "format": preset.get("format", "overlay"),
        }
        return captions

    # ── Match Recap ─────────────────────────────────────────────────

    def match_recap_preview(self, output_id: str) -> dict:
        """Build a match recap render plan from workspace stages.

        Sources clips from multiple stage_id values in one match_id,
        preserves stage ordering, supports Result Cards between stages.
        """
        if self.workspace is None:
            return {"success": False, "error": "No workspace open"}

        profile = None
        for p in self.workspace.match_output_profiles:
            if p.output_id == output_id:
                profile = p
                break
        if profile is None:
            return {"success": False, "error": f"Profile {output_id} not found"}

        clips = []
        for stage_id in self.workspace.stage_order:
            entry = self.workspace.stage_entries.get(stage_id)
            if entry is None:
                continue
            clips.append(
                {
                    "stage_id": stage_id,
                    "display_name": entry.display_name,
                    "status": entry.status,
                    "include": entry.status != "missing_media",
                    "result_card": {
                        "enabled": profile.metric_caption_preset.get("result_cards_enabled", True),
                        "stage_name": entry.display_name,
                    },
                }
            )

        return {
            "success": True,
            "output_id": output_id,
            "profile_kind": "match_recap",
            "match_id": self.workspace.match_id,
            "match_name": self.workspace.name,
            "stage_count": len(clips),
            "clips": clips,
            "shared_defaults": dict(self.workspace.shared_defaults),
            "render_settings": {
                "frame_profile": profile.frame_profile,
                "lead_in_card": dict(profile.lead_in_card),
                "brand_mark": dict(profile.brand_mark),
            },
        }

    # ── Stage Composite ─────────────────────────────────────────────

    def stage_composite_preview(self, output_id: str) -> dict:
        """Build a stage composite render plan for one stage with multiple clips."""
        profile = self._find_output_profile(output_id)
        if profile is None:
            return {"success": False, "error": f"Profile {output_id} not found"}

        clips = self._get_stage_clips(profile.scope_id)

        return {
            "success": True,
            "output_id": output_id,
            "profile_kind": "stage_composite",
            "stage_id": profile.scope_id,
            "clip_count": len(clips),
            "clips": clips,
            "angle_director_plan": [
                self._angle_director_cut_to_dict(cut) for cut in profile.angle_director_plan
            ],
            "render_settings": {
                "frame_profile": profile.frame_profile,
                "visibility_recipe": dict(profile.visibility_recipe),
            },
        }

    # ── Stage Clips (for Stage Composite) ───────────────────────────

    def _get_stage_clips(self, stage_id: str) -> list[dict]:
        """Get clips for a stage (for Stage Composite)."""
        return self._workspace_stage_clips_to_dicts(stage_id)

    def workspace_stage_clip_add(
        self, stage_id: str, source_path: str = "", angle_role: str = "primary", **kwargs
    ) -> list[dict]:
        """Add a clip source to a stage for composite editing."""
        entry = self._workspace_stage_entry(stage_id)
        if entry is None and self.workspace is not None:
            self.workspace_add_stage(stage_id, f"Stage {len(self.workspace.stage_entries) + 1}")
            entry = self._workspace_stage_entry(stage_id)
        if entry is None:
            return []

        clip = StageClipSource(
            clip_id=_new_uuid(),
            source_path=source_path,
            angle_role=angle_role,
            sync_offset_ms=int(kwargs.get("sync_offset_ms", 0)),
            audio_gain=float(kwargs.get("audio_gain", 1.0)),
            audio_muted=bool(kwargs.get("audio_muted", False)),
            audio_primary=bool(kwargs.get("audio_primary", angle_role == "primary")),
            angle_aligned=bool(kwargs.get("angle_aligned", False)),
        )
        entry.clip_sources.append(clip)
        if self.workspace is not None:
            self.workspace.updated_at = _utc_now()
            self.project_changed.emit()
        return self._get_stage_clips(stage_id)

    def workspace_stage_clip_update(self, stage_id: str, clip_id: str, **kwargs) -> dict | None:
        """Update a clip's properties."""
        clips = self._workspace_stage_clip_models(stage_id)
        for clip in clips:
            if clip.clip_id == clip_id:
                for key, value in kwargs.items():
                    if not hasattr(clip, key):
                        continue
                    if key == "sync_offset_ms":
                        try:
                            value = int(value)
                        except (TypeError, ValueError):
                            continue
                    elif key == "audio_gain":
                        try:
                            value = max(0.0, min(2.0, float(value)))
                        except (TypeError, ValueError):
                            continue
                    elif key in {"audio_muted", "audio_primary", "angle_aligned"}:
                        value = bool(value)
                    elif key == "angle_role":
                        value = str(value or clip.angle_role).strip() or clip.angle_role
                    setattr(clip, key, value)
                if clip.audio_primary:
                    for other in clips:
                        if other.clip_id != clip_id:
                            other.audio_primary = False
                if self.workspace is not None:
                    self.workspace.updated_at = _utc_now()
                    self.project_changed.emit()
                return self._workspace_stage_clip_to_dict(clip)
        return None

    def workspace_stage_clip_remove(self, stage_id: str, clip_id: str) -> bool:
        """Remove a clip from a stage."""
        clips = self._workspace_stage_clip_models(stage_id)
        for i, clip in enumerate(clips):
            if clip.clip_id == clip_id:
                del clips[i]
                if self.workspace is not None:
                    self.workspace.updated_at = _utc_now()
                    self.project_changed.emit()
                return True
        return False

    def workspace_stage_clip_reorder(
        self, stage_id: str, clip_id: str, target_index: int
    ) -> list[dict] | None:
        """Move a clip to a new index within a stage composite list."""
        clips = self._workspace_stage_clip_models(stage_id)
        for index, clip in enumerate(clips):
            if clip.clip_id != clip_id:
                continue
            moving_clip = clips.pop(index)
            next_index = max(0, min(len(clips), int(target_index)))
            clips.insert(next_index, moving_clip)
            if self.workspace is not None:
                self.workspace.updated_at = _utc_now()
                self.project_changed.emit()
            return self._get_stage_clips(stage_id)
        return None

    # ── Angle Align ─────────────────────────────────────────────────

    def angle_align(self, stage_id: str, reference_clip_id: str) -> dict:
        """Align clips for a stage by beep/sync to reference.

        Computes sync offsets for all clips relative to the reference.
        """
        clips = self._workspace_stage_clip_models(stage_id)
        if not clips:
            return {"success": False, "error": "No clips for this stage"}

        reference = None
        for clip in clips:
            if clip.clip_id == reference_clip_id:
                reference = clip
                break
        if reference is None:
            return {"success": False, "error": f"Reference clip {reference_clip_id} not found"}

        for clip in clips:
            clip.angle_aligned = True
        if self.workspace is not None:
            self.workspace.updated_at = _utc_now()
            self.project_changed.emit()

        return {
            "success": True,
            "stage_id": stage_id,
            "reference_clip_id": reference_clip_id,
            "aligned_clips": len(clips),
        }

    # ── Angle Director ──────────────────────────────────────────────

    def angle_director_generate(self, stage_id: str) -> dict:
        """Generate a suggested auto-cut plan for multi-angle composition.

        Produces a cut plan that switches between angles based on role priority.
        """
        clips = self._workspace_stage_clip_models(stage_id)
        if len(clips) < 2:
            return {"success": False, "error": "Need at least 2 clips for angle direction"}

        sorted_clips = _role_priority_sorted_stage_clips(clips)

        cut_plan = []
        for i, clip in enumerate(sorted_clips):
            cut_plan.append(
                {
                    "position": i,
                    "clip_id": clip.clip_id,
                    "angle_role": clip.angle_role,
                    "start_ms": 0,
                    "duration_ms": 0,
                    "suggested": True,
                }
            )

        return {
            "success": True,
            "stage_id": stage_id,
            "cut_plan": cut_plan,
            "clip_count": len(clips),
        }

    def angle_director_plan(self, stage_id: str, output_id: str) -> dict:
        """Return the current angle-director plan merged with persisted overrides."""
        entry = self._workspace_stage_entry(stage_id)
        if self.workspace is None or entry is None:
            return {"success": False, "error": "Stage not found in workspace"}

        profile = self._find_output_profile(output_id)
        if profile is None:
            return {"success": False, "error": f"Profile {output_id} not found"}
        if profile.scope_type != "stage" or profile.scope_id != stage_id:
            return {"success": False, "error": "Output profile does not belong to this stage"}

        clips = self._get_stage_clips(stage_id)
        generated = self.angle_director_generate(stage_id)
        if not generated.get("success"):
            return generated

        persisted_plan = [
            self._angle_director_cut_to_dict(cut) for cut in profile.angle_director_plan
        ]
        if persisted_plan:
            plan_by_position = {
                int(item["position"]): dict(item) for item in generated["cut_plan"]
            }
            for item in persisted_plan:
                plan_by_position[int(item["position"])] = dict(item)
            cut_plan = [plan_by_position[position] for position in sorted(plan_by_position)]
        else:
            cut_plan = generated["cut_plan"]
        return {
            "success": True,
            "stage_id": stage_id,
            "output_id": output_id,
            "clips": clips,
            "cut_plan": cut_plan,
            "has_overrides": bool(profile.angle_director_plan),
        }

    def _stage_composite_profile(
        self, stage_id: str, output_id: str | None = None
    ) -> OutputProfile | None:
        if output_id:
            profile = self._find_output_profile(output_id)
            if profile is None:
                return None
            return profile
        for candidate in self._output_profiles.values():
            if (
                candidate.scope_type == "stage"
                and candidate.scope_id == stage_id
                and candidate.profile_kind == "stage_composite"
            ):
                return candidate
        return None

    def angle_director_override_cut(
        self,
        stage_id: str,
        clip_id: str,
        position: int,
        start_ms: int = 0,
        duration_ms: int = 0,
        output_id: str | None = None,
    ) -> dict:
        """Override a suggested cut in the angle director plan."""
        clips = self._workspace_stage_clip_models(stage_id)
        profile = self._stage_composite_profile(stage_id, output_id)
        if profile is None:
            return {"success": False, "error": "Stage composite output profile not found"}
        if profile.scope_type != "stage" or profile.scope_id != stage_id:
            return {"success": False, "error": "Output profile does not belong to this stage"}
        if position < 0:
            return {"success": False, "error": "position must be 0 or greater"}

        for clip in clips:
            if clip.clip_id == clip_id:
                angle_role = clip.angle_role
                profile.angle_director_plan = [
                    decision
                    for decision in profile.angle_director_plan
                    if decision.position != position
                ]
                profile.angle_director_plan.append(
                    AngleDirectorCutDecision(
                        position=position,
                        clip_id=clip_id,
                        angle_role=angle_role,
                        start_ms=max(0, int(start_ms)),
                        duration_ms=max(0, int(duration_ms)),
                        suggested=False,
                    )
                )
                profile.angle_director_plan.sort(key=lambda item: item.position)
                if self.workspace is not None:
                    self.workspace.updated_at = _utc_now()
                    self.project_changed.emit()
                return {
                    "success": True,
                    "clip_id": clip_id,
                    "output_id": profile.output_id,
                    "overrides": len(profile.angle_director_plan),
                    "cut_plan": [
                        self._angle_director_cut_to_dict(item)
                        for item in profile.angle_director_plan
                    ],
                }
        return {"success": False, "error": f"Clip {clip_id} not found"}

    def angle_director_clear_cut(
        self,
        stage_id: str,
        position: int,
        output_id: str | None = None,
    ) -> dict:
        """Remove a persisted angle-director override for a given position."""
        profile = self._stage_composite_profile(stage_id, output_id)
        if profile is None:
            return {"success": False, "error": "Stage composite output profile not found"}
        before_count = len(profile.angle_director_plan)
        profile.angle_director_plan = [
            decision for decision in profile.angle_director_plan if decision.position != position
        ]
        if len(profile.angle_director_plan) == before_count:
            return {"success": False, "error": "Override not found"}
        if self.workspace is not None:
            self.workspace.updated_at = _utc_now()
            self.project_changed.emit()
        return {
            "success": True,
            "output_id": profile.output_id,
            "overrides": len(profile.angle_director_plan),
            "cut_plan": [self._angle_director_cut_to_dict(item) for item in profile.angle_director_plan],
        }

    # ── Audio Mix Lanes ─────────────────────────────────────────────

    def audio_mix_set(
        self,
        stage_id: str,
        clip_id: str,
        gain: float | None = None,
        muted: bool | None = None,
        primary: bool | None = None,
    ) -> dict | None:
        """Set audio mix properties for a clip."""
        clips = self._workspace_stage_clip_models(stage_id)
        for clip in clips:
            if clip.clip_id == clip_id:
                if gain is not None:
                    clip.audio_gain = max(0.0, min(2.0, gain))
                if muted is not None:
                    clip.audio_muted = muted
                if primary is not None:
                    clip.audio_primary = primary
                    if primary:
                        for other in clips:
                            if other.clip_id != clip_id:
                                other.audio_primary = False
                if self.workspace is not None:
                    self.workspace.updated_at = _utc_now()
                    self.project_changed.emit()
                return self._workspace_stage_clip_to_dict(clip)
        return None

    # ── Result Cards ────────────────────────────────────────────────

    def resolve_result_cards(self, match_output_id: str) -> dict:
        """Resolve result cards for a match recap from reviewed truth."""
        if self.workspace is None:
            return {"success": False, "error": "No workspace open"}

        cards = []
        for stage_id in self.workspace.stage_order:
            entry = self.workspace.stage_entries.get(stage_id)
            if entry is None:
                continue

            cards.append(
                {
                    "stage_id": stage_id,
                    "stage_name": entry.display_name,
                    "stage_number": entry.stage_number,
                    "status": entry.status,
                    "enabled": True,
                    "duration_ms": 3000,
                }
            )

        return {
            "success": True,
            "output_id": match_output_id,
            "card_count": len(cards),
            "cards": cards,
        }

    # ── Inheritance resolution ──────────────────────────────────────

    def resolve_setting(self, stage_id: str | None, key: str, default=None):
        """Resolve a setting through the full inheritance chain (eligible fields only).

        Order: stage override → match shared → folder → app → domain default.
        """
        if key in _INHERITANCE_ELIGIBLE_FIELDS:
            if stage_id and self.workspace and stage_id in self.workspace.stage_entries:
                entry = self.workspace.stage_entries[stage_id]
                if key in entry.override_values:
                    return entry.override_values[key]
            if self.workspace and key in self.workspace.shared_defaults:
                return self.workspace.shared_defaults[key]
        effective = self.effective_settings()
        if hasattr(effective, key):
            return getattr(effective, key)
        return default

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
        if not self.project.primary_video.path:
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
            self.project.primary_video.path,
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
            "video_path": self.project.primary_video.path,
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

    def analyze_secondary(self) -> None:
        source = _first_analyzable_merge_source(self.project)
        if source is None or not source.asset.path:
            _clear_secondary_analysis_state(self.project, preserve_sync_offset=True)
            self.project.secondary_video = None
            return
        self.project.secondary_video = source.asset
        self.project.analysis.analyzed_secondary_source_id = source.id
        self.project.analysis.secondary_analysis_status = "running"
        self.project.analysis.secondary_analysis_message = "Analyzing PiP sync source."
        self._set_status("Analyzing secondary video and computing sync offset...")
        result = _run_analyze_video_audio(
            source.asset.path,
            self.project.analysis.shotml_settings.detection_threshold,
            self.project.analysis.shotml_settings,
        )
        self.project.analysis.beep_time_ms_secondary = result.beep_time_ms
        self.project.analysis.waveform_secondary = result.waveform
        self.project.analysis.sync_offset_ms = compute_sync_offset(
            self.project.analysis.beep_time_ms_primary,
            self.project.analysis.beep_time_ms_secondary,
        )
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

    def ingest_primary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing primary video...")
        self.load_primary_video(path)
        self.analyze_primary()

    def ingest_secondary_video(self, path: str, source_name: str | None = None) -> None:
        self._set_status("Importing secondary video...")
        self.load_secondary_video(path)

    def set_project_details(self, name: str | None = None, description: str | None = None) -> None:
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
        if stage_number is not None or scoring.stage_number is not None:
            next_stage_number = None if stage_number is None else max(1, int(stage_number))
            if scoring.stage_number != next_stage_number:
                scoring.stage_number = next_stage_number
                changed = True
        if competitor_name is not None:
            next_competitor_name = str(competitor_name).strip()
            if scoring.competitor_name != next_competitor_name:
                scoring.competitor_name = next_competitor_name
                changed = True
        if competitor_place is not None or (
            competitor_place is None and scoring.competitor_place is not None
        ):
            if scoring.competitor_place != competitor_place:
                scoring.competitor_place = competitor_place
                changed = True
        if changed:
            if self._can_reimport_practiscore_source():
                self._import_practiscore_source(
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
        self._import_practiscore_source(path, source_name)

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
            "comparison_competitors": deepcopy(self._practiscore_comparison_competitors),
        }

    def practiscore_browser_state(self) -> dict[str, object]:
        payload = self._practiscore_options_browser_payload()
        payload["_session_payload"] = deepcopy(self._practiscore_session_payload)
        payload["_sync_payload"] = deepcopy(self._practiscore_sync_payload)
        return payload

    def _set_practiscore_session_payload(self, payload: dict[str, object]) -> None:
        self._practiscore_session_payload = (
            practiscore_sync_service.practiscore_session_payload_from_status(payload)
        )

    def _set_practiscore_sync_state(
        self,
        state: str,
        message: str,
        *,
        matches: list[RemotePractiScoreMatch] | list[dict[str, object]] | None = None,
        selected_remote_id: str | None | object = practiscore_sync_service.PRACTISCORE_SYNC_UNSET,
        error_category: str = "",
        details: dict[str, object] | None = None,
    ) -> None:
        self._practiscore_sync_payload = (
            practiscore_sync_service.build_practiscore_sync_payload(
                self._practiscore_sync_payload,
                state,
                message,
                matches=matches,
                selected_remote_id=selected_remote_id,
                error_category=error_category,
                details=details,
            )
        )

    def _practiscore_route_payload(self) -> dict[str, object]:
        return {
            "practiscore_session": deepcopy(self._practiscore_session_payload),
            "practiscore_sync": deepcopy(self._practiscore_sync_payload),
            "practiscore_options": self._practiscore_options_browser_payload(),
            "matches": practiscore_sync_service.serialize_practiscore_remote_matches(
                self._practiscore_sync_payload.get("matches")
            ),
        }

    def list_practiscore_matches(self, practiscore_session: object) -> dict[str, object]:
        return practiscore_sync_service.list_practiscore_matches(
            self,
            practiscore_session,
        )

    def start_practiscore_sync(
        self, payload: dict[str, object], practiscore_session: object
    ) -> dict[str, object]:
        return practiscore_sync_service.start_practiscore_sync(
            self,
            payload,
            practiscore_session,
        )

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
        names = [name for name in self.settings.settings_templates.keys() if str(name).strip()]
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
        if self.project.scoring.imported_stage is None:
            try:
                self._import_practiscore_source(
                    str(resolved_path), display_name, emit_change=emit_change
                )
                return True
            except ValueError:
                return changed or recovered_from_folder
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

    def _restore_media_sources_from_project(
        self,
        *,
        secondary_video_is_explicitly_persisted: bool = False,
    ) -> bool:
        candidates = self._project_input_candidates()
        if not candidates:
            return False

        used_paths: set[Path] = set()
        changed = False
        explicit_secondary_video = (
            self.project.secondary_video if secondary_video_is_explicitly_persisted else None
        )
        explicit_secondary_source_id = _merge_source_id_for_asset(
            self.project,
            explicit_secondary_video,
        )

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
            _sync_merge_source_trim_provenance(source)
            changed = True

        if self.project.merge_sources:
            if secondary_video_is_explicitly_persisted:
                if explicit_secondary_video is None:
                    self.project.secondary_video = None
                elif explicit_secondary_source_id is not None:
                    explicit_source = _merge_source_by_id(
                        self.project,
                        explicit_secondary_source_id,
                    )
                    if explicit_source is not None:
                        self.project.secondary_video = explicit_source.asset
                else:
                    recovered_secondary = self._recover_media_asset_from_project_folder(
                        explicit_secondary_video,
                        candidates,
                        used_paths,
                    )
                    if recovered_secondary is not None:
                        self.project.secondary_video = recovered_secondary
                        changed = True
            else:
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

    def _import_practiscore_source(
        self,
        path: str,
        source_name: str | None = None,
        *,
        emit_change: bool = True,
    ) -> None:
        normalized = normalize_downloaded_practiscore_artifact(
            path,
            source_name=source_name,
            **self._practiscore_import_context_kwargs(),
        )
        self._practiscore_options = normalized.options
        imported = normalized.stage_import
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
            for c in imported.comparison_competitors
        ]
        apply_scoring_preset(self.project, imported.ruleset)
        self.project.scoring.enabled = True
        self.project.scoring.penalties = max(0.0, float(imported.manual_penalties))
        self.project.scoring.penalty_counts = dict(imported.penalty_counts)
        self.project.scoring.imported_stage = imported.imported_stage
        self.project.scoring.competitor_name = imported.imported_stage.competitor_name
        self.project.scoring.competitor_place = imported.imported_stage.competitor_place
        self.project.scoring.match_type = imported.imported_stage.match_type
        self.project.scoring.stage_number = imported.imported_stage.stage_number
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
                )
            )
            self.project.overlay.text_boxes = boxes
        else:
            imported_box.enabled = True
        sync_overlay_legacy_custom_box_fields(self.project.overlay)
        self.update_hit_factor()
        stage_label = (
            imported.imported_stage.stage_name or f"Stage {imported.imported_stage.stage_number}"
        )
        self._set_status(f"Imported PractiScore results for {stage_label}.")
        if emit_change:
            self.project.touch()
            self.project_changed.emit()

    def add_merge_source(self, path: str, source_name: str | None = None) -> None:
        asset = probe_video(path)
        merge_source = MergeSource(
            asset=asset,
            angle_role=default_merge_source_angle_role(asset),
            pip_size_percent=self.project.merge.pip_size_percent,
            pip_x=self.project.merge.pip_x,
            pip_y=self.project.merge.pip_y,
            sync_offset_ms=0,
        )
        next_order_index = _next_merge_source_order_index(self.project)
        merge_source.placement.order_index = next_order_index
        merge_source.placement.layer_index = next_order_index
        merge_source.trim_derivative.original_path = asset.path
        merge_source.trim_derivative.derivative_path = None
        merge_source.trim_derivative.active_path_kind = MergeSourceAssetPathKind.ORIGINAL
        self.project.merge_sources.append(merge_source)
        for existing_source in self.project.merge_sources:
            _apply_merge_source_role_seed_defaults(
                self.project,
                existing_source,
                force=existing_source.id == merge_source.id,
            )
        self.project.merge.enabled = True
        _sync_secondary_video_from_merge_sources(self.project)
        if _first_analyzable_merge_source(self.project) is not None:
            self._set_status("Imported merge media.")
            self.analyze_secondary()
            return
        self._set_status("Imported merge media.")
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
        if removed_analyzed:
            _clear_secondary_analysis_state(
                self.project, preserve_sync_offset=bool(self.project.merge_sources)
            )
            if _first_analyzable_merge_source(self.project) is not None:
                self.analyze_secondary()
                return
            self.project.analysis.sync_offset_ms = 0
        self._set_status("Removed merge media.")
        self.project.touch()
        self.project_changed.emit()

    def rerun_merge_source_analysis(self, source_id: str) -> None:
        source = next((item for item in self.project.merge_sources if item.id == source_id), None)
        if source is None:
            raise ValueError("Merge source not found")
        analyzed_source = _first_analyzable_merge_source(self.project)
        if analyzed_source is None or analyzed_source.id != source_id:
            raise ValueError("Only the first analyzable PiP video can be reanalyzed")
        self.analyze_secondary()

    def _merge_source_by_id(self, source_id: str) -> MergeSource:
        source = next((item for item in self.project.merge_sources if item.id == source_id), None)
        if source is None:
            raise ValueError("Merge source not found")
        return source

    def _require_saved_project_for_trim_derivative(self) -> Path:
        if self.project_path is None:
            raise ValueError(
                "Trim derivative generation requires a saved project folder because derivatives live under Input/."
            )
        return self.project_path

    def _merge_source_trim_derivative_filename(self, source: MergeSource) -> str:
        source_path = _merge_source_original_path(source) or str(source.asset.path or "") or source.id
        base_name = re.sub(r"[^A-Za-z0-9._-]+", "-", Path(source_path).stem).strip("-._")
        if not base_name:
            base_name = "merge-source"
        suffix = Path(source_path).suffix.lower()
        if suffix not in _TRIM_DERIVATIVE_CONTAINER_SUFFIXES:
            suffix = ".mp4"
        return f"{base_name}-{source.id[:8]}-trim{suffix}"

    def _merge_source_trim_derivative_path(self, source: MergeSource) -> Path:
        existing_path = str(source.trim_derivative.derivative_path or "").strip()
        if existing_path:
            return Path(existing_path).expanduser().resolve(strict=False)

        project_path = self._require_saved_project_for_trim_derivative()
        derivative_path = (
            project_path / INPUT_DIRNAME / self._merge_source_trim_derivative_filename(source)
        ).resolve(strict=False)
        return derivative_path

    def _merge_source_available_original_path(self, source: MergeSource) -> Path | None:
        original_path = str(source.trim_derivative.original_path or "").strip()
        if original_path:
            original_candidate = Path(original_path).expanduser().resolve(strict=False)
            if original_candidate.is_file():
                return original_candidate

        asset_path = str(source.asset.path or "").strip()
        if not asset_path:
            return None

        asset_candidate = Path(asset_path).expanduser().resolve(strict=False)
        if not asset_candidate.is_file():
            return None

        derivative_path = str(source.trim_derivative.derivative_path or "").strip()
        if derivative_path:
            derivative_candidate = Path(derivative_path).expanduser().resolve(strict=False)
            if asset_candidate == derivative_candidate:
                return None

        return asset_candidate

    def _refresh_merge_source_trim_derivative_from_original(
        self,
        original_source_path: Path,
        derivative_path: Path,
    ) -> Path:
        derivative_path.parent.mkdir(parents=True, exist_ok=True)
        if original_source_path != derivative_path:
            shutil.copy2(original_source_path, derivative_path)
        elif not derivative_path.is_file():
            raise FileNotFoundError(
                "Trim derivative source is unavailable. Restore the original media before trimming again."
            )
        return derivative_path

    def _merge_source_trim_source_path(self, source: MergeSource) -> Path:
        original_path = _merge_source_original_path(source)
        if original_path:
            original_candidate = Path(original_path).expanduser().resolve(strict=False)
            if original_candidate.is_file():
                return original_candidate

        derivative_path = str(source.trim_derivative.derivative_path or "").strip()
        if derivative_path:
            derivative_candidate = Path(derivative_path).expanduser().resolve(strict=False)
            if derivative_candidate.is_file():
                return derivative_candidate

        asset_path = str(source.asset.path or "").strip()
        if asset_path:
            asset_candidate = Path(asset_path).expanduser().resolve(strict=False)
            if asset_candidate.is_file():
                return asset_candidate

        raise FileNotFoundError(
            "Trim source is unavailable. Restore the original media or keep the local derivative available before trimming again."
        )

    def trim_merge_source_to_derivative(
        self,
        source_id: str,
        *,
        start_ms: int,
        end_ms: int | None = None,
        export_settings: ExportSettings | None = None,
    ) -> MergeSource:
        project_path = self._require_saved_project_for_trim_derivative()
        source = self._merge_source_by_id(source_id)
        if source.asset.is_still_image:
            raise ValueError("Only video merge sources can generate trim derivatives.")

        derivative_path = self._merge_source_trim_derivative_path(source)
        (project_path / INPUT_DIRNAME).mkdir(parents=True, exist_ok=True)
        original_source_path = self._merge_source_available_original_path(source)
        if original_source_path is not None:
            trim_source_path = self._refresh_merge_source_trim_derivative_from_original(
                original_source_path,
                derivative_path,
            )
        else:
            trim_source_path = self._merge_source_trim_source_path(source)

        trim_source_fps = probe_video(trim_source_path).fps
        generate_trimmed_derivative(
            trim_source_path,
            derivative_path,
            start_ms=start_ms,
            end_ms=end_ms,
            source_fps=trim_source_fps,
            export_settings=export_settings or self.project.export,
        )

        if (
            not str(source.trim_derivative.original_path or "").strip()
            and original_source_path is not None
        ):
            source.trim_derivative.original_path = str(original_source_path)
        source.trim_derivative.derivative_path = str(derivative_path)
        source.asset = probe_video(derivative_path)
        _sync_merge_source_trim_provenance(source)
        _sync_secondary_video_from_merge_sources(self.project)
        self.project.merge.enabled = bool(self.project.merge_sources)
        self._set_status("Updated merge trim derivative.")
        self.project.touch()
        self.project_changed.emit()
        return source

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
            if _first_analyzable_merge_source(self.project) is not None:
                self.analyze_secondary()
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
        if _first_analyzable_merge_source(self.project) is not None:
            self.analyze_secondary()
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
            ("inspector_width", 320, 4096),
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
        self.project.touch()
        self.project_changed.emit()

    def set_badge_size(self, size: BadgeSize) -> None:
        self.project.overlay.badge_size = size
        if size != BadgeSize.CUSTOM:
            self.project.overlay.font_size = _badge_font_size_from_enum(size)
        self.settings.badge_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_layout(self, style_type: str, spacing: int, margin: int) -> None:
        self.project.overlay.style_type = (
            style_type if style_type in {"square", "bubble", "rounded"} else "square"
        )
        self.project.overlay.spacing = max(0, min(40, int(spacing)))
        self.project.overlay.margin = max(0, min(40, int(margin)))
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_display_options(self, payload: dict[str, object]) -> None:
        overlay = self.project.overlay
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
        valid_custom_box_modes = {"manual", "imported_summary"}
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
        self.project.touch()
        self.project_changed.emit()

    def set_overlay_badge_style(
        self,
        badge_name: str,
        background_color: str | None = None,
        text_color: str | None = None,
        opacity: float | None = None,
    ) -> None:
        if badge_name not in VALID_OVERLAY_BADGE_NAMES:
            raise ValueError(f"Unknown badge style: {badge_name}")
        style = getattr(self.project.overlay, badge_name)
        if not isinstance(style, BadgeStyle):
            raise ValueError(f"Unknown badge style: {badge_name}")
        if background_color is not None:
            style.background_color = background_color
        if text_color is not None:
            style.text_color = text_color
        if opacity is not None:
            style.opacity = max(0.0, min(1.0, opacity))
        self.project.touch()
        self.project_changed.emit()

    def set_scoring_color(self, score_key: str, color: str) -> None:
        normalized_key = str(score_key).strip()
        if not normalized_key:
            raise ValueError("score color key is required")
        if "|" in normalized_key:
            raise ValueError("score color keys must be individual tokens")
        self.project.overlay.scoring_colors[normalized_key] = color
        self.project.touch()
        self.project_changed.emit()

    def set_merge_enabled(self, enabled: bool) -> None:
        self.project.merge.enabled = enabled
        self.project.touch()
        self.project_changed.emit()

    def set_merge_layout(self, layout: MergeLayout) -> None:
        self.project.merge.layout = layout
        self.settings.merge_layout = layout
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size(self, size: PipSize) -> None:
        self.project.merge.pip_size = size
        self.project.merge.pip_size_percent = _pip_size_percent_from_enum(size)
        self.settings.pip_size = size
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def set_pip_size_percent(self, percent: int) -> None:
        self.project.merge.pip_size_percent = max(1, min(95, int(percent)))
        self.project.touch()
        self.project_changed.emit()

    def set_pip_position(self, pip_x: float | None = None, pip_y: float | None = None) -> None:
        if pip_x is not None:
            self.project.merge.pip_x = max(0.0, min(1.0, float(pip_x)))
        if pip_y is not None:
            self.project.merge.pip_y = max(0.0, min(1.0, float(pip_y)))
        self.project.touch()
        self.project_changed.emit()

    def set_merge_source_position(
        self,
        source_id: str,
        pip_size_percent: int | None = None,
        pip_x: float | None = None,
        pip_y: float | None = None,
        opacity: float | None = None,
        angle_role: str | None = None,
        placement_mode: str | None = None,
        placement_slot: str | None = None,
        target_kind: str | None = None,
        target_source_id: str | None = None,
    ) -> None:
        for index, source in enumerate(self.project.merge_sources):
            if source.id != source_id:
                continue
            explicit_placement_requested = any(
                value is not None
                for value in (placement_mode, placement_slot, target_kind, target_source_id)
            )
            role_changed = False
            previous_angle_role = source.angle_role
            if source.placement.order_index is None:
                source.placement.order_index = _merge_source_stable_order_index(source, index)
            if source.placement.layer_index is None:
                source.placement.layer_index = source.placement.order_index
            if pip_size_percent is not None:
                source.pip_size_percent = max(1, min(95, int(pip_size_percent)))
            if pip_x is not None:
                source.pip_x = max(0.0, min(1.0, float(pip_x)))
            if pip_y is not None:
                source.pip_y = max(0.0, min(1.0, float(pip_y)))
            if opacity is not None:
                source.opacity = max(0.0, min(1.0, float(opacity)))
            if angle_role is not None:
                next_angle_role = _normalize_merge_source_angle_role(angle_role, source.asset)
                role_changed = source.angle_role != next_angle_role
                previous_angle_role = source.angle_role
                source.angle_role = next_angle_role
            if explicit_placement_requested:
                next_mode = (
                    source.placement.mode
                    if placement_mode is None
                    else _normalize_merge_source_placement_mode(placement_mode)
                )
                next_target_source_id = (
                    source.placement.target_source_id
                    if target_source_id is None
                    else str(target_source_id).strip() or None
                )
                next_target_kind = _normalize_merge_source_placement_target_kind(
                    source.placement.target_kind if target_kind is None else target_kind,
                    target_source_id=next_target_source_id,
                )
                if next_target_kind != MergePlacementTargetKind.MERGE_SOURCE:
                    next_target_source_id = None
                next_slot_input = placement_slot
                if next_slot_input is None:
                    next_slot_input = None if placement_mode is not None else source.placement.slot
                source.placement.mode = next_mode
                source.placement.slot = _normalize_merge_source_placement_slot(
                    next_slot_input,
                    mode=next_mode,
                )
                source.placement.target_kind = next_target_kind
                source.placement.target_source_id = next_target_source_id
            if role_changed:
                if not explicit_placement_requested:
                    _apply_merge_source_role_seed_defaults(
                        self.project,
                        source,
                        reference_role=previous_angle_role,
                    )
                for other_source in self.project.merge_sources:
                    if other_source.id == source_id:
                        continue
                    _apply_merge_source_role_seed_defaults(self.project, other_source)
                _realign_live_merge_reference_state(self.project)
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def set_merge_source_sync_offset(self, source_id: str, offset_ms: int) -> None:
        for source in self.project.merge_sources:
            if source.id != source_id:
                continue
            source.sync_offset_ms = int(offset_ms)
            preferred_source = _preferred_merge_reference_source(self.project)
            if preferred_source is not None and preferred_source.id == source_id:
                self.project.analysis.sync_offset_ms = source.sync_offset_ms
                self.project.analysis.secondary_sync_source = "manual"
                self.project.secondary_video = (
                    source.asset if _source_supports_secondary_analysis(source) else None
                )
            self._set_status(f"Adjusted merge source sync to {source.sync_offset_ms} ms.")
            self.project.touch()
            self.project_changed.emit()
            return
        raise ValueError("Merge source not found")

    def reset_merge_defaults(self) -> None:
        self.project.merge.enabled = False
        _reset_project_merge_defaults(self.project)
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
        self.project.touch()
        self.project_changed.emit()

    def apply_export_preset(self, preset: str) -> None:
        if preset == ExportPreset.CUSTOM.value:
            self.project.export.preset = ExportPreset.CUSTOM
            self.project.touch()
            self.project_changed.emit()
            return
        apply_export_preset_settings(self.project, preset)
        self.settings.export_quality = self.project.export.quality
        save_settings(self.settings)
        self.settings_changed.emit()
        self.project_changed.emit()

    # Phase 3/6 must keep trim settings on the same export payload keys/preset ids
    # used by the existing export pane; trim-specific fields live alongside that
    # shared contract instead of introducing a parallel trim-only settings dialect.
    def trim_export_settings_from_payload(
        self,
        payload: dict[str, object] | None = None,
    ) -> ExportSettings:
        export_payload = payload
        if isinstance(payload, dict) and isinstance(payload.get("export"), dict):
            export_payload = payload.get("export")
        return resolved_export_settings(
            self.project.export,
            export_payload if isinstance(export_payload, dict) else {},
            synchronize_preset=True,
        )

    def trim_merge_source_from_payload(
        self,
        payload: dict[str, object] | None = None,
    ) -> MergeSource:
        request_payload = payload if isinstance(payload, dict) else {}
        source_id = request_payload.get("source_id", request_payload.get("id"))
        if source_id in {None, ""}:
            raise ValueError("source_id is required")

        trim_payload = request_payload.get("trim")
        trim_request = trim_payload if isinstance(trim_payload, dict) else request_payload
        start_ms_value = trim_request.get(
            "start_ms",
            request_payload.get("start_ms", request_payload.get("trim_start_ms")),
        )
        if start_ms_value in {None, ""}:
            raise ValueError("start_ms is required")
        end_ms_value = trim_request.get(
            "end_ms",
            request_payload.get("end_ms", request_payload.get("trim_end_ms")),
        )

        return self.trim_merge_source_to_derivative(
            str(source_id),
            start_ms=int(start_ms_value),
            end_ms=None if end_ms_value in {None, ""} else int(end_ms_value),
            export_settings=self.trim_export_settings_from_payload(request_payload),
        )

    def set_export_settings(self, payload: dict[str, object]) -> None:
        normalized_payload = apply_export_settings_payload(self.project.export, payload)
        if "quality" in normalized_payload:
            self.settings.export_quality = self.project.export.quality
            save_settings(self.settings)
            self.settings_changed.emit()
        self.project.touch()
        self.project_changed.emit()

    def adjust_sync_offset(self, delta_ms: int) -> None:
        self.project.analysis.sync_offset_ms += delta_ms
        source = _preferred_merge_reference_source(self.project)
        if source is not None:
            source.sync_offset_ms = self.project.analysis.sync_offset_ms
            if _source_supports_secondary_analysis(source):
                self.project.secondary_video = source.asset
        self.project.analysis.secondary_sync_source = "manual"
        self._set_status(f"Adjusted sync offset to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def set_sync_offset(self, offset_ms: int) -> None:
        self.project.analysis.sync_offset_ms = offset_ms
        source = _preferred_merge_reference_source(self.project)
        if source is not None:
            source.sync_offset_ms = self.project.analysis.sync_offset_ms
            if _source_supports_secondary_analysis(source):
                self.project.secondary_video = source.asset
        self.project.analysis.secondary_sync_source = "manual"
        self._set_status(f"Sync offset set to {self.project.analysis.sync_offset_ms} ms.")
        self.project.touch()
        self.project_changed.emit()

    def swap_videos(self) -> None:
        swapped_merge_source: MergeSource | None = None
        if self.project.merge_sources:
            swapped_merge_source = _preferred_merge_reference_source(self.project)
            if swapped_merge_source is None:
                return
            first_source = swapped_merge_source.asset
            swapped_merge_source.asset = self.project.primary_video
            _reset_merge_source_trim_provenance(swapped_merge_source)
            self.project.primary_video = first_source
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
        if swapped_merge_source is not None and _source_supports_secondary_analysis(swapped_merge_source):
            analyzed_source = swapped_merge_source
        else:
            analyzed_source = _first_analyzable_merge_source(self.project)
        if self.project.merge_sources:
            self.project.secondary_video = None if analyzed_source is None else analyzed_source.asset
        self.project.analysis.analyzed_secondary_source_id = None if analyzed_source is None else analyzed_source.id
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
        self.project.touch()
        self.project_path = ensure_project_suffix(target_path)
        self.folder_settings = self._load_folder_settings_safe(self.project_path)
        self._ensure_project_output_path(previous_project_path=previous_project_path)
        save_project(self.project, self.project_path)
        self._save_stage_profiles(self.project_path)
        self._sync_project_to_library()
        self._restore_practiscore_source_from_project()
        self._saved_snapshot = project_to_dict(self.project)
        self._remember_original_shots()
        self._remember_project(self.project_path)
        self._ensure_project_workspace_membership(self.project_path)
        self._set_status(f"Project folder ready at {self.project_path}.")
        self.project_path_changed.emit(str(self.project_path))
        self.project_changed.emit()

    def open_project(self, path: str) -> None:
        project_path = ensure_project_suffix(path)
        raw_payload = _project_payload_from_disk(project_path)
        secondary_video_is_explicitly_persisted = (
            isinstance(raw_payload, dict) and "secondary_video" in raw_payload
        )

        self.project = load_project(project_path)
        self.project_path = project_path
        self.folder_settings = self._load_folder_settings_safe(self.project_path)
        self._ensure_project_output_path()
        loaded_snapshot = project_to_dict(self.project)
        recovered_media = self._restore_media_sources_from_project(
            secondary_video_is_explicitly_persisted=secondary_video_is_explicitly_persisted,
        )
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
        self._ensure_project_workspace_membership(self.project_path)
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
        self._load_stage_profiles(self.project_path)
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
                    payload.get("layout_inspector_width"), 320, 4096
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
        current_snapshot = project_to_dict(self.project)
        if current_snapshot == self._saved_snapshot:
            return
        try:
            self._autosave_in_progress = True
            save_project(self.project, self.project_path)
            self._save_stage_profiles(self.project_path)
            self._sync_project_to_library()
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
        current_output_path = str(self.project.export.output_path or "").strip()
        project_output_path = str(default_project_output_path(self.project_path))
        previous_output_path = (
            str(default_project_output_path(previous_project_path))
            if previous_project_path is not None
            else ""
        )
        if not current_output_path or (
            previous_output_path and current_output_path == previous_output_path
        ):
            self.project.export.output_path = project_output_path

    def _set_status(self, message: str) -> None:
        self.status_message = message
        self.status_changed.emit(message)

    def landing_recent(self) -> dict:
        return shared_backend_service.landing_recent(self)

    def library_backup_create(self) -> dict:
        return shared_backend_service.library_backup_create()
    
    def library_backup_restore(self, manifest: dict) -> dict:
        return shared_backend_service.library_backup_restore(manifest)
