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


class AspectRatio(StrEnum):
    ORIGINAL = "original"
    LANDSCAPE = "16:9"
    PORTRAIT = "9:16"
    SQUARE = "1:1"
    PORTRAIT_45 = "4:5"


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

    @property
    def path_obj(self) -> Path:
        return Path(self.path)

    @property
    def size(self) -> tuple[int, int]:
        return self.width, self.height


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
class AnalysisState:
    beep_time_ms_primary: int | None = None
    beep_time_ms_secondary: int | None = None
    sync_offset_ms: int = 0
    detection_threshold: float = 0.5
    waveform_primary: list[float] = field(default_factory=list)
    waveform_secondary: list[float] = field(default_factory=list)
    shots: list[ShotEvent] = field(default_factory=list)


@dataclass(slots=True)
class ScoringState:
    enabled: bool = False
    ruleset: str = "uspsa_minor"
    penalties: int = 0
    point_map: dict[str, int] = field(
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
    hit_factor: float | None = None


@dataclass(slots=True)
class OverlaySettings:
    position: OverlayPosition = OverlayPosition.BOTTOM
    badge_size: BadgeSize = BadgeSize.M
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
        }
    )


@dataclass(slots=True)
class MergeSettings:
    enabled: bool = False
    layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    pip_size: PipSize = PipSize.MEDIUM
    primary_is_left_or_top: bool = True


@dataclass(slots=True)
class ExportSettings:
    quality: ExportQuality = ExportQuality.HIGH
    aspect_ratio: AspectRatio = AspectRatio.ORIGINAL
    crop_center_x: float = 0.5
    crop_center_y: float = 0.5
    output_path: str | None = None


@dataclass(slots=True)
class UIState:
    selected_shot_id: str | None = None
    timeline_zoom: float = 1.0
    timeline_offset_ms: int = 0


@dataclass(slots=True)
class Project:
    id: str = field(default_factory=lambda: uuid4().hex)
    name: str = "Untitled Project"
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    primary_video: VideoAsset = field(default_factory=VideoAsset)
    secondary_video: VideoAsset | None = None
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
    return VideoAsset(
        path=str(payload.get("path", "")),
        duration_ms=int(payload.get("duration_ms", 0)),
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        fps=float(payload.get("fps", 30.0)),
        audio_sample_rate=int(payload.get("audio_sample_rate", 22050)),
        rotation=int(payload.get("rotation", 0)),
    )


def project_from_dict(data: dict[str, Any]) -> Project:
    scoring_data = data.get("scoring", {})
    overlay_data = data.get("overlay", {})
    merge_data = data.get("merge", {})
    export_data = data.get("export", {})
    ui_data = data.get("ui_state", {})
    analysis_data = data.get("analysis", {})

    project = Project(
        id=str(data.get("id", uuid4().hex)),
        name=str(data.get("name", "Untitled Project")),
        created_at=datetime.fromisoformat(data.get("created_at", datetime.now(UTC).isoformat())),
        updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(UTC).isoformat())),
        primary_video=_video_from_dict(data.get("primary_video")),
        secondary_video=(
            None if data.get("secondary_video") is None else _video_from_dict(data.get("secondary_video"))
        ),
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
        ),
        scoring=ScoringState(
            enabled=bool(scoring_data.get("enabled", False)),
            ruleset=str(scoring_data.get("ruleset", "uspsa_minor")),
            penalties=int(scoring_data.get("penalties", 0)),
            point_map={
                str(key): int(value)
                for key, value in scoring_data.get("point_map", ScoringState().point_map).items()
            },
            hit_factor=(
                None if scoring_data.get("hit_factor") is None else float(scoring_data["hit_factor"])
            ),
        ),
        overlay=OverlaySettings(
            position=OverlayPosition(overlay_data.get("position", OverlayPosition.BOTTOM.value)),
            badge_size=BadgeSize(overlay_data.get("badge_size", BadgeSize.M.value)),
            timer_badge=_badge_style_from_dict(overlay_data.get("timer_badge")),
            shot_badge=_badge_style_from_dict(overlay_data.get("shot_badge")),
            current_shot_badge=_badge_style_from_dict(overlay_data.get("current_shot_badge")),
            hit_factor_badge=_badge_style_from_dict(overlay_data.get("hit_factor_badge")),
            scoring_colors={
                str(key): str(value)
                for key, value in overlay_data.get("scoring_colors", OverlaySettings().scoring_colors).items()
            },
        ),
        merge=MergeSettings(
            enabled=bool(merge_data.get("enabled", False)),
            layout=MergeLayout(merge_data.get("layout", MergeLayout.SIDE_BY_SIDE.value)),
            pip_size=PipSize(merge_data.get("pip_size", PipSize.MEDIUM.value)),
            primary_is_left_or_top=bool(merge_data.get("primary_is_left_or_top", True)),
        ),
        export=ExportSettings(
            quality=ExportQuality(export_data.get("quality", ExportQuality.HIGH.value)),
            aspect_ratio=AspectRatio(export_data.get("aspect_ratio", AspectRatio.ORIGINAL.value)),
            crop_center_x=float(export_data.get("crop_center_x", 0.5)),
            crop_center_y=float(export_data.get("crop_center_y", 0.5)),
            output_path=export_data.get("output_path"),
        ),
        ui_state=UIState(
            selected_shot_id=ui_data.get("selected_shot_id"),
            timeline_zoom=float(ui_data.get("timeline_zoom", 1.0)),
            timeline_offset_ms=int(ui_data.get("timeline_offset_ms", 0)),
        ),
        schema_version=int(data.get("schema_version", 1)),
    )
    project.sort_shots()
    return project
