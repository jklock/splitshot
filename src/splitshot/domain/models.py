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


@dataclass(slots=True)
class ScoreMark:
    letter: ScoreLetter = ScoreLetter.A
    x_norm: float = 0.5
    y_norm: float = 0.5
    animation_preset: str = "fade_scale"


@dataclass(slots=True)
class ShotEvent:
    id: str = field(default_factory=lambda: uuid4().hex)
    time_ms: int = 0
    source: ShotSource = ShotSource.AUTO
    confidence: float | None = None
    score: ScoreMark | None = None


@dataclass(slots=True)
class TimingEvent:
    id: str = field(default_factory=lambda: uuid4().hex)
    kind: str = "reload"
    label: str = "Reload"
    after_shot_id: str | None = None
    before_shot_id: str | None = None
    note: str = ""


@dataclass(slots=True)
class AnalysisState:
    beep_time_ms_primary: int | None = None
    beep_time_ms_secondary: int | None = None
    sync_offset_ms: int = 0
    detection_threshold: float = 0.5
    waveform_primary: list[float] = field(default_factory=list)
    waveform_secondary: list[float] = field(default_factory=list)
    shots: list[ShotEvent] = field(default_factory=list)
    events: list[TimingEvent] = field(default_factory=list)


@dataclass(slots=True)
class ScoringState:
    enabled: bool = False
    ruleset: str = "uspsa_minor"
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
    custom_box_enabled: bool = False
    custom_box_text: str = ""
    custom_box_quadrant: str = "top_right"
    custom_box_x: float | None = None
    custom_box_y: float | None = None
    custom_box_background_color: str = "#000000"
    custom_box_text_color: str = "#ffffff"
    custom_box_opacity: float = 0.9
    custom_box_width: int = 0
    custom_box_height: int = 0
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
    return _serialize(project)


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


def _score_mark_from_dict(data: dict[str, Any] | None) -> ScoreMark | None:
    if not data:
        return None
    return ScoreMark(
        letter=ScoreLetter(data.get("letter", ScoreLetter.A.value)),
        x_norm=float(data.get("x_norm", 0.5)),
        y_norm=float(data.get("y_norm", 0.5)),
        animation_preset=str(data.get("animation_preset", "fade_scale")),
    )


def _path_looks_like_still_image(path: str) -> bool:
    return Path(path).suffix.lower() in _STILL_IMAGE_SUFFIXES


def _merge_source_from_dict(data: dict[str, Any]) -> MergeSource:
    payload = data or {}
    asset_data = payload.get("asset", payload)
    return MergeSource(
        id=str(payload.get("id", uuid4().hex)),
        asset=_video_from_dict(asset_data),
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


def _shot_from_dict(data: dict[str, Any]) -> ShotEvent:
    return ShotEvent(
        id=str(data.get("id", uuid4().hex)),
        time_ms=int(data.get("time_ms", 0)),
        source=ShotSource(data.get("source", ShotSource.AUTO.value)),
        confidence=None if data.get("confidence") is None else float(data["confidence"]),
        score=_score_mark_from_dict(data.get("score")),
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
    merge_data = data.get("merge", {})
    export_data = data.get("export", {})
    ui_data = data.get("ui_state", {})
    analysis_data = data.get("analysis", {})
    secondary_video = (
        None if data.get("secondary_video") is None else _video_from_dict(data.get("secondary_video"))
    )
    merge_sources = [_merge_source_from_dict(item) for item in data.get("merge_sources", [])]
    if not merge_sources and secondary_video is not None:
        merge_sources = [MergeSource(asset=secondary_video)]
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
            detection_threshold=float(analysis_data.get("detection_threshold", 0.5)),
            waveform_primary=[
                float(item) for item in analysis_data.get("waveform_primary", [])
            ],
            waveform_secondary=[
                float(item) for item in analysis_data.get("waveform_secondary", [])
            ],
            shots=[_shot_from_dict(item) for item in analysis_data.get("shots", [])],
            events=[_timing_event_from_dict(item) for item in analysis_data.get("events", [])],
        ),
        scoring=ScoringState(
            enabled=bool(scoring_data.get("enabled", False)),
            ruleset=str(scoring_data.get("ruleset", "uspsa_minor")),
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
        ),
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
            custom_box_enabled=bool(overlay_data.get("custom_box_enabled", False)),
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
            timer_badge=_badge_style_from_dict(overlay_data.get("timer_badge")),
            shot_badge=_badge_style_from_dict(overlay_data.get("shot_badge")),
            current_shot_badge=_badge_style_from_dict(overlay_data.get("current_shot_badge")),
            hit_factor_badge=_badge_style_from_dict(overlay_data.get("hit_factor_badge")),
            scoring_colors={
                **OverlaySettings().scoring_colors,
                **{
                    str(key): str(value)
                    for key, value in overlay_data.get("scoring_colors", {}).items()
                },
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
        ),
        schema_version=int(data.get("schema_version", 1)),
    )
    if project.merge_sources:
        project.secondary_video = project.merge_sources[0].asset
    project.sort_shots()
    return project
