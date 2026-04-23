from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime, UTC
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4


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


class MergeLayout(StrEnum):
    SIDE_BY_SIDE = "side_by_side"
    ABOVE_BELOW = "above_below"
    PIP = "pip"


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


class AspectRatio(StrEnum):
    ORIGINAL = "original"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    PORTRAIT_45 = "4:5"


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

    @property
    def path_obj(self) -> Path:
        return Path(self.path)

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


@dataclass(slots=True)
class MergeSource:
    id: str = field(default_factory=lambda: uuid4().hex)
    asset: VideoAsset = field(default_factory=VideoAsset)
    pip_size_percent: int | None = None
    pip_x: float = 1.0
    pip_y: float = 1.0
    opacity: float = 1.0
    sync_offset_ms: int = 0


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
class AnalysisState:
    beep_time_ms_primary: int | None = None
    beep_time_ms_secondary: int | None = None
    sync_offset_ms: int = 0
    detection_threshold: float = 0.35
    shotml_settings: ShotMLSettings = field(default_factory=ShotMLSettings)
    timing_change_proposals: list[TimingChangeProposal] = field(default_factory=list)
    last_shotml_run_summary: dict[str, Any] = field(default_factory=dict)
    waveform_primary: list[float] = field(default_factory=list)
    waveform_secondary: list[float] = field(default_factory=list)
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
    enabled: bool = False
    ruleset: str = "uspsa_minor"
    match_type: str = ""
    stage_number: int | None = None
    competitor_name: str = ""
    competitor_place: int | None = None
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
    font_family: str = "Helvetica Neue"
    font_size: int = 14
    font_bold: bool = True
    font_italic: bool = False
    show_timer: bool = True
    show_draw: bool = True
    show_shots: bool = True
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
    text_boxes: list["OverlayTextBox"] = field(default_factory=list)
    timer_badge: BadgeStyle = field(default_factory=BadgeStyle)
    shot_badge: BadgeStyle = field(
        default_factory=lambda: BadgeStyle(background_color="#1D4ED8")
    )
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
    enabled: bool = False
    layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    pip_size: PipSize = PipSize.MEDIUM
    pip_size_percent: int = 35
    pip_x: float = 1.0
    pip_y: float = 1.0
    primary_is_left_or_top: bool = True


@dataclass(slots=True)
class OverlayTextBox:
    id: str = field(default_factory=lambda: uuid4().hex)
    enabled: bool = False
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
    follow_motion: bool = False
    motion_path: list[PopupMotionPoint] = field(default_factory=list)
    background_color: str = "#000000"
    text_color: str = "#ffffff"
    opacity: float = 0.9
    width: int = 0
    height: int = 0


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
    metrics_expanded: bool = False
    layout_locked: bool = True
    rail_width: int = 64
    inspector_width: int = 440
    waveform_height: int = 206
    scoring_shot_expansion: dict[str, bool] = field(default_factory=dict)
    waveform_shot_amplitudes: dict[str, float] = field(default_factory=dict)
    timing_edit_shot_ids: list[str] = field(default_factory=list)
    timing_column_widths: dict[str, float] = field(default_factory=dict)
    review_text_box_expansion: dict[str, bool] = field(default_factory=dict)
    popup_bubble_expansion: dict[str, bool] = field(default_factory=dict)
    popup_authoring_collapsed: bool = False
    merge_source_expansion: dict[str, bool] = field(default_factory=dict)
    shotml_section_expansion: dict[str, bool] = field(default_factory=dict)


@dataclass(slots=True)
class Project:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Untitled Project"
    description: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    primary_video: VideoAsset = field(default_factory=VideoAsset)
    secondary_video: VideoAsset | None = None
    merge_sources: list[MergeSource] = field(default_factory=list)
    analysis: AnalysisState = field(default_factory=AnalysisState)
    scoring: ScoringState = field(default_factory=ScoringState)
    overlay: OverlaySettings = field(default_factory=OverlaySettings)
    popups: list[PopupBubble] = field(default_factory=list)
    merge: MergeSettings = field(default_factory=MergeSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    ui_state: UIState = field(default_factory=UIState)
    schema_version: int = 1

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


def project_to_dict(project: Project) -> dict[str, Any]:
    data = _serialize(project)
    overlay = data.get("overlay")
    if isinstance(overlay, dict):
        overlay["scoring_colors"] = _normalize_scoring_color_map(overlay.get("scoring_colors", {}))
        overlay.pop("review_boxes_lock_to_stack", None)
    return data


def _parse_enum(enum_type: type[StrEnum], value: str | None, default: StrEnum) -> StrEnum:
    if value is None:
        return default
    return enum_type(value)


def _badge_style_from_dict(data: dict[str, Any] | None) -> BadgeStyle:
    payload = data or {}
    return BadgeStyle(
        background_color=payload.get("background_color", BadgeStyle().background_color),
        text_color=payload.get("text_color", BadgeStyle().text_color),
        opacity=float(payload.get("opacity", BadgeStyle().opacity)),
    )


def _normalize_scoring_color_map(data: dict[str, Any] | None) -> dict[str, str]:
    normalized: dict[str, str] = {}
    for key, value in (data or {}).items():
        normalized_key = str(key).strip()
        if not normalized_key or "|" in normalized_key:
            continue
        normalized[normalized_key] = str(value)
    return normalized


_TEXT_BOX_SOURCES = {"manual", "imported_summary"}
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
_POPUP_MOTION_EASINGS = {"linear", "hold", "ease_in", "ease_out", "ease_in_out"}

_UI_STATE_ACTIVE_TOOLS = {
    "project",
    "scoring",
    "shotml",
    "timing",
    "merge",
    "overlay",
    "review",
    "popup",
    "export",
    "metrics",
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
        offset_ms = max(0, int(round(float(data.get("offset_ms", data.get("time_ms", 0)) or 0))))
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


def _normalize_ui_state_active_tool(value: Any) -> str:
    normalized = str(value or "project")
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


def _overlay_text_box_from_dict(data: dict[str, Any], legacy_lock_to_stack: bool = False) -> OverlayTextBox:
    box = OverlayTextBox(
        id=str(data.get("id") or uuid4().hex),
        enabled=bool(data.get("enabled", False)),
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
    )
    if box.x is not None or box.y is not None:
        box.quadrant = "custom"
    return box


def _popup_bubble_from_dict(data: dict[str, Any]) -> PopupBubble:
    shot_id = None if data.get("shot_id") in {None, ""} else str(data["shot_id"])
    x_value = None if data.get("x") in {None, ""} else float(data["x"])
    y_value = None if data.get("y") in {None, ""} else float(data["y"])
    motion_path = _normalize_popup_motion_path(data.get("motion_path"))
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
        follow_motion=bool(data.get("follow_motion", bool(motion_path))),
        motion_path=motion_path,
        background_color=str(data.get("background_color", "#000000")),
        text_color=str(data.get("text_color", "#ffffff")),
        opacity=max(0.0, min(1.0, float(data.get("opacity", 0.9)))),
        width=max(0, int(data.get("width", 0) or 0)),
        height=max(0, int(data.get("height", 0) or 0)),
    )


def legacy_custom_box_as_text_box(overlay: OverlaySettings, legacy_lock_to_stack: bool = False) -> OverlayTextBox | None:
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
            str(key): float(value)
            for key, value in data.get("penalty_counts", {}).items()
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
        competitor_place=(
            None
            if competitor_place in {None, ""}
            else int(competitor_place)
        ),
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
            str(key): float(value)
            for key, value in data.get("score_counts", {}).items()
        },
    )


def _path_looks_like_still_image(path: str) -> bool:
    return Path(path).suffix.lower() in _STILL_IMAGE_SUFFIXES


def _merge_source_from_dict(data: dict[str, Any]) -> MergeSource:
    payload = data or {}
    asset_data = payload.get("asset", payload)
    return MergeSource(
        id=str(payload.get("id", uuid4().hex)),
        asset=_video_from_dict(asset_data),
        pip_size_percent=(
            None
            if payload.get("pip_size_percent") in {None, ""}
            else int(payload.get("pip_size_percent"))
        ),
        pip_x=float(payload.get("pip_x", 1.0)),
        pip_y=float(payload.get("pip_y", 1.0)),
        opacity=max(0.0, min(1.0, float(payload.get("opacity", 1.0)))),
        sync_offset_ms=int(payload.get("sync_offset_ms", 0)),
    )


def _timing_event_from_dict(data: dict[str, Any]) -> TimingEvent:
    return TimingEvent(
        id=str(data.get("id", uuid4().hex)),
        kind=str(data.get("kind", "reload")),
        label=str(data.get("label", data.get("kind", "Reload"))),
        after_shot_id=None if data.get("after_shot_id") in {None, ""} else str(data["after_shot_id"]),
        before_shot_id=None if data.get("before_shot_id") in {None, ""} else str(data["before_shot_id"]),
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


def _shotml_settings_from_dict(data: dict[str, Any] | None, *, detection_threshold: float | None = None) -> ShotMLSettings:
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
        source_time_ms=None if data.get("source_time_ms") in {None, ""} else int(data["source_time_ms"]),
        target_time_ms=None if data.get("target_time_ms") in {None, ""} else int(data["target_time_ms"]),
        alternate_shot_id=None if data.get("alternate_shot_id") in {None, ""} else str(data["alternate_shot_id"]),
        alternate_time_ms=None if data.get("alternate_time_ms") in {None, ""} else int(data["alternate_time_ms"]),
        confidence=None if data.get("confidence") in {None, ""} else float(data["confidence"]),
        support_confidence=None if data.get("support_confidence") in {None, ""} else float(data["support_confidence"]),
        message=str(data.get("message", "")),
        evidence=evidence if isinstance(evidence, dict) else {},
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
        user_added=bool(data.get("user_added", source == ShotSource.MANUAL and shotml_time_ms in {None, ""})),
    )


def _video_from_dict(data: dict[str, Any] | None) -> VideoAsset:
    payload = data or {}
    path = str(payload.get("path", ""))
    still_image = payload.get("is_still_image")
    if still_image is None:
        still_image = _path_looks_like_still_image(path)
    else:
        still_image = bool(still_image) or _path_looks_like_still_image(path)
    return VideoAsset(
        path=path,
        duration_ms=int(payload.get("duration_ms", 0)),
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        fps=float(payload.get("fps", 30.0)),
        audio_sample_rate=int(payload.get("audio_sample_rate", 22050)),
        rotation=int(payload.get("rotation", 0)),
        is_still_image=bool(still_image),
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
        None if data.get("secondary_video") is None else _video_from_dict(data.get("secondary_video"))
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
        created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
        primary_video=_video_from_dict(data.get("primary_video")),
        secondary_video=secondary_video,
        merge_sources=merge_sources,
        analysis=AnalysisState(
            beep_time_ms_primary=analysis_data.get("beep_time_ms_primary"),
            beep_time_ms_secondary=analysis_data.get("beep_time_ms_secondary"),
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
            waveform_primary=[
                float(item) for item in analysis_data.get("waveform_primary", [])
            ],
            waveform_secondary=[
                float(item) for item in analysis_data.get("waveform_secondary", [])
            ],
            shots=[_shot_from_dict(item) for item in analysis_data.get("shots", [])],
            events=[_timing_event_from_dict(item) for item in analysis_data.get("events", [])],
            detection_review_suggestions=[
                item
                for item in analysis_data.get("detection_review_suggestions", [])
                if isinstance(item, dict)
            ],
        ),
        scoring=ScoringState(
            enabled=bool(scoring_data.get("enabled", False)),
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
                None if scoring_data.get("hit_factor") is None else float(scoring_data["hit_factor"])
            ),
            imported_stage=_imported_stage_from_dict(scoring_data.get("imported_stage")),
        ),
        popups=[
            _popup_bubble_from_dict(item)
            for item in data.get("popups", [])
            if isinstance(item, dict)
        ],
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
                None if overlay_data.get("custom_x") in {None, ""} else float(overlay_data["custom_x"])
            ),
            custom_y=(
                None if overlay_data.get("custom_y") in {None, ""} else float(overlay_data["custom_y"])
            ),
            timer_x=(
                None if overlay_data.get("timer_x") in {None, ""} else float(overlay_data["timer_x"])
            ),
            timer_y=(
                None if overlay_data.get("timer_y") in {None, ""} else float(overlay_data["timer_y"])
            ),
            draw_x=(
                None if overlay_data.get("draw_x") in {None, ""} else float(overlay_data["draw_x"])
            ),
            draw_y=(
                None if overlay_data.get("draw_y") in {None, ""} else float(overlay_data["draw_y"])
            ),
            score_x=(
                None if overlay_data.get("score_x") in {None, ""} else float(overlay_data["score_x"])
            ),
            score_y=(
                None if overlay_data.get("score_y") in {None, ""} else float(overlay_data["score_y"])
            ),
            bubble_width=int(overlay_data.get("bubble_width", 0)),
            bubble_height=int(overlay_data.get("bubble_height", 0)),
            font_family=str(overlay_data.get("font_family", "Helvetica Neue")),
            font_size=int(overlay_data.get("font_size", 14)),
            font_bold=bool(overlay_data.get("font_bold", True)),
            font_italic=bool(overlay_data.get("font_italic", False)),
            show_timer=bool(overlay_data.get("show_timer", True)),
            show_draw=bool(overlay_data.get("show_draw", True)),
            show_shots=bool(overlay_data.get("show_shots", True)),
            show_score=bool(overlay_data.get("show_score", True)),
            timer_lock_to_stack=bool(
                overlay_data.get(
                    "timer_lock_to_stack",
                    overlay_data.get("timer_x") in {None, ""} and overlay_data.get("timer_y") in {None, ""},
                )
            ),
            draw_lock_to_stack=bool(
                overlay_data.get(
                    "draw_lock_to_stack",
                    overlay_data.get("draw_x") in {None, ""} and overlay_data.get("draw_y") in {None, ""},
                )
            ),
            score_lock_to_stack=bool(
                overlay_data.get(
                    "score_lock_to_stack",
                    overlay_data.get("score_x") in {None, ""} and overlay_data.get("score_y") in {None, ""},
                )
            ),
            custom_box_enabled=bool(overlay_data.get("custom_box_enabled", False)),
            custom_box_mode=(
                str(overlay_data.get("custom_box_mode", "manual"))
                if str(overlay_data.get("custom_box_mode", "manual")) in {"manual", "imported_summary"}
                else "manual"
            ),
            custom_box_text=str(overlay_data.get("custom_box_text", "")),
            custom_box_quadrant=str(overlay_data.get("custom_box_quadrant", "top_right")),
            custom_box_x=(
                None if overlay_data.get("custom_box_x") in {None, ""} else float(overlay_data["custom_box_x"])
            ),
            custom_box_y=(
                None if overlay_data.get("custom_box_y") in {None, ""} else float(overlay_data["custom_box_y"])
            ),
            custom_box_background_color=str(overlay_data.get("custom_box_background_color", "#000000")),
            custom_box_text_color=str(overlay_data.get("custom_box_text_color", "#ffffff")),
            custom_box_opacity=float(overlay_data.get("custom_box_opacity", 0.9)),
            custom_box_width=int(overlay_data.get("custom_box_width", 0)),
            custom_box_height=int(overlay_data.get("custom_box_height", 0)),
            text_boxes=[
                _overlay_text_box_from_dict(item, legacy_lock_to_stack=legacy_review_boxes_lock_to_stack)
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
            enabled=bool(merge_data.get("enabled", False)),
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
                None if export_data.get("target_width") in {None, ""} else int(export_data["target_width"])
            ),
            target_height=(
                None if export_data.get("target_height") in {None, ""} else int(export_data["target_height"])
            ),
            frame_rate=ExportFrameRate(export_data.get("frame_rate", ExportFrameRate.SOURCE.value)),
            video_codec=ExportVideoCodec(export_data.get("video_codec", ExportVideoCodec.H264.value)),
            video_bitrate_mbps=float(export_data.get("video_bitrate_mbps", 15.0)),
            audio_codec=ExportAudioCodec(export_data.get("audio_codec", ExportAudioCodec.AAC.value)),
            audio_sample_rate=int(export_data.get("audio_sample_rate", 48000)),
            audio_bitrate_kbps=int(export_data.get("audio_bitrate_kbps", 320)),
            color_space=ExportColorSpace(export_data.get("color_space", ExportColorSpace.BT709_SDR.value)),
            two_pass=bool(export_data.get("two_pass", False)),
            ffmpeg_preset=str(export_data.get("ffmpeg_preset", "medium")),
            last_log=str(export_data.get("last_log", "")),
            last_error=(
                None if export_data.get("last_error") in {None, ""} else str(export_data["last_error"])
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
            metrics_expanded=bool(ui_data.get("metrics_expanded", False)),
            layout_locked=bool(ui_data.get("layout_locked", True)),
            rail_width=int(ui_data.get("rail_width", 64)),
            inspector_width=int(ui_data.get("inspector_width", 440)),
            waveform_height=int(ui_data.get("waveform_height", 206)),
            scoring_shot_expansion=_ui_state_bool_map(ui_data.get("scoring_shot_expansion")),
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
            popup_authoring_collapsed=bool(ui_data.get("popup_authoring_collapsed", False)),
            merge_source_expansion=_ui_state_bool_map(ui_data.get("merge_source_expansion")),
            shotml_section_expansion=_ui_state_bool_map(ui_data.get("shotml_section_expansion")),
        ),
        schema_version=int(data.get("schema_version", 1)),
    )
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
    return project
