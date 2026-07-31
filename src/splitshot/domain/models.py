"""Canonical SplitShot project schema, enums, dataclasses, and serialization helpers."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

from splitshot.overlay.font_policy import default_overlay_font_family


class StrEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ShotSource(StrEnum):
    AUTO = "auto"
    MANUAL = "manual"


class ScoreLetter(StrEnum):
    A = "A"
    C = "C"
    D = "D"
    M = "M"
    NS = "NS"
    MU = "MU"
    M_NS = "M+NS"
    DOWN_0 = "-0"
    DOWN_1 = "-1"
    DOWN_3 = "-3"
    GPA_0 = "0"
    GPA_1 = "+1"
    GPA_3 = "+3"
    GPA_10 = "+10"
    STEEL_HIT = "HIT"
    STEEL_STOP_FAIL = "STOP"


class OverlayPosition(StrEnum):
    NONE = "none"
    TOP = "top"
    BOTTOM = "bottom"
    LEFT = "left"
    RIGHT = "right"


class BadgeSize(StrEnum):
    XS = "XS"
    S = "S"
    M = "M"
    L = "L"
    XL = "XL"
    CUSTOM = "custom"


class MergeLayout(StrEnum):
    SIDE_BY_SIDE = "side_by_side"
    ABOVE_BELOW = "above_below"
    PIP = "pip"
    FULL_SCREEN_PORTRAIT = "full_screen_portrait"
    DUAL_CENTER_HUD = "dual_center_hud"
    DUAL_TOP_HUD = "dual_top_hud"


class MergePlacementMode(StrEnum):
    AUTO = "auto"
    BASE = "base"
    SIDE_BY_SIDE = "side_by_side"
    ABOVE_BELOW = "above_below"
    PIP = "pip"
    FULL_SCREEN_PORTRAIT = "full_screen_portrait"
    DUAL_CENTER_HUD = "dual_center_hud"
    DUAL_TOP_HUD = "dual_top_hud"


class MergePlacementSlot(StrEnum):
    AUTO = "auto"
    LEFT = "left"
    RIGHT = "right"
    TOP = "top"
    BOTTOM = "bottom"
    CENTER = "center"
    OVERLAY = "overlay"


class MergePlacementTargetKind(StrEnum):
    PRIMARY_VIDEO = "primary_video"
    MERGE_SOURCE = "merge_source"


class MergeSourceAssetPathKind(StrEnum):
    ORIGINAL = "original"
    LOCAL_DERIVATIVE = "local_derivative"


class PipSize(StrEnum):
    SMALL = "25%"
    MEDIUM = "35%"
    LARGE = "50%"


class ExportQuality(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ExportPreset(StrEnum):
    SOURCE = "source"
    UNIVERSAL_VERTICAL = "universal_vertical"
    SHORT_FORM_VERTICAL = "short_form_vertical"
    YOUTUBE_LONG_1080P = "youtube_long_1080p"
    YOUTUBE_LONG_4K = "youtube_long_4k"
    CUSTOM = "custom"


class ExportFrameRate(StrEnum):
    SOURCE = "source"
    FPS_30 = "30"
    FPS_60 = "60"


class ExportVideoCodec(StrEnum):
    H264 = "h264"
    HEVC = "hevc"


class ExportAudioCodec(StrEnum):
    AAC = "aac"


class ExportColorSpace(StrEnum):
    BT709_SDR = "bt709_sdr"


class QueueStatus(StrEnum):
    NOT_QUEUED = "not_queued"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"


class CombinedExportMode(StrEnum):
    PLAIN_STITCH = "plain_stitch"
    SEPARATOR = "separator"


class AspectRatio(StrEnum):
    ORIGINAL = "original"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    PORTRAIT_45 = "4:5"


class FrameProfile(StrEnum):
    SOURCE = "source"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    PORTRAIT_45 = "4:5"


class OutputProfileKind(StrEnum):
    STAGE_OUTPUT = "stage_output"
    STAGE_COMPOSITE = "stage_composite"


OUTPUT_PROFILE_FRAME_PROFILE_VALUES = frozenset({"source", "16:9", "9:16", "1:1", "4:5"})


_STILL_IMAGE_SUFFIXES = {
    ".apng",
    ".avif",
    ".bmp",
    ".gif",
    ".heic",
    ".heif",
    ".jpeg",
    ".jpg",
    ".png",
    ".qoi",
    ".svg",
    ".tif",
    ".tiff",
    ".webp",
}


@dataclass(slots=True)
class BadgeStyle:
    background_color: str = "#111827"
    text_color: str = "#F9FAFB"
    opacity: float = 0.9


@dataclass(slots=True)
class VideoAsset:
    path: str = ""
    duration_ms: int = 0
    width: int = 0
    height: int = 0
    fps: float = 30.0
    audio_sample_rate: int = 22050
    rotation: int = 0
    is_still_image: bool = False
    media_kind: str = "video"

    @property
    def path_obj(self) -> Path:
        return Path(self.path)

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


# Keep the internal model field name `angle_role` for now. Outward browser and
# persistence payloads emit `camera_role`, while readers accept legacy
# `angle_role` as a narrow compatibility alias.
MERGE_SOURCE_ANGLE_ROLE_VALUES = ("primary", "follow", "static", "detail")

_MERGE_SOURCE_ANGLE_ROLES = frozenset(MERGE_SOURCE_ANGLE_ROLE_VALUES)


def default_merge_source_angle_role(asset: VideoAsset | None = None) -> str:
    if asset is not None and asset.is_still_image:
        return "detail"
    return "follow"


def _normalize_merge_source_angle_role(
    value: Any,
    asset: VideoAsset | None = None,
) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _MERGE_SOURCE_ANGLE_ROLES:
        return normalized
    return default_merge_source_angle_role(asset)


def _default_merge_source_placement_slot(mode: MergePlacementMode) -> MergePlacementSlot:
    if mode == MergePlacementMode.PIP:
        return MergePlacementSlot.OVERLAY
    if mode in {
        MergePlacementMode.BASE,
        MergePlacementMode.FULL_SCREEN_PORTRAIT,
        MergePlacementMode.DUAL_CENTER_HUD,
        MergePlacementMode.DUAL_TOP_HUD,
    }:
        return MergePlacementSlot.CENTER
    return MergePlacementSlot.AUTO


def _normalize_merge_source_placement_mode(value: Any) -> MergePlacementMode:
    try:
        return MergePlacementMode(str(value or MergePlacementMode.AUTO.value).strip().lower())
    except ValueError:
        return MergePlacementMode.AUTO


def _normalize_merge_source_placement_slot(
    value: Any,
    *,
    mode: MergePlacementMode,
) -> MergePlacementSlot:
    try:
        return MergePlacementSlot(str(value).strip().lower())
    except ValueError:
        return _default_merge_source_placement_slot(mode)


def _normalize_merge_source_placement_target_kind(
    value: Any,
    *,
    target_source_id: str | None = None,
) -> MergePlacementTargetKind:
    normalized = str(value or "").strip().lower()
    try:
        kind: MergePlacementTargetKind | None = MergePlacementTargetKind(normalized)
    except ValueError:
        kind = None
    if kind is not None:
        if kind == MergePlacementTargetKind.MERGE_SOURCE and not target_source_id:
            return MergePlacementTargetKind.PRIMARY_VIDEO
        return kind
    if target_source_id:
        return MergePlacementTargetKind.MERGE_SOURCE
    return MergePlacementTargetKind.PRIMARY_VIDEO


def _normalize_merge_source_index(value: Any) -> int | None:
    if value in {None, ""}:
        return None
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return None


def _trim_float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _normalize_merge_source_active_path_kind(
    value: Any,
    *,
    asset_path: str = "",
    original_path: str = "",
    derivative_path: str | None = None,
) -> MergeSourceAssetPathKind:
    normalized = str(value or "").strip().lower()
    try:
        kind: MergeSourceAssetPathKind | None = MergeSourceAssetPathKind(normalized)
    except ValueError:
        kind = None
    if kind == MergeSourceAssetPathKind.LOCAL_DERIVATIVE and not derivative_path:
        return MergeSourceAssetPathKind.ORIGINAL
    if kind is not None:
        return kind
    if (
        derivative_path
        and asset_path
        and asset_path == derivative_path
        and derivative_path != original_path
    ):
        return MergeSourceAssetPathKind.LOCAL_DERIVATIVE
    return MergeSourceAssetPathKind.ORIGINAL


def _merge_layout_to_placement_mode(layout: MergeLayout) -> MergePlacementMode:
    return {
        MergeLayout.SIDE_BY_SIDE: MergePlacementMode.SIDE_BY_SIDE,
        MergeLayout.ABOVE_BELOW: MergePlacementMode.ABOVE_BELOW,
        MergeLayout.PIP: MergePlacementMode.PIP,
        MergeLayout.FULL_SCREEN_PORTRAIT: MergePlacementMode.FULL_SCREEN_PORTRAIT,
        MergeLayout.DUAL_CENTER_HUD: MergePlacementMode.DUAL_CENTER_HUD,
        MergeLayout.DUAL_TOP_HUD: MergePlacementMode.DUAL_TOP_HUD,
    }[layout]


def _legacy_merge_source_slot(
    mode: MergePlacementMode,
    *,
    primary_is_left_or_top: bool,
) -> MergePlacementSlot:
    if mode == MergePlacementMode.SIDE_BY_SIDE:
        return MergePlacementSlot.RIGHT if primary_is_left_or_top else MergePlacementSlot.LEFT
    if mode == MergePlacementMode.ABOVE_BELOW:
        return MergePlacementSlot.BOTTOM if primary_is_left_or_top else MergePlacementSlot.TOP
    return _default_merge_source_placement_slot(mode)


def _payload_has_value(payload: dict[str, Any] | None, *keys: str) -> bool:
    if not isinstance(payload, dict):
        return False
    return any(payload.get(key) not in {None, ""} for key in keys)


@dataclass(slots=True)
class MergeSourcePlacement:
    mode: MergePlacementMode = MergePlacementMode.AUTO
    slot: MergePlacementSlot = MergePlacementSlot.AUTO
    target_kind: MergePlacementTargetKind = MergePlacementTargetKind.PRIMARY_VIDEO
    target_source_id: str | None = None
    order_index: int | None = None
    layer_index: int | None = None


@dataclass(slots=True)
class MergeSourceTrimDerivative:
    original_path: str = ""
    derivative_path: str | None = None
    derivative_asset: VideoAsset = field(default_factory=VideoAsset)
    active_path_kind: MergeSourceAssetPathKind = MergeSourceAssetPathKind.ORIGINAL
    start_s: float | None = None
    end_s: float | None = None


@dataclass(slots=True)
class OutputProfile:
    output_id: str = field(default_factory=lambda: uuid4().hex)
    scope_type: str = "stage"
    scope_id: str = ""
    profile_name: str = ""
    profile_kind: OutputProfileKind = OutputProfileKind.STAGE_OUTPUT
    frame_profile: str = "source"
    metric_caption_preset: str = ""
    lead_in_card: str = ""
    brand_mark: str = ""
    subject_track_crop: str = ""
    visibility_recipe: str = ""
    angle_director_plan: str = ""
    review_source_id: str = ""
    retained_proxy_id: str = ""
    archive_id: str = ""
    last_rendered_at: str = ""
    export_settings: dict[str, Any] = field(default_factory=dict)


def _normalize_frame_profile(value: str) -> str:
    normalized = str(value or "source").strip().lower()
    if normalized in OUTPUT_PROFILE_FRAME_PROFILE_VALUES:
        return normalized
    return "source"


def _normalize_output_profile_export_settings(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not value:
        return {}
    settings = _export_from_dict(value)
    return {
        "quality": settings.quality.value,
        "aspect_ratio": settings.aspect_ratio.value,
        "crop_center_x": settings.crop_center_x,
        "crop_center_y": settings.crop_center_y,
        "preset": settings.preset.value,
        "target_width": settings.target_width,
        "target_height": settings.target_height,
        "frame_rate": settings.frame_rate.value,
        "video_codec": settings.video_codec.value,
        "video_bitrate_mbps": settings.video_bitrate_mbps,
        "audio_codec": settings.audio_codec.value,
        "audio_sample_rate": settings.audio_sample_rate,
        "audio_bitrate_kbps": settings.audio_bitrate_kbps,
        "color_space": settings.color_space.value,
        "two_pass": settings.two_pass,
        "multi_track": settings.multi_track,
        "ffmpeg_preset": settings.ffmpeg_preset,
    }


def output_profile_from_dict(data: dict[str, Any]) -> OutputProfile:
    return OutputProfile(
        output_id=str(data.get("output_id", uuid4().hex)),
        scope_type=str(data.get("scope_type", "stage")),
        scope_id=str(data.get("scope_id", "")),
        profile_name=str(data.get("profile_name", "")),
        profile_kind=OutputProfileKind(
            str(data.get("profile_kind", "stage_output")).strip().lower()
        ),
        frame_profile=_normalize_frame_profile(data.get("frame_profile", "source")),
        metric_caption_preset=str(data.get("metric_caption_preset", "")),
        lead_in_card=str(data.get("lead_in_card", "")),
        brand_mark=str(data.get("brand_mark", "")),
        subject_track_crop=str(data.get("subject_track_crop", "")),
        visibility_recipe=str(data.get("visibility_recipe", "")),
        angle_director_plan=str(data.get("angle_director_plan", "")),
        review_source_id=str(data.get("review_source_id", "")),
        retained_proxy_id=str(data.get("retained_proxy_id", "")),
        archive_id=str(data.get("archive_id", "")),
        last_rendered_at=str(data.get("last_rendered_at", "")),
        export_settings=_normalize_output_profile_export_settings(data.get("export_settings")),
    )


def output_profile_to_dict(profile: OutputProfile) -> dict[str, Any]:
    return {
        "output_id": profile.output_id,
        "scope_type": profile.scope_type,
        "scope_id": profile.scope_id,
        "profile_name": profile.profile_name,
        "profile_kind": str(profile.profile_kind.value),
        "frame_profile": profile.frame_profile,
        "metric_caption_preset": profile.metric_caption_preset,
        "lead_in_card": profile.lead_in_card,
        "brand_mark": profile.brand_mark,
        "subject_track_crop": profile.subject_track_crop,
        "visibility_recipe": profile.visibility_recipe,
        "angle_director_plan": profile.angle_director_plan,
        "review_source_id": profile.review_source_id,
        "retained_proxy_id": profile.retained_proxy_id,
        "archive_id": profile.archive_id,
        "last_rendered_at": profile.last_rendered_at,
        "export_settings": _normalize_output_profile_export_settings(profile.export_settings),
    }


def _serialize_output_profiles(profiles: list[OutputProfile]) -> str:
    return json.dumps([output_profile_to_dict(p) for p in profiles], indent=2)


def _deserialize_output_profiles(data: str) -> list[OutputProfile]:
    try:
        raw = json.loads(data)
        if isinstance(raw, list):
            return [output_profile_from_dict(item) for item in raw if isinstance(item, dict)]
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return []


@dataclass(slots=True)
class MergeSource:
    id: str = field(default_factory=lambda: uuid4().hex)
    asset: VideoAsset = field(default_factory=VideoAsset)
    angle_role: str = "follow"
    pip_size_percent: int | None = None
    pip_x: float = 1.0
    pip_y: float = 1.0
    opacity: float = 1.0
    sync_offset_ms: int = 0
    placement: MergeSourcePlacement = field(default_factory=MergeSourcePlacement)
    trim_derivative: MergeSourceTrimDerivative = field(default_factory=MergeSourceTrimDerivative)


@dataclass(slots=True)
class ScoreMark:
    letter: ScoreLetter = ScoreLetter.A
    x_norm: float = 0.5
    y_norm: float = 0.5
    animation_preset: str = "fade_scale"
    penalty_counts: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ShotEvent:
    id: str = field(default_factory=lambda: uuid4().hex)
    time_ms: int = 0
    shotml_time_ms: int | None = None
    shotml_confidence: float | None = None
    source: ShotSource = ShotSource.AUTO
    confidence: float | None = None
    score: ScoreMark | None = field(default_factory=ScoreMark)
    user_added: bool = False


@dataclass(slots=True)
class TimingEvent:
    id: str = field(default_factory=lambda: uuid4().hex)
    kind: str = "reload"
    label: str = "Reload"
    after_shot_id: str | None = None
    before_shot_id: str | None = None
    note: str = ""


@dataclass(slots=True)
class ShotMLSettings:
    detection_threshold: float = 0.35
    shot_detection_cutoff_base: float = 0.42
    shot_detection_cutoff_span: float = 0.28
    beep_onset_fraction: float = 0.24
    beep_search_lead_ms: int = 4000
    beep_search_tail_guard_ms: int = 40
    beep_fallback_min_window_ms: int = 80
    beep_heuristic_fft_window_s: float = 0.02
    beep_heuristic_hop_s: float = 0.005
    beep_heuristic_band_min_hz: int = 1800
    beep_heuristic_band_max_hz: int = 4200
    beep_fallback_threshold_multiplier: float = 0.8
    beep_tonal_window_ms: int = 80
    beep_tonal_hop_ms: int = 1
    beep_tonal_band_min_hz: int = 1500
    beep_tonal_band_max_hz: int = 5000
    beep_refine_pre_ms: int = 500
    beep_refine_post_ms: int = 450
    beep_refine_min_gap_before_first_shot_ms: int = 40
    beep_exclusion_radius_ms: int = 70
    beep_region_cutoff_base: float = 0.82
    beep_region_cutoff_threshold_weight: float = 0.1
    beep_model_boost_floor: float = 0.3
    min_shot_interval_ms: int = 100
    shot_peak_min_spacing_ms: int = 200
    shot_confidence_source: str = "shot_minus_background_beep"
    shot_onset_fraction: float = 0.66
    shot_refine_pre_ms: int = 150
    shot_refine_post_ms: int = 120
    shot_refine_midpoint_clamp_padding_ms: int = 70
    shot_refine_min_search_window_ms: int = 12
    shot_refine_rms_window_ms: int = 3
    shot_refine_rms_hop_ms: int = 1
    weak_onset_support_threshold: float = 0.35
    near_cutoff_interval_ms: int = 150
    shot_selection_confidence_weight: float = 0.55
    shot_selection_support_weight: float = 0.45
    weak_support_penalty: float = 0.08
    suppress_close_pair_duplicates: bool = True
    suppress_sound_profile_outliers: bool = True
    refinement_confidence_weight: float = 0.35
    onset_support_pre_ms: int = 45
    onset_support_post_ms: int = 80
    onset_support_rms_window_ms: int = 3
    onset_support_rms_hop_ms: int = 1
    onset_support_alignment_penalty_divisor_ms: int = 45
    onset_support_alignment_penalty_multiplier: float = 0.25
    sound_profile_search_radius_ms: int = 120
    sound_profile_distance_limit: float = 5.0
    sound_profile_high_confidence_limit: float = 0.995
    window_size: int = 2048
    hop_size: int = 128


@dataclass(slots=True)
class TimingChangeProposal:
    id: str = field(default_factory=lambda: uuid4().hex)
    proposal_type: str = "move_shot"
    status: str = "pending"
    shot_id: str | None = None
    shot_number: int | None = None
    source_time_ms: int | None = None
    target_time_ms: int | None = None
    alternate_shot_id: str | None = None
    alternate_time_ms: int | None = None
    confidence: float | None = None
    support_confidence: float | None = None
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class SecondarySourceAnalysis:
    source_id: str = ""
    beep_time_ms: int | None = None
    sync_offset_ms: int = 0
    analysis_status: str = "idle"
    analysis_message: str = ""
    sync_source: str = "manual"
    waveform: list[float] = field(default_factory=list)


@dataclass(slots=True)
class AnalysisState:
    beep_time_ms_primary: int | None = None
    beep_time_ms_secondary: int | None = None
    analyzed_secondary_source_id: str | None = None
    secondary_analysis_status: str = "idle"
    secondary_analysis_message: str = ""
    secondary_sync_source: str = "manual"
    sync_offset_ms: int = 0
    detection_threshold: float = 0.35
    shotml_settings: ShotMLSettings = field(default_factory=ShotMLSettings)
    timing_change_proposals: list[TimingChangeProposal] = field(default_factory=list)
    last_shotml_run_summary: dict[str, Any] = field(default_factory=dict)
    waveform_primary: list[float] = field(default_factory=list)
    waveform_secondary: list[float] = field(default_factory=list)
    secondary_sources: list[SecondarySourceAnalysis] = field(default_factory=list)
    shots: list[ShotEvent] = field(default_factory=list)
    events: list[TimingEvent] = field(default_factory=list)
    detection_review_suggestions: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class ImportedStageScore:
    source_name: str = ""
    source_path: str = ""
    match_type: str = ""
    competitor_name: str = ""
    competitor_place: int | None = None
    stage_number: int | None = None
    stage_name: str = ""
    division: str = ""
    classification: str = ""
    power_factor: str = ""
    raw_seconds: float | None = None
    aggregate_points: float = 0.0
    total_points: float | None = None
    shot_penalties: float = 0.0
    hit_factor: float | None = None
    final_time: float | None = None
    stage_points: float | None = None
    stage_place: int | None = None
    score_counts: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class ScoringState:
    enabled: bool = True
    ruleset: str = "uspsa_minor"
    match_type: str = ""
    stage_number: int | None = None
    competitor_name: str = ""
    competitor_place: int | None = None
    classification: str = ""
    division: str = ""
    practiscore_source_path: str = ""
    practiscore_source_name: str = ""
    penalties: float = 0.0
    point_map: dict[str, float] = field(
        default_factory=lambda: {
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        }
    )
    penalty_counts: dict[str, float] = field(default_factory=dict)
    hit_factor: float | None = None
    imported_stage: ImportedStageScore | None = None
    comparison_competitors: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class OverlaySettings:
    position: OverlayPosition = OverlayPosition.BOTTOM
    badge_size: BadgeSize = BadgeSize.M
    style_type: str = "square"
    spacing: int = 8
    margin: int = 8
    max_visible_shots: int = 4
    shot_quadrant: str = "bottom_left"
    shot_direction: str = "right"
    custom_x: float | None = None
    custom_y: float | None = None
    timer_x: float | None = None
    timer_y: float | None = None
    draw_x: float | None = None
    draw_y: float | None = None
    score_x: float | None = None
    score_y: float | None = None
    bubble_width: int = 0
    bubble_height: int = 0
    font_family: str = field(default_factory=default_overlay_font_family)
    font_size: int = 14
    font_bold: bool = True
    font_italic: bool = False
    show_timer: bool = True
    show_draw: bool = True
    show_shots: bool = True
    show_shot_scores: bool = True
    show_score: bool = True
    timer_lock_to_stack: bool = True
    draw_lock_to_stack: bool = True
    score_lock_to_stack: bool = True
    custom_box_enabled: bool = False
    custom_box_mode: str = "manual"
    custom_box_text: str = ""
    custom_box_quadrant: str = "top_right"
    custom_box_x: float | None = None
    custom_box_y: float | None = None
    custom_box_background_color: str = "#000000"
    custom_box_text_color: str = "#ffffff"
    custom_box_opacity: float = 0.9
    custom_box_width: int = 0
    custom_box_height: int = 0
    text_boxes: list[OverlayTextBox] = field(default_factory=list)
    timer_badge: BadgeStyle = field(default_factory=BadgeStyle)
    shot_badge: BadgeStyle = field(default_factory=lambda: BadgeStyle(background_color="#1D4ED8"))
    current_shot_badge: BadgeStyle = field(
        default_factory=lambda: BadgeStyle(background_color="#DC2626")
    )
    hit_factor_badge: BadgeStyle = field(
        default_factory=lambda: BadgeStyle(background_color="#047857")
    )
    scoring_colors: dict[str, str] = field(
        default_factory=lambda: {
            ScoreLetter.A.value: "#22C55E",
            ScoreLetter.C.value: "#F59E0B",
            ScoreLetter.D.value: "#FB7185",
            ScoreLetter.M.value: "#EF4444",
            ScoreLetter.NS.value: "#7C3AED",
            ScoreLetter.MU.value: "#0EA5E9",
            ScoreLetter.M_NS.value: "#BE123C",
            ScoreLetter.DOWN_0.value: "#22C55E",
            ScoreLetter.DOWN_1.value: "#F59E0B",
            ScoreLetter.DOWN_3.value: "#FB7185",
            "PE": "#EF4444",
            "NT": "#F59E0B",
            "FP": "#DC2626",
            "FTDR": "#EA580C",
            "FPE": "#BE123C",
            "PM": "#EF4444",
            "SPF": "#EF4444",
            "SND": "#F59E0B",
            ScoreLetter.GPA_0.value: "#22C55E",
            ScoreLetter.GPA_1.value: "#F59E0B",
            ScoreLetter.GPA_3.value: "#FB7185",
            ScoreLetter.GPA_10.value: "#EF4444",
            ScoreLetter.STEEL_HIT.value: "#22C55E",
            ScoreLetter.STEEL_STOP_FAIL.value: "#EF4444",
        }
    )


@dataclass(slots=True)
class MergeSettings:
    enabled: bool = True
    layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    pip_size: PipSize = PipSize.MEDIUM
    pip_size_percent: int = 35
    pip_x: float = 1.0
    pip_y: float = 1.0
    primary_is_left_or_top: bool = True


@dataclass(slots=True)
class OverlayTextBox:
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    lock_to_stack: bool = False
    source: str = "manual"
    text: str = ""
    quadrant: str = "top_right"
    x: float | None = None
    y: float | None = None
    background_color: str = "#000000"
    text_color: str = "#ffffff"
    opacity: float = 0.9
    width: int = 0
    height: int = 0
    summary_metric_ids: list[str] = field(default_factory=list)
    style_type: str = "square"
    font_family: str = field(default_factory=default_overlay_font_family)
    font_size: int = 14
    font_bold: bool = True
    font_italic: bool = False


@dataclass(slots=True)
class PopupMotionPoint:
    offset_ms: int = 0
    x: float = 0.5
    y: float = 0.5
    easing: str = "linear"


@dataclass(slots=True)
class PopupBubble:
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = True
    name: str = ""
    text: str = ""
    anchor_mode: str = "time"
    shot_id: str | None = None
    time_ms: int = 0
    duration_ms: int = 1000
    quadrant: str = "middle_middle"
    x: float = 0.5
    y: float = 0.5
    motion_mode: str = "fixed"
    follow_motion: bool = False
    motion_path: list[PopupMotionPoint] = field(default_factory=list)
    background_color: str = "#000000"
    text_color: str = "#ffffff"
    opacity: float = 0.9
    width: int = 0
    height: int = 0
    style_type: str = "square"
    font_family: str = field(default_factory=default_overlay_font_family)
    font_size: int = 14
    font_bold: bool = True
    font_italic: bool = False
    content_type: str = "text"
    image_path: str = ""
    image_scale_mode: str = "contain"


@dataclass(slots=True)
class PopupTemplate:
    enabled: bool = True
    content_type: str = "text"
    text_source: str = "score"
    duration_ms: int = 1000
    use_shot_split_duration: bool = False
    quadrant: str = "middle_middle"
    width: int = 0
    height: int = 0
    motion_mode: str = "fixed"
    follow_motion: bool = False
    background_color: str = "#000000"
    text_color: str = "#ffffff"
    opacity: float = 0.9
    style_type: str = "square"
    font_family: str = field(default_factory=default_overlay_font_family)
    font_size: int = 14
    font_bold: bool = True
    font_italic: bool = False


@dataclass(slots=True)
class ExportSettings:
    quality: ExportQuality = ExportQuality.HIGH
    aspect_ratio: AspectRatio = AspectRatio.ORIGINAL
    crop_center_x: float = 0.5
    crop_center_y: float = 0.5
    output_path: str | None = None
    preset: ExportPreset = ExportPreset.SOURCE
    target_width: int | None = None
    target_height: int | None = None
    frame_rate: ExportFrameRate = ExportFrameRate.SOURCE
    video_codec: ExportVideoCodec = ExportVideoCodec.H264
    video_bitrate_mbps: float = 15.0
    audio_codec: ExportAudioCodec = ExportAudioCodec.AAC
    audio_sample_rate: int = 48000
    audio_bitrate_kbps: int = 320
    color_space: ExportColorSpace = ExportColorSpace.BT709_SDR
    two_pass: bool = False
    multi_track: bool = False
    ffmpeg_preset: str = "medium"
    last_log: str = ""
    last_error: str | None = None


@dataclass(slots=True)
class UIState:
    selected_shot_id: str | None = None
    timeline_zoom: float = 1.0
    timeline_offset_ms: int = 0
    active_tool: str = "project"
    waveform_mode: str = "select"
    waveform_expanded: bool = False
    timing_expanded: bool = False
    timing_enabled: bool = True
    review_show_markers: bool = True
    review_show_pip: bool = True
    metrics_expanded: bool = False
    markers_expanded: bool = False
    scoring_expanded: bool = False
    layout_locked: bool = True
    rail_width: int = 84
    inspector_width: int = 440
    waveform_height: int = 206
    scoring_shot_expansion: dict[str, bool] = field(default_factory=dict)
    scoring_edit_shot_ids: list[str] = field(default_factory=list)
    waveform_shot_amplitudes: dict[str, float] = field(default_factory=dict)
    timing_edit_shot_ids: list[str] = field(default_factory=list)
    timing_column_widths: dict[str, float] = field(default_factory=dict)
    review_text_box_expansion: dict[str, bool] = field(default_factory=dict)
    popup_bubble_expansion: dict[str, bool] = field(default_factory=dict)
    popup_authoring_collapsed: bool = True
    merge_source_expansion: dict[str, bool] = field(default_factory=dict)
    shotml_section_expansion: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class CombinedExportSettings:
    mode: CombinedExportMode = CombinedExportMode.PLAIN_STITCH
    separator_enabled: bool = False
    separator_duration_s: float = 0.5
    separator_text: str = ""
    separator_image_path: str = ""


@dataclass(slots=True)
class QueueSettings:
    fade_in_s: float = 0.5
    fade_out_s: float = 0.5
    intro_path: str = ""
    outro_path: str = ""
    include_intro: bool = False
    include_outro: bool = False


def _boundary_overlay_defaults() -> OverlaySettings:
    overlay = OverlaySettings()
    overlay.show_timer = False
    overlay.show_draw = False
    overlay.show_shots = False
    overlay.show_shot_scores = False
    overlay.show_score = False
    return overlay


@dataclass(slots=True)
class IntroOutroClip:
    asset: VideoAsset = field(default_factory=VideoAsset)
    overlay: OverlaySettings = field(default_factory=_boundary_overlay_defaults)


@dataclass(slots=True)
class ProjectStage:
    id: str = field(default_factory=lambda: uuid4().hex)
    label: str = ""
    order_index: int = 1
    imported_stage_number: int | None = None
    imported_stage_name: str = ""
    primary_media: VideoAsset = field(default_factory=VideoAsset)
    primary_trim_derivative: MergeSourceTrimDerivative = field(
        default_factory=MergeSourceTrimDerivative
    )
    added_media: list[MergeSource] = field(default_factory=list)
    analysis: AnalysisState = field(default_factory=AnalysisState)
    scoring: ScoringState = field(default_factory=ScoringState)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    popups: list[PopupBubble] = field(default_factory=list)
    popup_template: PopupTemplate = field(default_factory=PopupTemplate)
    merge: MergeSettings = field(default_factory=MergeSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    queue_status: QueueStatus = QueueStatus.NOT_QUEUED
    queue_snapshot: dict[str, Any] = field(default_factory=dict)
    last_processed_at: str = ""
    last_output_path: str = ""
    presentation_overridden: bool = False


@dataclass(slots=True)
class QueueEntry:
    id: str = field(default_factory=lambda: uuid4().hex)
    stage_id: str = ""
    status: QueueStatus = QueueStatus.NOT_QUEUED
    snapshot: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    processed_at: str = ""
    output_path: str = ""
    error_message: str = ""


@dataclass(slots=True)
class Project:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Untitled Project"
    description: str = ""
    output_root: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    primary_video: VideoAsset = field(default_factory=VideoAsset)
    primary_trim_derivative: MergeSourceTrimDerivative = field(
        default_factory=MergeSourceTrimDerivative
    )
    secondary_video: VideoAsset | None = None
    merge_sources: list[MergeSource] = field(default_factory=list)
    analysis: AnalysisState = field(default_factory=AnalysisState)
    scoring: ScoringState = field(default_factory=ScoringState)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    popups: list[PopupBubble] = field(default_factory=list)
    popup_template: PopupTemplate = field(default_factory=PopupTemplate)
    merge: MergeSettings = field(default_factory=MergeSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    ui_state: UIState = field(default_factory=UIState)
    schema_version: int = 1
    stages: list[ProjectStage] = field(default_factory=list)
    active_stage_id: str = ""
    queue: list[QueueEntry] = field(default_factory=list)
    last_combined_output_path: str = ""
    combined_export_settings: CombinedExportSettings = field(default_factory=CombinedExportSettings)
    queue_settings: QueueSettings = field(default_factory=QueueSettings)
    intro_clip: IntroOutroClip = field(default_factory=IntroOutroClip)
    outro_clip: IntroOutroClip = field(default_factory=IntroOutroClip)
    practiscore_source_file: str = ""
    excluded_imported_stage_numbers: list[int] = field(default_factory=list)

    @property
    def active_stage(self) -> ProjectStage | None:
        if not self.stages or not self.active_stage_id:
            return self.stages[0] if self.stages else None
        for stage in self.stages:
            if stage.id == self.active_stage_id:
                return stage
        return self.stages[0] if self.stages else None

    def sort_shots(self) -> None:
        self.analysis.shots.sort(key=lambda shot: shot.time_ms)

    def touch(self) -> None:
        self.updated_at = datetime.now(UTC)


def _serialize(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    if is_dataclass(value):
        return {item.name: _serialize(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, list):
        return [_serialize(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    return value


def stage_to_dict(stage: ProjectStage) -> dict[str, Any]:
    return {
        "id": stage.id,
        "label": stage.label,
        "order_index": stage.order_index,
        "imported_stage_number": stage.imported_stage_number,
        "imported_stage_name": stage.imported_stage_name,
        "primary_media": _serialize(stage.primary_media),
        "primary_trim_derivative": _serialize(stage.primary_trim_derivative),
        "added_media": _serialize(stage.added_media),
        "analysis": _serialize(stage.analysis),
        "scoring": _serialize(stage.scoring),
        "overlay": _serialize(stage.overlay),
        "popups": _serialize(stage.popups),
        "popup_template": _serialize(stage.popup_template),
        "merge": _serialize(stage.merge),
        "export": _serialize(stage.export),
        "queue_status": str(stage.queue_status),
        "queue_snapshot": stage.queue_snapshot,
        "last_processed_at": stage.last_processed_at,
        "last_output_path": stage.last_output_path,
        "presentation_overridden": stage.presentation_overridden,
    }


def _stage_from_dict(data: dict[str, Any]) -> ProjectStage:
    primary_media_data = data.get("primary_media")
    primary_media = (
        _video_from_dict(primary_media_data)
        if isinstance(primary_media_data, dict)
        else VideoAsset()
    )
    added_media_data = data.get("added_media", [])
    added_media = (
        [_merge_source_from_dict(item) for item in added_media_data]
        if isinstance(added_media_data, list)
        else []
    )
    analysis_data = data.get("analysis")
    return ProjectStage(
        id=str(data.get("id", uuid4().hex)),
        label=str(data.get("label", "")),
        order_index=int(data.get("order_index", 1)),
        imported_stage_number=None
        if data.get("imported_stage_number") in {None, ""}
        else int(data["imported_stage_number"]),
        imported_stage_name=str(data.get("imported_stage_name", "")),
        primary_media=primary_media,
        primary_trim_derivative=_merge_source_trim_derivative_from_dict(
            data.get("primary_trim_derivative"),
            asset=primary_media,
        ),
        added_media=added_media,
        analysis=_analysis_state_from_dict(analysis_data),
        scoring=_scoring_from_dict(data.get("scoring"))
        if isinstance(data.get("scoring"), dict)
        else ScoringState(),
        overlay=_overlay_from_dict(data.get("overlay"))
        if isinstance(data.get("overlay"), dict)
        else OverlaySettings(),
        popups=[],
        popup_template=_popup_template_from_dict(data.get("popup_template")),
        merge=_merge_from_dict(data.get("merge"))
        if isinstance(data.get("merge"), dict)
        else MergeSettings(),
        export=_export_from_dict(data.get("export"))
        if isinstance(data.get("export"), dict)
        else ExportSettings(),
        queue_status=QueueStatus(str(data.get("queue_status", "not_queued")).strip().lower()),
        queue_snapshot=data.get("queue_snapshot", {})
        if isinstance(data.get("queue_snapshot"), dict)
        else {},
        last_processed_at=str(data.get("last_processed_at", "") or ""),
        last_output_path=str(data.get("last_output_path", "") or ""),
        presentation_overridden=bool(data.get("presentation_overridden", False)),
    )


def _scoring_from_dict(data: dict[str, Any]) -> ScoringState:
    return ScoringState(
        enabled=bool(data.get("enabled", True)),
        ruleset=str(data.get("ruleset", "uspsa_minor")),
        match_type=str(data.get("match_type", "")),
        stage_number=None if data.get("stage_number") in {None, ""} else int(data["stage_number"]),
        competitor_name=str(data.get("competitor_name", "")),
        competitor_place=None
        if data.get("competitor_place") in {None, ""}
        else int(data["competitor_place"]),
        classification=str(data.get("classification", "")),
        division=str(data.get("division", "")),
        practiscore_source_path=str(data.get("practiscore_source_path", "")),
        practiscore_source_name=str(data.get("practiscore_source_name", "")),
        penalties=float(data.get("penalties", 0)),
        point_map={str(key): float(value) for key, value in data.get("point_map", {}).items()},
        penalty_counts={
            str(key): float(value) for key, value in data.get("penalty_counts", {}).items()
        },
        hit_factor=None if data.get("hit_factor") is None else float(data["hit_factor"]),
        imported_stage=_imported_stage_from_dict(data.get("imported_stage")),
        comparison_competitors=[
            {str(key): value for key, value in item.items()}
            for item in data.get("comparison_competitors", [])
            if isinstance(item, dict)
        ],
    )


def _overlay_from_dict(data: dict[str, Any]) -> OverlaySettings:
    return OverlaySettings(
        position=OverlayPosition(data.get("position", OverlayPosition.BOTTOM.value)),
        badge_size=BadgeSize(data.get("badge_size", BadgeSize.M.value)),
        style_type=str(data.get("style_type", "square")),
        spacing=int(data.get("spacing", 8)),
        margin=int(data.get("margin", 8)),
        max_visible_shots=int(data.get("max_visible_shots", 4)),
        shot_quadrant=str(data.get("shot_quadrant", "bottom_left")),
        shot_direction=str(data.get("shot_direction", "right")),
        custom_x=None if data.get("custom_x") in {None, ""} else float(data["custom_x"]),
        custom_y=None if data.get("custom_y") in {None, ""} else float(data["custom_y"]),
        timer_x=None if data.get("timer_x") in {None, ""} else float(data["timer_x"]),
        timer_y=None if data.get("timer_y") in {None, ""} else float(data["timer_y"]),
        draw_x=None if data.get("draw_x") in {None, ""} else float(data["draw_x"]),
        draw_y=None if data.get("draw_y") in {None, ""} else float(data["draw_y"]),
        score_x=None if data.get("score_x") in {None, ""} else float(data["score_x"]),
        score_y=None if data.get("score_y") in {None, ""} else float(data["score_y"]),
        bubble_width=int(data.get("bubble_width", 0)),
        bubble_height=int(data.get("bubble_height", 0)),
        font_family=str(data.get("font_family", default_overlay_font_family())),
        font_size=int(data.get("font_size", 14)),
        font_bold=bool(data.get("font_bold", True)),
        font_italic=bool(data.get("font_italic", False)),
        show_timer=bool(data.get("show_timer", True)),
        show_draw=bool(data.get("show_draw", True)),
        show_shots=bool(data.get("show_shots", True)),
        show_shot_scores=bool(data.get("show_shot_scores", True)),
        show_score=bool(data.get("show_score", True)),
        timer_lock_to_stack=bool(data.get("timer_lock_to_stack", True)),
        draw_lock_to_stack=bool(data.get("draw_lock_to_stack", True)),
        score_lock_to_stack=bool(data.get("score_lock_to_stack", True)),
        custom_box_enabled=bool(data.get("custom_box_enabled", False)),
        custom_box_mode=str(data.get("custom_box_mode", "manual")),
        custom_box_text=str(data.get("custom_box_text", "")),
        custom_box_quadrant=str(data.get("custom_box_quadrant", "top_right")),
        custom_box_x=(
            None if data.get("custom_box_x") in {None, ""} else float(data["custom_box_x"])
        ),
        custom_box_y=(
            None if data.get("custom_box_y") in {None, ""} else float(data["custom_box_y"])
        ),
        custom_box_background_color=str(data.get("custom_box_background_color", "#000000")),
        custom_box_text_color=str(data.get("custom_box_text_color", "#ffffff")),
        custom_box_opacity=float(data.get("custom_box_opacity", 0.9)),
        custom_box_width=int(data.get("custom_box_width", 0)),
        custom_box_height=int(data.get("custom_box_height", 0)),
        text_boxes=[
            _overlay_text_box_from_dict(item)
            for item in data.get("text_boxes", [])
            if isinstance(item, dict)
        ],
        timer_badge=_badge_style_from_dict(data.get("timer_badge")),
        shot_badge=_badge_style_from_dict(data.get("shot_badge")),
        current_shot_badge=_badge_style_from_dict(data.get("current_shot_badge")),
        hit_factor_badge=_badge_style_from_dict(data.get("hit_factor_badge")),
        scoring_colors={
            **OverlaySettings().scoring_colors,
            **_normalize_scoring_color_map(data.get("scoring_colors", {})),
        },
    )


def _merge_from_dict(data: dict[str, Any]) -> MergeSettings:
    return MergeSettings(
        enabled=bool(data.get("enabled", True)),
        layout=MergeLayout(data.get("layout", MergeLayout.SIDE_BY_SIDE.value)),
        pip_size=PipSize(data.get("pip_size", PipSize.MEDIUM.value)),
        pip_size_percent=int(data.get("pip_size_percent", 35)),
        pip_x=float(data.get("pip_x", 1.0)),
        pip_y=float(data.get("pip_y", 1.0)),
        primary_is_left_or_top=bool(data.get("primary_is_left_or_top", True)),
    )


def _export_from_dict(data: dict[str, Any]) -> ExportSettings:
    return ExportSettings(
        quality=ExportQuality(data.get("quality", ExportQuality.HIGH.value)),
        aspect_ratio=AspectRatio(data.get("aspect_ratio", AspectRatio.ORIGINAL.value)),
        crop_center_x=float(data.get("crop_center_x", 0.5)),
        crop_center_y=float(data.get("crop_center_y", 0.5)),
        output_path=data.get("output_path"),
        preset=ExportPreset(data.get("preset", ExportPreset.SOURCE.value)),
        target_width=None if data.get("target_width") in {None, ""} else int(data["target_width"]),
        target_height=None
        if data.get("target_height") in {None, ""}
        else int(data["target_height"]),
        frame_rate=ExportFrameRate(data.get("frame_rate", ExportFrameRate.SOURCE.value)),
        video_codec=ExportVideoCodec(data.get("video_codec", ExportVideoCodec.H264.value)),
        video_bitrate_mbps=float(data.get("video_bitrate_mbps", 15.0)),
        audio_codec=ExportAudioCodec(data.get("audio_codec", ExportAudioCodec.AAC.value)),
        audio_sample_rate=int(data.get("audio_sample_rate", 48000)),
        audio_bitrate_kbps=int(data.get("audio_bitrate_kbps", 320)),
        color_space=ExportColorSpace(data.get("color_space", ExportColorSpace.BT709_SDR.value)),
        two_pass=bool(data.get("two_pass", False)),
        ffmpeg_preset=str(data.get("ffmpeg_preset", "medium")),
        last_log=str(data.get("last_log", "")),
        last_error=None if data.get("last_error") in {None, ""} else str(data["last_error"]),
    )


def queue_entry_to_dict(entry: QueueEntry) -> dict[str, Any]:
    return {
        "id": entry.id,
        "stage_id": entry.stage_id,
        "status": str(entry.status),
        "snapshot": entry.snapshot,
        "created_at": entry.created_at.isoformat(),
        "processed_at": entry.processed_at,
        "output_path": entry.output_path,
        "error_message": entry.error_message,
    }


def _queue_entry_from_dict(data: dict[str, Any]) -> QueueEntry:
    created_at = datetime.now(UTC)
    if data.get("created_at"):
        try:
            created_at = datetime.fromisoformat(str(data["created_at"]))
        except (ValueError, TypeError):
            pass
    return QueueEntry(
        id=str(data.get("id", uuid4().hex)),
        stage_id=str(data.get("stage_id", "")),
        status=QueueStatus(str(data.get("status", "not_queued")).strip().lower()),
        snapshot=data.get("snapshot", {}) if isinstance(data.get("snapshot"), dict) else {},
        created_at=created_at,
        processed_at=str(data.get("processed_at", "") or ""),
        output_path=str(data.get("output_path", "") or ""),
        error_message=str(data.get("error_message", "") or ""),
    )


def _combined_export_settings_from_dict(data: dict[str, Any]) -> CombinedExportSettings:
    payload = data if isinstance(data, dict) else {}
    return CombinedExportSettings(
        mode=CombinedExportMode(str(payload.get("mode", "plain_stitch")).strip().lower()),
        separator_enabled=bool(payload.get("separator_enabled", False)),
        separator_duration_s=float(payload.get("separator_duration_s", 0.5)),
        separator_text=str(payload.get("separator_text", "") or ""),
        separator_image_path=str(payload.get("separator_image_path", "") or ""),
    )


def _queue_settings_from_dict(data: dict[str, Any] | None) -> QueueSettings:
    payload = data if isinstance(data, dict) else {}
    try:
        fade_in_s = float(payload.get("fade_in_s", 0.5))
    except (TypeError, ValueError):
        fade_in_s = 0.5
    try:
        fade_out_s = float(payload.get("fade_out_s", 0.5))
    except (TypeError, ValueError):
        fade_out_s = 0.5
    if not math.isfinite(fade_in_s) or fade_in_s < 0:
        fade_in_s = 0.5
    if not math.isfinite(fade_out_s) or fade_out_s < 0:
        fade_out_s = 0.5
    return QueueSettings(
        fade_in_s=fade_in_s,
        fade_out_s=fade_out_s,
        intro_path=str(payload.get("intro_path", "") or ""),
        outro_path=str(payload.get("outro_path", "") or ""),
        include_intro=bool(payload.get("include_intro", bool(payload.get("intro_path")))),
        include_outro=bool(payload.get("include_outro", bool(payload.get("outro_path")))),
    )


def _intro_outro_clip_from_dict(data: dict[str, Any] | None, legacy_path: str = "") -> IntroOutroClip:
    payload = data if isinstance(data, dict) else {}
    asset_payload = payload.get("asset") if isinstance(payload.get("asset"), dict) else {}
    asset = _video_from_dict(asset_payload)
    if not asset.path and legacy_path:
        asset.path = legacy_path
    overlay_payload = payload.get("overlay") if isinstance(payload.get("overlay"), dict) else None
    return IntroOutroClip(
        asset=asset,
        overlay=(
            _overlay_from_dict(overlay_payload)
            if overlay_payload is not None
            else _boundary_overlay_defaults()
        ),
    )


def project_to_dict(project: Project) -> dict[str, Any]:
    data = _serialize(project)
    overlay = data.get("overlay")
    if isinstance(overlay, dict):
        overlay["scoring_colors"] = _normalize_scoring_color_map(overlay.get("scoring_colors", {}))
        overlay.pop("review_boxes_lock_to_stack", None)
    merge_sources = data.get("merge_sources")
    primary_trim_derivative = data.get("primary_trim_derivative")
    if isinstance(primary_trim_derivative, dict):
        if not primary_trim_derivative.get("derivative_path"):
            primary_trim_derivative.pop("derivative_path", None)
            primary_trim_derivative.pop("derivative_asset", None)
        elif not isinstance(
            primary_trim_derivative.get("derivative_asset"), dict
        ) or not primary_trim_derivative["derivative_asset"].get("path"):
            primary_trim_derivative.pop("derivative_asset", None)
        if project.primary_trim_derivative.start_s is None:
            primary_trim_derivative.pop("start_s", None)
        if project.primary_trim_derivative.end_s is None:
            primary_trim_derivative.pop("end_s", None)
        if project.primary_trim_derivative.active_path_kind == MergeSourceAssetPathKind.ORIGINAL:
            primary_trim_derivative.pop("active_path_kind", None)
        default_original_path = project.primary_video.path or ""
        if project.primary_trim_derivative.original_path in {"", default_original_path}:
            primary_trim_derivative.pop("original_path", None)
        if not primary_trim_derivative:
            data.pop("primary_trim_derivative", None)
    if isinstance(merge_sources, list):
        for index, (item, source) in enumerate(
            zip(merge_sources, project.merge_sources, strict=False)
        ):
            if not isinstance(item, dict):
                continue
            placement = item.get("placement")
            if isinstance(placement, dict):
                default_slot = _default_merge_source_placement_slot(source.placement.mode)
                if source.placement.mode == MergePlacementMode.AUTO:
                    placement.pop("mode", None)
                if source.placement.slot == default_slot:
                    placement.pop("slot", None)
                if source.placement.target_kind == MergePlacementTargetKind.PRIMARY_VIDEO:
                    placement.pop("target_kind", None)
                if source.placement.target_source_id in {None, ""}:
                    placement.pop("target_source_id", None)
                if source.placement.order_index in {None, index}:
                    placement.pop("order_index", None)
                if source.placement.layer_index in {
                    None,
                    index,
                    source.placement.order_index,
                }:
                    placement.pop("layer_index", None)
                if not placement:
                    item.pop("placement", None)
            trim_derivative = item.get("trim_derivative")
            if isinstance(trim_derivative, dict):
                if source.trim_derivative.derivative_path in {None, ""}:
                    trim_derivative.pop("derivative_path", None)
                    trim_derivative.pop("derivative_asset", None)
                elif not isinstance(
                    trim_derivative.get("derivative_asset"), dict
                ) or not trim_derivative["derivative_asset"].get("path"):
                    trim_derivative.pop("derivative_asset", None)
                if source.trim_derivative.start_s is None:
                    trim_derivative.pop("start_s", None)
                if source.trim_derivative.end_s is None:
                    trim_derivative.pop("end_s", None)
                if source.trim_derivative.active_path_kind == MergeSourceAssetPathKind.ORIGINAL:
                    trim_derivative.pop("active_path_kind", None)
                default_original_path = ""
                if source.asset.path and (
                    source.trim_derivative.derivative_path is None
                    or source.asset.path != source.trim_derivative.derivative_path
                ):
                    default_original_path = source.asset.path
                if source.trim_derivative.original_path in {"", default_original_path}:
                    trim_derivative.pop("original_path", None)
                if not trim_derivative:
                    item.pop("trim_derivative", None)
    data["schema_version"] = 2
    data["stages"] = [stage_to_dict(stage) for stage in project.stages]
    data["active_stage_id"] = project.active_stage_id
    data["queue"] = [queue_entry_to_dict(entry) for entry in project.queue]
    data["last_combined_output_path"] = project.last_combined_output_path
    data["combined_export_settings"] = _serialize(project.combined_export_settings)
    data["queue_settings"] = _serialize(project.queue_settings)
    data["intro_clip"] = _serialize(project.intro_clip)
    data["outro_clip"] = _serialize(project.outro_clip)
    data["practiscore_source_file"] = project.practiscore_source_file
    data["excluded_imported_stage_numbers"] = sorted(set(project.excluded_imported_stage_numbers))
    data.pop("_stages", None)
    data.pop("_queue", None)
    return _promote_camera_role_key(data)


def _normalize_merge_layout(value: Any) -> MergeLayout:
    try:
        return MergeLayout(str(value or MergeLayout.SIDE_BY_SIDE.value).strip().lower())
    except ValueError:
        return MergeLayout.SIDE_BY_SIDE


def _normalize_pip_size(value: Any) -> PipSize:
    try:
        return PipSize(str(value or PipSize.MEDIUM.value).strip())
    except ValueError:
        return PipSize.MEDIUM


def _default_merge_pip_size_percent(pip_size: PipSize) -> int:
    return {
        PipSize.SMALL: 25,
        PipSize.MEDIUM: 35,
        PipSize.LARGE: 50,
    }[pip_size]


def _normalize_merge_pip_size_percent(value: Any, *, pip_size: PipSize) -> int:
    default_percent = _default_merge_pip_size_percent(pip_size)
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return default_percent
    return normalized if normalized > 0 else default_percent


def _parse_enum(enum_type: type[StrEnum], value: str | None, default: StrEnum) -> StrEnum:
    if value is None:
        return default
    return enum_type(value)


def _badge_style_from_dict(
    data: dict[str, Any] | None, fallback: BadgeStyle | None = None
) -> BadgeStyle:
    default = fallback or BadgeStyle()
    payload = data or {}
    return BadgeStyle(
        background_color=str(
            payload.get("background_color", default.background_color) or default.background_color
        ),
        text_color=str(payload.get("text_color", default.text_color) or default.text_color),
        opacity=max(0.0, min(1.0, float(payload.get("opacity", default.opacity)))),
    )


def _normalize_scoring_color_map(data: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (data or {}).items():
        normalized_key = str(key).strip()
        if not normalized_key or "|" in normalized_key:
            continue
        normalized[normalized_key] = str(value)
    return normalized


_TEXT_BOX_SOURCES = {"manual", "imported_summary", "match_summary"}
_TEXT_BOX_QUADRANTS = {
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
    "custom",
}

_POPUP_BUBBLE_ANCHOR_MODES = {"time", "shot"}
_POPUP_BUBBLE_QUADRANTS = {
    "top_left",
    "top_middle",
    "top_right",
    "middle_left",
    "middle_middle",
    "middle_right",
    "bottom_left",
    "bottom_middle",
    "bottom_right",
    "custom",
}
_POPUP_MOTION_MODES = {"fixed", "guided", "manual", "auto"}
_POPUP_MOTION_EASINGS = {"linear", "hold", "ease_in", "ease_out", "ease_in_out"}

_UI_STATE_ACTIVE_TOOLS = {
    "project",
    "media",
    "scoring",
    "shotml",
    "timing",
    "merge",
    "overlay",
    "review",
    "markers",
    "popup",
    "settings",
    "export",
    "metrics",
    "intro-outro",
    "queue",
}

_UI_STATE_WAVEFORM_MODES = {"select", "add"}


def _normalize_text_box_source(value: str | None) -> str:
    normalized = str(value or "manual")
    return normalized if normalized in _TEXT_BOX_SOURCES else "manual"


def _normalize_text_box_quadrant(value: str | None) -> str:
    normalized = str(value or "top_right")
    return normalized if normalized in _TEXT_BOX_QUADRANTS else "top_right"


def _normalize_popup_bubble_anchor_mode(value: Any, shot_id: str | None = None) -> str:
    normalized = str(value or "").strip()
    if normalized in _POPUP_BUBBLE_ANCHOR_MODES:
        return normalized
    return "shot" if shot_id else "time"


def _normalize_popup_bubble_quadrant(value: Any, *, x: Any = None, y: Any = None) -> str:
    normalized = str(value or "").strip()
    if normalized in _POPUP_BUBBLE_QUADRANTS:
        return normalized
    if x not in {None, ""} or y not in {None, ""}:
        return "custom"
    return "middle_middle"


def _normalize_popup_motion_point(data: Any) -> PopupMotionPoint | None:
    if not isinstance(data, dict):
        return None
    try:
        offset_ms = max(0, round(float(data.get("offset_ms", data.get("time_ms", 0)) or 0)))
    except (TypeError, ValueError):
        offset_ms = 0
    try:
        x = max(0.0, min(1.0, float(data.get("x", 0.5))))
    except (TypeError, ValueError):
        x = 0.5
    try:
        y = max(0.0, min(1.0, float(data.get("y", 0.5))))
    except (TypeError, ValueError):
        y = 0.5
    easing = str(data.get("easing", "linear") or "linear").strip().lower()
    if easing not in _POPUP_MOTION_EASINGS:
        easing = "linear"
    return PopupMotionPoint(offset_ms=offset_ms, x=x, y=y, easing=easing)


def _normalize_popup_motion_path(data: Any) -> list[PopupMotionPoint]:
    if not isinstance(data, list):
        return []
    points = [point for item in data if (point := _normalize_popup_motion_point(item)) is not None]
    points.sort(key=lambda point: point.offset_ms)
    deduped: list[PopupMotionPoint] = []
    for point in points:
        if deduped and deduped[-1].offset_ms == point.offset_ms:
            deduped[-1] = point
        else:
            deduped.append(point)
    return deduped


def _normalize_popup_motion_mode(
    value: Any,
    *,
    follow_motion: bool = False,
    motion_path: list[PopupMotionPoint] | None = None,
) -> str:
    normalized = str(value or "").strip().lower()
    has_motion = follow_motion or bool(motion_path)
    if normalized in _POPUP_MOTION_MODES and not (normalized == "fixed" and has_motion):
        return normalized
    if has_motion:
        return "manual"
    return "fixed"


def _normalize_ui_state_active_tool(value: Any) -> str:
    normalized = str(value or "project")
    if normalized == "popup":
        normalized = "markers"
    return normalized if normalized in _UI_STATE_ACTIVE_TOOLS else "project"


def _normalize_ui_state_waveform_mode(value: Any) -> str:
    normalized = str(value or "select")
    return normalized if normalized in _UI_STATE_WAVEFORM_MODES else "select"


def _ui_state_bool_map(data: Any) -> dict[str, bool]:
    if not isinstance(data, dict):
        return {}
    normalized: dict[str, bool] = {}
    for key, value in data.items():
        clean_key = str(key).strip()
        if clean_key:
            normalized[clean_key] = bool(value)
    return normalized


def _ui_state_float_map(data: Any, *, minimum: float = 0.0) -> dict[str, float]:
    if not isinstance(data, dict):
        return {}
    normalized: dict[str, float] = {}
    for key, value in data.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        if numeric < minimum:
            continue
        normalized[clean_key] = numeric
    return normalized


def _ui_state_string_list(data: Any) -> list[str]:
    if not isinstance(data, list):
        return []
    normalized: list[str] = []
    for value in data:
        clean_value = str(value).strip()
        if clean_value:
            normalized.append(clean_value)
    return normalized


def _overlay_text_box_from_dict(
    data: dict[str, Any], legacy_lock_to_stack: bool = False
) -> OverlayTextBox:
    box = OverlayTextBox(
        id=str(data.get("id") or uuid4().hex),
        enabled=bool(data.get("enabled", True)),
        lock_to_stack=bool(data.get("lock_to_stack", legacy_lock_to_stack)),
        source=_normalize_text_box_source(data.get("source")),
        text=str(data.get("text", ""))[:500],
        quadrant=_normalize_text_box_quadrant(data.get("quadrant")),
        x=None if data.get("x") in {None, ""} else float(data["x"]),
        y=None if data.get("y") in {None, ""} else float(data["y"]),
        background_color=str(data.get("background_color", "#000000")),
        text_color=str(data.get("text_color", "#ffffff")),
        opacity=float(data.get("opacity", 0.9)),
        width=int(data.get("width", 0)),
        height=int(data.get("height", 0)),
        summary_metric_ids=_ui_state_string_list(data.get("summary_metric_ids")),
        style_type=str(data.get("style_type", "square") or "square"),
        font_family=str(
            data.get("font_family", default_overlay_font_family()) or default_overlay_font_family()
        )[:80],
        font_size=max(8, min(72, int(data.get("font_size", 14) or 14))),
        font_bold=bool(data.get("font_bold", True)),
        font_italic=bool(data.get("font_italic", False)),
    )
    if box.x is not None or box.y is not None:
        box.quadrant = "custom"
    return box


def _popup_bubble_from_dict(data: dict[str, Any]) -> PopupBubble:
    shot_id = None if data.get("shot_id") in {None, ""} else str(data["shot_id"])
    x_value = None if data.get("x") in {None, ""} else float(data["x"])
    y_value = None if data.get("y") in {None, ""} else float(data["y"])
    motion_path = _normalize_popup_motion_path(data.get("motion_path"))
    follow_motion = bool(data.get("follow_motion", bool(motion_path)))
    return PopupBubble(
        id=str(data.get("id") or uuid4().hex),
        enabled=bool(data.get("enabled", True)),
        name=str(data.get("name", ""))[:80],
        text=str(data.get("text", ""))[:500],
        anchor_mode=_normalize_popup_bubble_anchor_mode(data.get("anchor_mode"), shot_id),
        shot_id=shot_id,
        time_ms=max(0, int(data.get("time_ms", 0) or 0)),
        duration_ms=max(1, int(data.get("duration_ms", 1000) or 1000)),
        quadrant=_normalize_popup_bubble_quadrant(data.get("quadrant"), x=x_value, y=y_value),
        x=max(0.0, min(1.0, x_value if x_value is not None else 0.5)),
        y=max(0.0, min(1.0, y_value if y_value is not None else 0.5)),
        motion_mode=_normalize_popup_motion_mode(
            data.get("motion_mode"),
            follow_motion=follow_motion,
            motion_path=motion_path,
        ),
        follow_motion=follow_motion,
        motion_path=motion_path,
        background_color=str(data.get("background_color", "#000000")),
        text_color=str(data.get("text_color", "#ffffff")),
        opacity=max(0.0, min(1.0, float(data.get("opacity", 0.9)))),
        width=max(0, int(data.get("width", 0) or 0)),
        height=max(0, int(data.get("height", 0) or 0)),
        style_type=str(data.get("style_type", "square") or "square"),
        font_family=str(
            data.get("font_family", default_overlay_font_family()) or default_overlay_font_family()
        )[:80],
        font_size=max(8, min(72, int(data.get("font_size", 14) or 14))),
        font_bold=bool(data.get("font_bold", True)),
        font_italic=bool(data.get("font_italic", False)),
        content_type=str(data.get("content_type", "text") or "text"),
        image_path=str(data.get("image_path", "") or ""),
        image_scale_mode=str(data.get("image_scale_mode", "contain") or "contain"),
    )


def _popup_template_from_dict(data: dict[str, Any] | None) -> PopupTemplate:
    payload = data if isinstance(data, dict) else {}
    follow_motion = bool(payload.get("follow_motion", False))
    return PopupTemplate(
        enabled=bool(payload.get("enabled", True)),
        content_type=str(payload.get("content_type", "text") or "text"),
        text_source=str(payload.get("text_source", "score") or "score"),
        duration_ms=max(1, int(payload.get("duration_ms", 1000) or 1000)),
        use_shot_split_duration=bool(payload.get("use_shot_split_duration", False)),
        quadrant=_normalize_popup_bubble_quadrant(payload.get("quadrant")),
        width=max(0, int(payload.get("width", 0) or 0)),
        height=max(0, int(payload.get("height", 0) or 0)),
        motion_mode=_normalize_popup_motion_mode(
            payload.get("motion_mode"), follow_motion=follow_motion
        ),
        follow_motion=follow_motion,
        background_color=str(payload.get("background_color", "#000000") or "#000000"),
        text_color=str(payload.get("text_color", "#ffffff") or "#ffffff"),
        opacity=max(0.0, min(1.0, float(payload.get("opacity", 0.9)))),
        style_type=str(payload.get("style_type", "square") or "square"),
        font_family=str(
            payload.get("font_family", default_overlay_font_family())
            or default_overlay_font_family()
        )[:80],
        font_size=max(8, min(72, int(payload.get("font_size", 14) or 14))),
        font_bold=bool(payload.get("font_bold", True)),
        font_italic=bool(payload.get("font_italic", False)),
    )


def legacy_custom_box_as_text_box(
    overlay: OverlaySettings, legacy_lock_to_stack: bool = False
) -> OverlayTextBox | None:
    has_legacy_box = (
        overlay.custom_box_enabled
        or overlay.custom_box_mode == "imported_summary"
        or bool(overlay.custom_box_text.strip())
    )
    if not has_legacy_box:
        return None
    box = OverlayTextBox(
        enabled=overlay.custom_box_enabled,
        lock_to_stack=legacy_lock_to_stack,
        source=_normalize_text_box_source(overlay.custom_box_mode),
        text=overlay.custom_box_text,
        quadrant=_normalize_text_box_quadrant(overlay.custom_box_quadrant),
        x=overlay.custom_box_x,
        y=overlay.custom_box_y,
        background_color=overlay.custom_box_background_color,
        text_color=overlay.custom_box_text_color,
        opacity=float(overlay.custom_box_opacity),
        width=int(overlay.custom_box_width),
        height=int(overlay.custom_box_height),
        style_type="square",
        font_family=overlay.font_family,
        font_size=overlay.font_size,
        font_bold=overlay.font_bold,
        font_italic=overlay.font_italic,
    )
    if box.x is not None or box.y is not None:
        box.quadrant = "custom"
    return box


def overlay_text_boxes_for_render(overlay: OverlaySettings) -> list[OverlayTextBox]:
    if overlay.text_boxes:
        return overlay.text_boxes
    legacy_box = legacy_custom_box_as_text_box(overlay)
    return [] if legacy_box is None else [legacy_box]


def sync_overlay_legacy_custom_box_fields(overlay: OverlaySettings) -> None:
    boxes = overlay.text_boxes
    if not boxes:
        overlay.custom_box_enabled = False
        overlay.custom_box_mode = "manual"
        overlay.custom_box_text = ""
        return
    primary = next((box for box in boxes if box.source == "imported_summary"), boxes[0])
    overlay.custom_box_enabled = bool(primary.enabled)
    overlay.custom_box_mode = _normalize_text_box_source(primary.source)
    overlay.custom_box_text = primary.text[:500]
    overlay.custom_box_quadrant = _normalize_text_box_quadrant(primary.quadrant)
    overlay.custom_box_x = primary.x
    overlay.custom_box_y = primary.y
    overlay.custom_box_background_color = primary.background_color
    overlay.custom_box_text_color = primary.text_color
    overlay.custom_box_opacity = float(primary.opacity)
    overlay.custom_box_width = int(primary.width)
    overlay.custom_box_height = int(primary.height)
    if overlay.custom_box_x is not None or overlay.custom_box_y is not None:
        overlay.custom_box_quadrant = "custom"


def _score_mark_from_dict(data: dict[str, Any] | None) -> ScoreMark:
    if not data:
        return ScoreMark()
    return ScoreMark(
        letter=ScoreLetter(data.get("letter", ScoreLetter.A.value)),
        x_norm=float(data.get("x_norm", 0.5)),
        y_norm=float(data.get("y_norm", 0.5)),
        animation_preset=str(data.get("animation_preset", "fade_scale")),
        penalty_counts={
            str(key): float(value) for key, value in data.get("penalty_counts", {}).items()
        },
    )


def _imported_stage_from_dict(data: dict[str, Any] | None) -> ImportedStageScore | None:
    if not data:
        return None
    competitor_place = data.get("competitor_place")
    stage_number = data.get("stage_number")
    stage_place = data.get("stage_place")
    raw_seconds = data.get("raw_seconds")
    total_points = data.get("total_points")
    hit_factor = data.get("hit_factor")
    final_time = data.get("final_time")
    stage_points = data.get("stage_points")
    return ImportedStageScore(
        source_name=str(data.get("source_name", "")),
        source_path=str(data.get("source_path", "")),
        match_type=str(data.get("match_type", "")),
        competitor_name=str(data.get("competitor_name", "")),
        competitor_place=(None if competitor_place in {None, ""} else int(competitor_place)),
        stage_number=None if stage_number in {None, ""} else int(stage_number),
        stage_name=str(data.get("stage_name", "")),
        division=str(data.get("division", "")),
        classification=str(data.get("classification", "")),
        power_factor=str(data.get("power_factor", "")),
        raw_seconds=None if raw_seconds in {None, ""} else float(raw_seconds),
        aggregate_points=float(data.get("aggregate_points", 0.0)),
        total_points=None if total_points in {None, ""} else float(total_points),
        shot_penalties=float(data.get("shot_penalties", 0.0)),
        hit_factor=None if hit_factor in {None, ""} else float(hit_factor),
        final_time=None if final_time in {None, ""} else float(final_time),
        stage_points=None if stage_points in {None, ""} else float(stage_points),
        stage_place=None if stage_place in {None, ""} else int(stage_place),
        score_counts={
            str(key): float(value) for key, value in data.get("score_counts", {}).items()
        },
    )


def _path_looks_like_still_image(path: str) -> bool:
    return Path(path).suffix.lower() in _STILL_IMAGE_SUFFIXES


def _camera_role_payload_value(data: dict[str, Any] | None, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    for key in ("camera_role", "angle_role"):
        value = data.get(key)
        if value not in {None, ""}:
            return value
    return default


def _promote_camera_role_key(value: Any) -> Any:
    if isinstance(value, list):
        return [_promote_camera_role_key(item) for item in value]
    if isinstance(value, dict):
        promoted: dict[str, Any] = {}
        for key, item in value.items():
            promoted_key = "camera_role" if str(key) == "angle_role" else str(key)
            promoted[promoted_key] = _promote_camera_role_key(item)
        return promoted
    return value


def _merge_source_placement_from_dict(
    data: dict[str, Any] | None,
    *,
    payload: dict[str, Any] | None = None,
) -> MergeSourcePlacement:
    placement_data = data if isinstance(data, dict) else {}
    source = payload or {}
    target_source_id_value = placement_data.get(
        "target_source_id",
        source.get("target_source_id", source.get("base_source_id")),
    )
    target_source_id = None if target_source_id_value in {None, ""} else str(target_source_id_value)
    mode = _normalize_merge_source_placement_mode(
        placement_data.get(
            "mode",
            source.get("placement_mode", source.get("composition_mode")),
        )
    )
    target_kind = _normalize_merge_source_placement_target_kind(
        placement_data.get("target_kind", source.get("target_kind")),
        target_source_id=target_source_id,
    )
    if target_kind != MergePlacementTargetKind.MERGE_SOURCE:
        target_source_id = None
    return MergeSourcePlacement(
        mode=mode,
        slot=_normalize_merge_source_placement_slot(
            placement_data.get("slot", source.get("placement_slot")),
            mode=mode,
        ),
        target_kind=target_kind,
        target_source_id=target_source_id,
        order_index=_normalize_merge_source_index(
            placement_data.get(
                "order_index",
                source.get("order_index", source.get("stack_order", source.get("display_order"))),
            )
        ),
        layer_index=_normalize_merge_source_index(
            placement_data.get(
                "layer_index",
                source.get("layer_index", source.get("z_index")),
            )
        ),
    )


def _merge_source_trim_derivative_from_dict(
    data: dict[str, Any] | None,
    *,
    payload: dict[str, Any] | None = None,
    asset: VideoAsset | None = None,
) -> MergeSourceTrimDerivative:
    trim_data = data if isinstance(data, dict) else {}
    source = payload or {}
    asset_path = asset.path if asset is not None else ""
    derivative_path_value = trim_data.get(
        "derivative_path",
        source.get("trimmed_asset_path", source.get("derivative_asset_path")),
    )
    derivative_path = None if derivative_path_value in {None, ""} else str(derivative_path_value)
    original_path_value = trim_data.get(
        "original_path",
        source.get("original_asset_path", source.get("source_asset_path", "")),
    )
    original_path = str(original_path_value or "")
    if (
        not original_path
        and asset_path
        and (derivative_path is None or asset_path != derivative_path)
    ):
        original_path = asset_path
    derivative_asset_payload = trim_data.get("derivative_asset")
    derivative_asset = (
        _video_from_dict(derivative_asset_payload)
        if isinstance(derivative_asset_payload, dict)
        else VideoAsset(path=str(derivative_path or ""))
    )
    if derivative_path and not derivative_asset.path:
        derivative_asset.path = str(derivative_path)
    return MergeSourceTrimDerivative(
        original_path=original_path,
        derivative_path=derivative_path,
        derivative_asset=derivative_asset,
        active_path_kind=_normalize_merge_source_active_path_kind(
            trim_data.get(
                "active_path_kind",
                source.get("active_asset_path_kind", source.get("asset_path_kind")),
            ),
            asset_path=asset_path,
            original_path=original_path,
            derivative_path=derivative_path,
        ),
        start_s=_trim_float_or_none(trim_data.get("start_s")),
        end_s=_trim_float_or_none(trim_data.get("end_s")),
    )


def _finalize_merge_source_metadata(merge_sources: list[MergeSource]) -> None:
    for index, source in enumerate(merge_sources):
        placement = source.placement
        if placement.order_index is None:
            placement.order_index = index
        if placement.layer_index is None:
            placement.layer_index = placement.order_index
        if (
            placement.target_kind == MergePlacementTargetKind.MERGE_SOURCE
            and not placement.target_source_id
        ):
            placement.target_kind = MergePlacementTargetKind.PRIMARY_VIDEO
        if placement.target_kind != MergePlacementTargetKind.MERGE_SOURCE:
            placement.target_source_id = None
        default_slot = _default_merge_source_placement_slot(placement.mode)
        if placement.slot == MergePlacementSlot.AUTO and default_slot != MergePlacementSlot.AUTO:
            placement.slot = default_slot
        trim_derivative = source.trim_derivative
        if trim_derivative.derivative_path == "":
            trim_derivative.derivative_path = None
        if (
            trim_derivative.active_path_kind == MergeSourceAssetPathKind.LOCAL_DERIVATIVE
            and not trim_derivative.derivative_path
        ):
            trim_derivative.active_path_kind = MergeSourceAssetPathKind.ORIGINAL
        if (
            not trim_derivative.original_path
            and source.asset.path
            and (
                trim_derivative.derivative_path is None
                or source.asset.path != trim_derivative.derivative_path
            )
        ):
            trim_derivative.original_path = source.asset.path
        if trim_derivative.derivative_path and not trim_derivative.derivative_asset.path:
            trim_derivative.derivative_asset.path = str(trim_derivative.derivative_path)


def _finalize_primary_trim_derivative(
    primary_asset: VideoAsset,
    trim_derivative: MergeSourceTrimDerivative,
) -> None:
    if trim_derivative.derivative_path == "":
        trim_derivative.derivative_path = None
    if (
        trim_derivative.active_path_kind == MergeSourceAssetPathKind.LOCAL_DERIVATIVE
        and not trim_derivative.derivative_path
    ):
        trim_derivative.active_path_kind = MergeSourceAssetPathKind.ORIGINAL
    if not trim_derivative.original_path and primary_asset.path:
        trim_derivative.original_path = primary_asset.path
    if trim_derivative.derivative_path and not trim_derivative.derivative_asset.path:
        trim_derivative.derivative_asset.path = str(trim_derivative.derivative_path)


def _canonicalize_secondary_video_reference(project: Project) -> None:
    secondary_video = project.secondary_video
    if secondary_video is None:
        return

    secondary_path = str(secondary_video.path or "").strip()
    for source in project.merge_sources:
        if source.asset is secondary_video:
            project.secondary_video = source.asset
            return
        if secondary_path and str(source.asset.path or "").strip() == secondary_path:
            project.secondary_video = source.asset
            return


def _apply_legacy_merge_defaults_to_source(
    source: MergeSource,
    *,
    raw_source: dict[str, Any] | None,
    merge_layout: MergeLayout,
    merge_pip_size_percent: int,
    merge_pip_x: float,
    merge_pip_y: float,
    primary_is_left_or_top: bool,
) -> None:
    placement_payload = raw_source.get("placement") if isinstance(raw_source, dict) else None
    if not isinstance(placement_payload, dict):
        placement_payload = None

    has_explicit_mode = _payload_has_value(placement_payload, "mode") or _payload_has_value(
        raw_source,
        "placement_mode",
        "composition_mode",
    )
    has_explicit_slot = _payload_has_value(placement_payload, "slot") or _payload_has_value(
        raw_source,
        "placement_slot",
    )

    migrated_from_legacy_layout = False
    if (
        raw_source is not None
        and not has_explicit_mode
        and source.placement.mode == MergePlacementMode.AUTO
    ):
        source.placement.mode = _merge_layout_to_placement_mode(merge_layout)
        migrated_from_legacy_layout = True

    if source.pip_size_percent is None and not _payload_has_value(raw_source, "pip_size_percent"):
        source.pip_size_percent = merge_pip_size_percent
    if raw_source is not None:
        if not _payload_has_value(raw_source, "pip_x"):
            source.pip_x = merge_pip_x
        if not _payload_has_value(raw_source, "pip_y"):
            source.pip_y = merge_pip_y
    elif migrated_from_legacy_layout:
        source.pip_x = merge_pip_x
        source.pip_y = merge_pip_y

    if not has_explicit_slot:
        legacy_slot = _legacy_merge_source_slot(
            source.placement.mode,
            primary_is_left_or_top=primary_is_left_or_top,
        )
        if source.placement.slot in {
            MergePlacementSlot.AUTO,
            _default_merge_source_placement_slot(source.placement.mode),
        }:
            source.placement.slot = legacy_slot


def ensure_merge_source_composition_truth(
    project: Project,
    *,
    raw_merge_sources: list[dict[str, Any]] | None = None,
    secondary_video_is_explicitly_set: bool = True,
) -> None:
    project.merge.layout = _normalize_merge_layout(project.merge.layout)
    project.merge.pip_size = _normalize_pip_size(project.merge.pip_size)
    project.merge.pip_size_percent = _normalize_merge_pip_size_percent(
        project.merge.pip_size_percent,
        pip_size=project.merge.pip_size,
    )

    if not project.merge_sources and project.secondary_video is not None:
        placement_mode = _merge_layout_to_placement_mode(project.merge.layout)
        project.merge_sources = [
            MergeSource(
                asset=project.secondary_video,
                angle_role=default_merge_source_angle_role(project.secondary_video),
                pip_size_percent=project.merge.pip_size_percent,
                pip_x=float(project.merge.pip_x),
                pip_y=float(project.merge.pip_y),
                opacity=1.0,
                sync_offset_ms=int(project.analysis.sync_offset_ms),
                placement=MergeSourcePlacement(
                    mode=placement_mode,
                    slot=_legacy_merge_source_slot(
                        placement_mode,
                        primary_is_left_or_top=bool(project.merge.primary_is_left_or_top),
                    ),
                ),
            )
        ]

    normalized_raw_sources: list[dict[str, Any] | None] = []
    for item in raw_merge_sources or []:
        normalized_raw_sources.append(item if isinstance(item, dict) else None)
    while len(normalized_raw_sources) < len(project.merge_sources):
        normalized_raw_sources.append(None)

    for source, raw_source in zip(project.merge_sources, normalized_raw_sources, strict=False):
        _apply_legacy_merge_defaults_to_source(
            source,
            raw_source=raw_source,
            merge_layout=project.merge.layout,
            merge_pip_size_percent=project.merge.pip_size_percent,
            merge_pip_x=float(project.merge.pip_x),
            merge_pip_y=float(project.merge.pip_y),
            primary_is_left_or_top=bool(project.merge.primary_is_left_or_top),
        )

    _finalize_merge_source_metadata(project.merge_sources)
    if project.merge_sources:
        if secondary_video_is_explicitly_set:
            _canonicalize_secondary_video_reference(project)
        else:
            project.secondary_video = project.merge_sources[0].asset


def _merge_source_from_dict(data: dict[str, Any]) -> MergeSource:
    payload = data or {}
    asset_data = payload.get("asset", payload)
    asset = _video_from_dict(asset_data)
    return MergeSource(
        id=str(payload.get("id", uuid4().hex)),
        asset=asset,
        angle_role=_normalize_merge_source_angle_role(
            _camera_role_payload_value(payload),
            asset,
        ),
        pip_size_percent=(
            None
            if payload.get("pip_size_percent") in {None, ""}
            else int(payload.get("pip_size_percent"))
        ),
        pip_x=float(payload.get("pip_x", 1.0)),
        pip_y=float(payload.get("pip_y", 1.0)),
        opacity=max(0.0, min(1.0, float(payload.get("opacity", 1.0)))),
        sync_offset_ms=int(payload.get("sync_offset_ms", 0)),
        placement=_merge_source_placement_from_dict(payload.get("placement"), payload=payload),
        trim_derivative=_merge_source_trim_derivative_from_dict(
            payload.get("trim_derivative"),
            payload=payload,
            asset=asset,
        ),
    )


def _timing_event_from_dict(data: dict[str, Any]) -> TimingEvent:
    return TimingEvent(
        id=str(data.get("id", uuid4().hex)),
        kind=str(data.get("kind", "reload")),
        label=str(data.get("label", data.get("kind", "Reload"))),
        after_shot_id=None
        if data.get("after_shot_id") in {None, ""}
        else str(data["after_shot_id"]),
        before_shot_id=None
        if data.get("before_shot_id") in {None, ""}
        else str(data["before_shot_id"]),
        note=str(data.get("note", "")),
    )


def _coerce_dataclass_value(default: Any, value: Any) -> Any:
    if isinstance(default, bool):
        return bool(value)
    if isinstance(default, int) and not isinstance(default, bool):
        return int(value)
    if isinstance(default, float):
        return float(value)
    if value is None:
        return default
    return str(value)


def _shotml_settings_from_dict(
    data: dict[str, Any] | None, *, detection_threshold: float | None = None
) -> ShotMLSettings:
    defaults = ShotMLSettings()
    payload = data if isinstance(data, dict) else {}
    values: dict[str, Any] = {}
    for item in fields(ShotMLSettings):
        default = getattr(defaults, item.name)
        if item.name in payload:
            try:
                values[item.name] = _coerce_dataclass_value(default, payload[item.name])
            except (TypeError, ValueError):
                values[item.name] = default
        else:
            values[item.name] = default
    if detection_threshold is not None and "detection_threshold" not in payload:
        values["detection_threshold"] = float(detection_threshold)
    return ShotMLSettings(**values)


def _timing_change_proposal_from_dict(data: dict[str, Any]) -> TimingChangeProposal:
    evidence = data.get("evidence", {})
    return TimingChangeProposal(
        id=str(data.get("id", uuid4().hex)),
        proposal_type=str(data.get("proposal_type", "move_shot")),
        status=str(data.get("status", "pending")),
        shot_id=None if data.get("shot_id") in {None, ""} else str(data["shot_id"]),
        shot_number=None if data.get("shot_number") in {None, ""} else int(data["shot_number"]),
        source_time_ms=None
        if data.get("source_time_ms") in {None, ""}
        else int(data["source_time_ms"]),
        target_time_ms=None
        if data.get("target_time_ms") in {None, ""}
        else int(data["target_time_ms"]),
        alternate_shot_id=None
        if data.get("alternate_shot_id") in {None, ""}
        else str(data["alternate_shot_id"]),
        alternate_time_ms=None
        if data.get("alternate_time_ms") in {None, ""}
        else int(data["alternate_time_ms"]),
        confidence=None if data.get("confidence") in {None, ""} else float(data["confidence"]),
        support_confidence=None
        if data.get("support_confidence") in {None, ""}
        else float(data["support_confidence"]),
        message=str(data.get("message", "")),
        evidence=evidence if isinstance(evidence, dict) else {},
    )


def _secondary_source_analysis_from_dict(data: dict[str, Any]) -> SecondarySourceAnalysis:
    payload = data if isinstance(data, dict) else {}
    return SecondarySourceAnalysis(
        source_id=str(payload.get("source_id", "") or ""),
        beep_time_ms=(
            None if payload.get("beep_time_ms") in {None, ""} else int(payload.get("beep_time_ms"))
        ),
        sync_offset_ms=int(payload.get("sync_offset_ms", 0)),
        analysis_status=str(payload.get("analysis_status", "idle") or "idle"),
        analysis_message=str(payload.get("analysis_message", "") or ""),
        sync_source=str(payload.get("sync_source", "manual") or "manual"),
        waveform=[float(item) for item in payload.get("waveform", [])],
    )


def _analysis_state_from_dict(data: dict[str, Any] | None) -> AnalysisState:
    analysis_data = data if isinstance(data, dict) else {}
    return AnalysisState(
        beep_time_ms_primary=analysis_data.get("beep_time_ms_primary"),
        beep_time_ms_secondary=analysis_data.get("beep_time_ms_secondary"),
        analyzed_secondary_source_id=(
            None
            if analysis_data.get("analyzed_secondary_source_id") in {None, ""}
            else str(analysis_data.get("analyzed_secondary_source_id"))
        ),
        secondary_analysis_status=str(
            analysis_data.get("secondary_analysis_status", "idle") or "idle"
        ),
        secondary_analysis_message=str(analysis_data.get("secondary_analysis_message", "") or ""),
        secondary_sync_source=str(analysis_data.get("secondary_sync_source", "manual") or "manual"),
        sync_offset_ms=int(analysis_data.get("sync_offset_ms", 0)),
        detection_threshold=float(analysis_data.get("detection_threshold", 0.35)),
        shotml_settings=_shotml_settings_from_dict(
            analysis_data.get("shotml_settings"),
            detection_threshold=float(analysis_data.get("detection_threshold", 0.35)),
        ),
        timing_change_proposals=[
            _timing_change_proposal_from_dict(item)
            for item in analysis_data.get("timing_change_proposals", [])
            if isinstance(item, dict)
        ],
        last_shotml_run_summary=(
            analysis_data.get("last_shotml_run_summary", {})
            if isinstance(analysis_data.get("last_shotml_run_summary", {}), dict)
            else {}
        ),
        waveform_primary=[float(item) for item in analysis_data.get("waveform_primary", [])],
        waveform_secondary=[float(item) for item in analysis_data.get("waveform_secondary", [])],
        secondary_sources=[
            _secondary_source_analysis_from_dict(item)
            for item in analysis_data.get("secondary_sources", [])
            if isinstance(item, dict)
        ],
        shots=[_shot_from_dict(item) for item in analysis_data.get("shots", [])],
        events=[_timing_event_from_dict(item) for item in analysis_data.get("events", [])],
        detection_review_suggestions=[
            item
            for item in analysis_data.get("detection_review_suggestions", [])
            if isinstance(item, dict)
        ],
    )


def _shot_from_dict(data: dict[str, Any]) -> ShotEvent:
    shotml_time_ms = data.get("shotml_time_ms")
    shotml_confidence = data.get("shotml_confidence")
    source_value = data.get("source", ShotSource.AUTO.value)
    source = ShotSource(source_value)
    return ShotEvent(
        id=str(data.get("id", uuid4().hex)),
        time_ms=int(data.get("time_ms", 0)),
        shotml_time_ms=None if shotml_time_ms in {None, ""} else int(shotml_time_ms),
        shotml_confidence=None if shotml_confidence in {None, ""} else float(shotml_confidence),
        source=source,
        confidence=None if data.get("confidence") is None else float(data["confidence"]),
        score=_score_mark_from_dict(data.get("score")),
        user_added=bool(
            data.get("user_added", source == ShotSource.MANUAL and shotml_time_ms in {None, ""})
        ),
    )


def _video_from_dict(data: dict[str, Any] | None) -> VideoAsset:
    payload = data or {}
    path = str(payload.get("path", ""))
    media_kind = str(payload.get("media_kind", "") or "").strip().lower()
    inferred_still = _path_looks_like_still_image(path)
    still_image = payload.get("is_still_image")
    if media_kind == "animated_gif":
        still_image_value = False
    elif media_kind == "still_image":
        still_image_value = True
    elif still_image is None:
        still_image_value = inferred_still
    else:
        still_image_value = bool(still_image) or inferred_still
    if not media_kind:
        if Path(path).suffix.lower() == ".gif" and not still_image_value:
            media_kind = "animated_gif"
        elif still_image_value:
            media_kind = "still_image"
        else:
            media_kind = "video"
    return VideoAsset(
        path=path,
        duration_ms=int(payload.get("duration_ms", 0)),
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        fps=float(payload.get("fps", 30.0)),
        audio_sample_rate=int(payload.get("audio_sample_rate", 22050)),
        rotation=int(payload.get("rotation", 0)),
        is_still_image=bool(still_image_value),
        media_kind=media_kind,
    )


def project_from_dict(data: dict[str, Any]) -> Project:
    scoring_data = data.get("scoring", {})
    overlay_data = data.get("overlay", {})
    legacy_review_boxes_lock_to_stack = bool(overlay_data.get("review_boxes_lock_to_stack", False))
    merge_data = data.get("merge", {})
    export_data = data.get("export", {})
    ui_data = data.get("ui_state", {})
    analysis_data = data.get("analysis", {})
    secondary_video = (
        None
        if data.get("secondary_video") is None
        else _video_from_dict(data.get("secondary_video"))
    )
    raw_merge_sources = data.get("merge_sources", [])
    merge_sources = [_merge_source_from_dict(item) for item in raw_merge_sources]
    merge_pip_value = merge_data.get("pip_size", PipSize.MEDIUM.value)
    if isinstance(merge_pip_value, PipSize):
        merge_pip_enum = merge_pip_value
    else:
        merge_pip_enum = PipSize(str(merge_pip_value))
    merge_pip_percent_default = {
        PipSize.SMALL: 25,
        PipSize.MEDIUM: 35,
        PipSize.LARGE: 50,
    }[merge_pip_enum]
    if not merge_sources and secondary_video is not None:
        merge_sources = [
            MergeSource(
                asset=secondary_video,
                pip_size_percent=int(merge_data.get("pip_size_percent", merge_pip_percent_default)),
                pip_x=float(merge_data.get("pip_x", 1.0)),
                pip_y=float(merge_data.get("pip_y", 1.0)),
                opacity=1.0,
                sync_offset_ms=int(analysis_data.get("sync_offset_ms", 0)),
            )
        ]
    elif len(merge_sources) == 1:
        has_explicit_source_sync = any(
            isinstance(item, dict) and item.get("sync_offset_ms") not in {None, ""}
            for item in raw_merge_sources
        )
        if not has_explicit_source_sync:
            merge_sources[0].sync_offset_ms = int(analysis_data.get("sync_offset_ms", 0))

    project = Project(
        id=str(data.get("id", uuid4().hex)),
        name=str(data.get("name", "Untitled Project")),
        description=str(data.get("description", "")),
        output_root=str(data.get("output_root", "") or ""),
        created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
        primary_video=_video_from_dict(data.get("primary_video")),
        primary_trim_derivative=_merge_source_trim_derivative_from_dict(
            data.get("primary_trim_derivative"),
            asset=_video_from_dict(data.get("primary_video")),
        ),
        secondary_video=secondary_video,
        merge_sources=merge_sources,
        analysis=_analysis_state_from_dict(analysis_data),
        scoring=ScoringState(
            enabled=bool(scoring_data.get("enabled", True)),
            ruleset=str(scoring_data.get("ruleset", "uspsa_minor")),
            match_type=str(scoring_data.get("match_type", "")),
            stage_number=(
                None
                if scoring_data.get("stage_number") in {None, ""}
                else int(scoring_data.get("stage_number"))
            ),
            competitor_name=str(scoring_data.get("competitor_name", "")),
            competitor_place=(
                None
                if scoring_data.get("competitor_place") in {None, ""}
                else int(scoring_data.get("competitor_place"))
            ),
            classification=str(scoring_data.get("classification", "")),
            division=str(scoring_data.get("division", "")),
            practiscore_source_path=str(scoring_data.get("practiscore_source_path", "")),
            practiscore_source_name=str(scoring_data.get("practiscore_source_name", "")),
            penalties=float(scoring_data.get("penalties", 0)),
            point_map={
                str(key): float(value)
                for key, value in scoring_data.get("point_map", ScoringState().point_map).items()
            },
            penalty_counts={
                str(key): float(value)
                for key, value in scoring_data.get("penalty_counts", {}).items()
            },
            hit_factor=(
                None
                if scoring_data.get("hit_factor") is None
                else float(scoring_data["hit_factor"])
            ),
            imported_stage=_imported_stage_from_dict(scoring_data.get("imported_stage")),
            comparison_competitors=[
                {str(key): value for key, value in item.items()}
                for item in scoring_data.get("comparison_competitors", [])
                if isinstance(item, dict)
            ],
        ),
        popups=[
            _popup_bubble_from_dict(item)
            for item in data.get("popups", [])
            if isinstance(item, dict)
        ],
        popup_template=_popup_template_from_dict(data.get("popup_template")),
        overlay=OverlaySettings(
            position=OverlayPosition(overlay_data.get("position", OverlayPosition.BOTTOM.value)),
            badge_size=BadgeSize(overlay_data.get("badge_size", BadgeSize.M.value)),
            style_type=str(overlay_data.get("style_type", "square")),
            spacing=int(overlay_data.get("spacing", 8)),
            margin=int(overlay_data.get("margin", 8)),
            max_visible_shots=int(overlay_data.get("max_visible_shots", 4)),
            shot_quadrant=str(overlay_data.get("shot_quadrant", "bottom_left")),
            shot_direction=str(overlay_data.get("shot_direction", "right")),
            custom_x=(
                None
                if overlay_data.get("custom_x") in {None, ""}
                else float(overlay_data["custom_x"])
            ),
            custom_y=(
                None
                if overlay_data.get("custom_y") in {None, ""}
                else float(overlay_data["custom_y"])
            ),
            timer_x=(
                None
                if overlay_data.get("timer_x") in {None, ""}
                else float(overlay_data["timer_x"])
            ),
            timer_y=(
                None
                if overlay_data.get("timer_y") in {None, ""}
                else float(overlay_data["timer_y"])
            ),
            draw_x=(
                None if overlay_data.get("draw_x") in {None, ""} else float(overlay_data["draw_x"])
            ),
            draw_y=(
                None if overlay_data.get("draw_y") in {None, ""} else float(overlay_data["draw_y"])
            ),
            score_x=(
                None
                if overlay_data.get("score_x") in {None, ""}
                else float(overlay_data["score_x"])
            ),
            score_y=(
                None
                if overlay_data.get("score_y") in {None, ""}
                else float(overlay_data["score_y"])
            ),
            bubble_width=int(overlay_data.get("bubble_width", 0)),
            bubble_height=int(overlay_data.get("bubble_height", 0)),
            font_family=str(overlay_data.get("font_family", default_overlay_font_family())),
            font_size=int(overlay_data.get("font_size", 14)),
            font_bold=bool(overlay_data.get("font_bold", True)),
            font_italic=bool(overlay_data.get("font_italic", False)),
            show_timer=bool(overlay_data.get("show_timer", True)),
            show_draw=bool(overlay_data.get("show_draw", True)),
            show_shots=bool(overlay_data.get("show_shots", True)),
            show_shot_scores=bool(overlay_data.get("show_shot_scores", True)),
            show_score=bool(overlay_data.get("show_score", True)),
            timer_lock_to_stack=bool(
                overlay_data.get(
                    "timer_lock_to_stack",
                    overlay_data.get("timer_x") in {None, ""}
                    and overlay_data.get("timer_y") in {None, ""},
                )
            ),
            draw_lock_to_stack=bool(
                overlay_data.get(
                    "draw_lock_to_stack",
                    overlay_data.get("draw_x") in {None, ""}
                    and overlay_data.get("draw_y") in {None, ""},
                )
            ),
            score_lock_to_stack=bool(
                overlay_data.get(
                    "score_lock_to_stack",
                    overlay_data.get("score_x") in {None, ""}
                    and overlay_data.get("score_y") in {None, ""},
                )
            ),
            custom_box_enabled=bool(overlay_data.get("custom_box_enabled", False)),
            custom_box_mode=(
                str(overlay_data.get("custom_box_mode", "manual"))
                if str(overlay_data.get("custom_box_mode", "manual"))
                in {"manual", "imported_summary"}
                else "manual"
            ),
            custom_box_text=str(overlay_data.get("custom_box_text", "")),
            custom_box_quadrant=str(overlay_data.get("custom_box_quadrant", "top_right")),
            custom_box_x=(
                None
                if overlay_data.get("custom_box_x") in {None, ""}
                else float(overlay_data["custom_box_x"])
            ),
            custom_box_y=(
                None
                if overlay_data.get("custom_box_y") in {None, ""}
                else float(overlay_data["custom_box_y"])
            ),
            custom_box_background_color=str(
                overlay_data.get("custom_box_background_color", "#000000")
            ),
            custom_box_text_color=str(overlay_data.get("custom_box_text_color", "#ffffff")),
            custom_box_opacity=float(overlay_data.get("custom_box_opacity", 0.9)),
            custom_box_width=int(overlay_data.get("custom_box_width", 0)),
            custom_box_height=int(overlay_data.get("custom_box_height", 0)),
            text_boxes=[
                _overlay_text_box_from_dict(
                    item, legacy_lock_to_stack=legacy_review_boxes_lock_to_stack
                )
                for item in overlay_data.get("text_boxes", [])
                if isinstance(item, dict)
            ],
            timer_badge=_badge_style_from_dict(overlay_data.get("timer_badge")),
            shot_badge=_badge_style_from_dict(overlay_data.get("shot_badge")),
            current_shot_badge=_badge_style_from_dict(overlay_data.get("current_shot_badge")),
            hit_factor_badge=_badge_style_from_dict(overlay_data.get("hit_factor_badge")),
            scoring_colors={
                **OverlaySettings().scoring_colors,
                **_normalize_scoring_color_map(overlay_data.get("scoring_colors", {})),
            },
        ),
        merge=MergeSettings(
            enabled=bool(merge_data.get("enabled", True)),
            layout=MergeLayout(merge_data.get("layout", MergeLayout.SIDE_BY_SIDE.value)),
            pip_size=merge_pip_enum,
            pip_size_percent=int(merge_data.get("pip_size_percent", merge_pip_percent_default)),
            pip_x=float(merge_data.get("pip_x", 1.0)),
            pip_y=float(merge_data.get("pip_y", 1.0)),
            primary_is_left_or_top=bool(merge_data.get("primary_is_left_or_top", True)),
        ),
        export=ExportSettings(
            quality=ExportQuality(export_data.get("quality", ExportQuality.HIGH.value)),
            aspect_ratio=AspectRatio(export_data.get("aspect_ratio", AspectRatio.ORIGINAL.value)),
            crop_center_x=float(export_data.get("crop_center_x", 0.5)),
            crop_center_y=float(export_data.get("crop_center_y", 0.5)),
            output_path=export_data.get("output_path"),
            preset=ExportPreset(export_data.get("preset", ExportPreset.SOURCE.value)),
            target_width=(
                None
                if export_data.get("target_width") in {None, ""}
                else int(export_data["target_width"])
            ),
            target_height=(
                None
                if export_data.get("target_height") in {None, ""}
                else int(export_data["target_height"])
            ),
            frame_rate=ExportFrameRate(export_data.get("frame_rate", ExportFrameRate.SOURCE.value)),
            video_codec=ExportVideoCodec(
                export_data.get("video_codec", ExportVideoCodec.H264.value)
            ),
            video_bitrate_mbps=float(export_data.get("video_bitrate_mbps", 15.0)),
            audio_codec=ExportAudioCodec(
                export_data.get("audio_codec", ExportAudioCodec.AAC.value)
            ),
            audio_sample_rate=int(export_data.get("audio_sample_rate", 48000)),
            audio_bitrate_kbps=int(export_data.get("audio_bitrate_kbps", 320)),
            color_space=ExportColorSpace(
                export_data.get("color_space", ExportColorSpace.BT709_SDR.value)
            ),
            two_pass=bool(export_data.get("two_pass", False)),
            ffmpeg_preset=str(export_data.get("ffmpeg_preset", "medium")),
            last_log=str(export_data.get("last_log", "")),
            last_error=(
                None
                if export_data.get("last_error") in {None, ""}
                else str(export_data["last_error"])
            ),
        ),
        ui_state=UIState(
            selected_shot_id=ui_data.get("selected_shot_id"),
            timeline_zoom=float(ui_data.get("timeline_zoom", 1.0)),
            timeline_offset_ms=int(ui_data.get("timeline_offset_ms", 0)),
            active_tool=_normalize_ui_state_active_tool(ui_data.get("active_tool")),
            waveform_mode=_normalize_ui_state_waveform_mode(ui_data.get("waveform_mode")),
            waveform_expanded=bool(ui_data.get("waveform_expanded", False)),
            timing_expanded=bool(ui_data.get("timing_expanded", False)),
            timing_enabled=bool(ui_data.get("timing_enabled", True)),
            review_show_markers=bool(ui_data.get("review_show_markers", True)),
            review_show_pip=bool(ui_data.get("review_show_pip", True)),
            metrics_expanded=bool(ui_data.get("metrics_expanded", False)),
            markers_expanded=bool(ui_data.get("markers_expanded", False)),
            scoring_expanded=bool(ui_data.get("scoring_expanded", False)),
            layout_locked=bool(ui_data.get("layout_locked", True)),
            rail_width=int(ui_data.get("rail_width", 84)),
            inspector_width=int(ui_data.get("inspector_width", 440)),
            waveform_height=int(ui_data.get("waveform_height", 206)),
            scoring_shot_expansion=_ui_state_bool_map(ui_data.get("scoring_shot_expansion")),
            scoring_edit_shot_ids=_ui_state_string_list(
                ui_data.get("scoring_edit_shot_ids")
                or [
                    key
                    for key, value in _ui_state_bool_map(
                        ui_data.get("scoring_shot_expansion")
                    ).items()
                    if value
                ]
            ),
            waveform_shot_amplitudes=_ui_state_float_map(
                ui_data.get("waveform_shot_amplitudes"),
                minimum=0.25,
            ),
            timing_edit_shot_ids=_ui_state_string_list(ui_data.get("timing_edit_shot_ids")),
            timing_column_widths=_ui_state_float_map(
                ui_data.get("timing_column_widths"),
                minimum=72,
            ),
            review_text_box_expansion=_ui_state_bool_map(ui_data.get("review_text_box_expansion")),
            popup_bubble_expansion=_ui_state_bool_map(ui_data.get("popup_bubble_expansion")),
            popup_authoring_collapsed=bool(ui_data.get("popup_authoring_collapsed", True)),
            merge_source_expansion=_ui_state_bool_map(ui_data.get("merge_source_expansion")),
            shotml_section_expansion=_ui_state_bool_map(ui_data.get("shotml_section_expansion")),
        ),
        schema_version=int(data.get("schema_version", 1)),
    )
    ensure_merge_source_composition_truth(
        project,
        raw_merge_sources=[item for item in raw_merge_sources if isinstance(item, dict)],
        secondary_video_is_explicitly_set=(
            data.get("secondary_video") is not None
            and isinstance(data.get("secondary_video"), dict)
            and bool(data["secondary_video"].get("path"))
        ),
    )
    _finalize_primary_trim_derivative(project.primary_video, project.primary_trim_derivative)
    project.analysis.detection_threshold = project.analysis.shotml_settings.detection_threshold
    if project.merge_sources:
        project.secondary_video = project.merge_sources[0].asset
        if len(project.merge_sources) == 1:
            project.analysis.sync_offset_ms = int(project.merge_sources[0].sync_offset_ms)
    if not project.overlay.text_boxes:
        legacy_box = legacy_custom_box_as_text_box(
            project.overlay,
            legacy_lock_to_stack=legacy_review_boxes_lock_to_stack,
        )
        if legacy_box is not None:
            project.overlay.text_boxes = [legacy_box]
    for text_box in project.overlay.text_boxes:
        if text_box.x is not None or text_box.y is not None:
            text_box.quadrant = "custom"
    from splitshot.scoring.logic import ensure_default_shot_scores

    ensure_default_shot_scores(project)
    sync_overlay_legacy_custom_box_fields(project.overlay)
    project.sort_shots()

    schema_version = int(data.get("schema_version", 1))
    if schema_version >= 2 or "stages" in data:
        raw_stages = data.get("stages", [])
        if isinstance(raw_stages, list):
            project.stages = [
                _stage_from_dict(item) for item in raw_stages if isinstance(item, dict)
            ]
        project.active_stage_id = str(data.get("active_stage_id", ""))
        raw_queue = data.get("queue", [])
        if isinstance(raw_queue, list):
            project.queue = [
                _queue_entry_from_dict(item) for item in raw_queue if isinstance(item, dict)
            ]
        project.last_combined_output_path = str(data.get("last_combined_output_path", "") or "")
        project.combined_export_settings = _combined_export_settings_from_dict(
            data.get("combined_export_settings")
        )
        project.queue_settings = _queue_settings_from_dict(data.get("queue_settings"))
        project.intro_clip = _intro_outro_clip_from_dict(
            data.get("intro_clip"), project.queue_settings.intro_path
        )
        project.outro_clip = _intro_outro_clip_from_dict(
            data.get("outro_clip"), project.queue_settings.outro_path
        )
        project.practiscore_source_file = str(data.get("practiscore_source_file", ""))
        raw_excluded_stage_numbers = data.get("excluded_imported_stage_numbers", [])
        if isinstance(raw_excluded_stage_numbers, list):
            project.excluded_imported_stage_numbers = sorted(
                {
                    int(stage_number)
                    for stage_number in raw_excluded_stage_numbers
                    if str(stage_number).strip().isdigit() and int(stage_number) > 0
                }
            )
    else:
        from copy import deepcopy

        imported_stage_number = project.scoring.stage_number
        imported_stage_name = ""
        if project.scoring.imported_stage:
            imported_stage_number = project.scoring.imported_stage.stage_number
            imported_stage_name = project.scoring.imported_stage.stage_name
        legacy_stage = ProjectStage(
            label=imported_stage_name if imported_stage_name else "Stage 1",
            order_index=project.scoring.stage_number if project.scoring.stage_number else 1,
            primary_media=project.primary_video,
            primary_trim_derivative=deepcopy(project.primary_trim_derivative),
            added_media=list(project.merge_sources),
            analysis=deepcopy(project.analysis),
            scoring=deepcopy(project.scoring),
            overlay=deepcopy(project.overlay),
            popups=list(project.popups),
            popup_template=deepcopy(project.popup_template),
            merge=deepcopy(project.merge),
            export=deepcopy(project.export),
            imported_stage_number=imported_stage_number,
            imported_stage_name=imported_stage_name,
        )
        project.stages = [legacy_stage]
        project.active_stage_id = legacy_stage.id
        project.schema_version = 2

    if not project.active_stage_id and project.stages:
        project.active_stage_id = project.stages[0].id

    for stage in project.stages:
        _finalize_primary_trim_derivative(stage.primary_media, stage.primary_trim_derivative)

    return project
