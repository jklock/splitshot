from __future__ import annotations

import json
import tomllib
from copy import deepcopy
from dataclasses import dataclass, field, fields
from pathlib import Path

from splitshot.domain.models import (
    BadgeSize,
    BadgeStyle,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    OverlayPosition,
    PipSize,
    PopupTemplate,
    ShotMLSettings,
    _badge_style_from_dict,
    _popup_template_from_dict,
)

APP_DIR = Path.home() / ".splitshot"
SETTINGS_PATH = APP_DIR / "settings.json"
FOLDER_SETTINGS_FILENAME = "splitshot.conf"
APPLICATION_DEFAULTS_SCHEMA_VERSION = 1

_APPLICATION_DEFAULT_KEYS = {
    "schema_version",
    "trim_defaults",
    "scoring",
    "ui_state",
    "merge",
    "compose_source_templates",
    "overlay",
    "popup_template",
    "export",
    "shotml_settings",
    "queue_settings",
    "combined_export_settings",
    "intro_clip_settings",
    "outro_clip_settings",
}


def normalize_application_project_defaults(value: object) -> dict[str, object]:
    """Migrate legacy project_defaults into the versioned application-only schema."""
    if not isinstance(value, dict):
        return {"schema_version": APPLICATION_DEFAULTS_SCHEMA_VERSION}
    normalized = {
        key: deepcopy(item) for key, item in value.items() if key in _APPLICATION_DEFAULT_KEYS
    }
    normalized["schema_version"] = APPLICATION_DEFAULTS_SCHEMA_VERSION
    return normalized


_POPUP_MOTION_MODES = {"fixed", "guided", "manual", "auto"}


def _serialize_popup_template(template: PopupTemplate) -> dict[str, object]:
    return {
        "enabled": template.enabled,
        "content_type": template.content_type,
        "text_source": template.text_source,
        "duration_ms": template.duration_ms,
        "use_shot_split_duration": template.use_shot_split_duration,
        "quadrant": template.quadrant,
        "width": template.width,
        "height": template.height,
        "motion_mode": template.motion_mode,
        "follow_motion": template.follow_motion,
        "background_color": template.background_color,
        "text_color": template.text_color,
        "opacity": template.opacity,
    }


def _float_or_default(value: object, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _normalize_popup_motion_mode(value: object, *, follow_motion: bool = False) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in _POPUP_MOTION_MODES and not (normalized == "fixed" and follow_motion):
        return normalized
    return "manual" if follow_motion else "fixed"


# (imported from splitshot.domain.models)


def _serialize_badge_style(style: BadgeStyle) -> dict[str, object]:
    return {
        "background_color": style.background_color,
        "text_color": style.text_color,
        "opacity": style.opacity,
    }


# (imported from splitshot.domain.models)


def _review_text_boxes_from_dict(data: object) -> list[dict[str, object]]:
    if not isinstance(data, list):
        return []
    boxes: list[dict[str, object]] = []
    for item in data:
        if isinstance(item, dict):
            boxes.append({str(key): value for key, value in item.items()})
    return boxes


def _settings_templates_from_dict(data: object) -> dict[str, dict[str, object]]:
    if not isinstance(data, dict):
        return {}
    templates: dict[str, dict[str, object]] = {}
    for name, payload in data.items():
        if not isinstance(payload, dict):
            continue
        template = {str(key): value for key, value in payload.items()}
        template.pop("settings_templates", None)
        template.pop("active_template_name", None)
        templates[str(name)] = template
    return templates


@dataclass(slots=True)
class AppSettings:
    detection_threshold: float = 0.35
    shotml_defaults: ShotMLSettings = field(default_factory=ShotMLSettings)
    default_match_type: str = "uspsa"
    default_stage_number: int | None = None
    default_competitor_name: str = ""
    default_competitor_place: int | None = None
    overlay_position: OverlayPosition = OverlayPosition.BOTTOM
    timer_badge: BadgeStyle = field(default_factory=BadgeStyle)
    shot_badge: BadgeStyle = field(default_factory=lambda: BadgeStyle(background_color="#1D4ED8"))
    current_shot_badge: BadgeStyle = field(
        default_factory=lambda: BadgeStyle(background_color="#DC2626")
    )
    hit_factor_badge: BadgeStyle = field(
        default_factory=lambda: BadgeStyle(background_color="#047857")
    )
    overlay_custom_box_background_color: str = "#000000"
    overlay_custom_box_text_color: str = "#ffffff"
    overlay_custom_box_opacity: float = 0.9
    merge_layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    merge_pip_x: float = 1.0
    merge_pip_y: float = 1.0
    pip_size: PipSize = PipSize.MEDIUM
    merge_source_defaults: list[dict[str, object]] = field(default_factory=list)
    export_quality: ExportQuality = ExportQuality.HIGH
    export_preset: ExportPreset = ExportPreset.SOURCE
    export_frame_rate: ExportFrameRate = ExportFrameRate.SOURCE
    export_video_codec: ExportVideoCodec = ExportVideoCodec.H264
    export_audio_codec: ExportAudioCodec = ExportAudioCodec.AAC
    export_color_space: ExportColorSpace = ExportColorSpace.BT709_SDR
    export_two_pass: bool = False
    export_ffmpeg_preset: str = "medium"
    badge_size: BadgeSize = BadgeSize.M
    default_tool: str = "project"
    reopen_last_tool: bool = True
    layout_locked: bool | None = None
    layout_rail_width: int | None = None
    layout_inspector_width: int | None = None
    layout_waveform_height: int | None = None
    marker_template: PopupTemplate = field(default_factory=PopupTemplate)
    review_text_boxes: list[dict[str, object]] = field(default_factory=list)
    project_defaults: dict[str, object] = field(
        default_factory=lambda: {"schema_version": APPLICATION_DEFAULTS_SCHEMA_VERSION}
    )
    active_template_name: str = "Default"
    settings_templates: dict[str, dict[str, object]] = field(default_factory=dict)
    recent_projects: list[str] = field(default_factory=list)

    def config_dict(self) -> dict[str, object]:
        return {
            "detection_threshold": self.detection_threshold,
            "shotml_defaults": {
                item.name: getattr(self.shotml_defaults, item.name)
                for item in fields(ShotMLSettings)
            },
            "default_match_type": self.default_match_type,
            "default_stage_number": self.default_stage_number,
            "default_competitor_name": self.default_competitor_name,
            "default_competitor_place": self.default_competitor_place,
            "overlay_position": self.overlay_position.value,
            "timer_badge": _serialize_badge_style(self.timer_badge),
            "shot_badge": _serialize_badge_style(self.shot_badge),
            "current_shot_badge": _serialize_badge_style(self.current_shot_badge),
            "hit_factor_badge": _serialize_badge_style(self.hit_factor_badge),
            "overlay_custom_box_background_color": self.overlay_custom_box_background_color,
            "overlay_custom_box_text_color": self.overlay_custom_box_text_color,
            "overlay_custom_box_opacity": self.overlay_custom_box_opacity,
            "merge_layout": self.merge_layout.value,
            "merge_pip_x": self.merge_pip_x,
            "merge_pip_y": self.merge_pip_y,
            "pip_size": self.pip_size.value,
            "merge_source_defaults": deepcopy(self.merge_source_defaults),
            "export_quality": self.export_quality.value,
            "export_preset": self.export_preset.value,
            "export_frame_rate": self.export_frame_rate.value,
            "export_video_codec": self.export_video_codec.value,
            "export_audio_codec": self.export_audio_codec.value,
            "export_color_space": self.export_color_space.value,
            "export_two_pass": self.export_two_pass,
            "export_ffmpeg_preset": self.export_ffmpeg_preset,
            "badge_size": self.badge_size.value,
            "default_tool": self.default_tool,
            "reopen_last_tool": self.reopen_last_tool,
            "layout_locked": self.layout_locked,
            "layout_rail_width": self.layout_rail_width,
            "layout_inspector_width": self.layout_inspector_width,
            "layout_waveform_height": self.layout_waveform_height,
            "marker_template": _serialize_popup_template(self.marker_template),
            "review_text_boxes": deepcopy(self.review_text_boxes),
            "project_defaults": deepcopy(self.project_defaults),
        }

    def template_snapshot(self) -> dict[str, object]:
        snapshot = self.config_dict()
        snapshot["active_template_name"] = self.active_template_name
        return snapshot

    def to_dict(self) -> dict[str, object]:
        data = self.config_dict()
        data["active_template_name"] = self.active_template_name
        templates = deepcopy(self.settings_templates)
        if not templates:
            templates[self.active_template_name] = self.template_snapshot()
        data["settings_templates"] = templates
        data["recent_projects"] = self.recent_projects
        return data

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> AppSettings:
        shotml_payload = data.get("shotml_defaults")
        defaults = ShotMLSettings()
        factory_threshold = defaults.detection_threshold
        shotml_values: dict[str, object] = {}
        if isinstance(shotml_payload, dict):
            for item in fields(ShotMLSettings):
                default_value = getattr(defaults, item.name)
                raw_value = shotml_payload.get(item.name, default_value)
                try:
                    if isinstance(default_value, bool):
                        shotml_values[item.name] = bool(raw_value)
                    elif isinstance(default_value, int) and not isinstance(default_value, bool):
                        shotml_values[item.name] = int(raw_value)
                    elif isinstance(default_value, float):
                        shotml_values[item.name] = float(raw_value)
                    else:
                        shotml_values[item.name] = str(raw_value)
                except (TypeError, ValueError):
                    shotml_values[item.name] = default_value
        shotml_defaults = ShotMLSettings(**shotml_values) if shotml_values else defaults
        # Preserve an explicit shotml_defaults threshold supplied in saved settings or templates.
        # A factory default is only used when the payload omits the threshold entirely.
        review_text_boxes = _review_text_boxes_from_dict(data.get("review_text_boxes"))
        merge_source_defaults = _review_text_boxes_from_dict(data.get("merge_source_defaults"))
        if not merge_source_defaults and isinstance(data.get("merge_source_defaults_json"), str):
            try:
                merge_source_defaults = _review_text_boxes_from_dict(
                    json.loads(str(data["merge_source_defaults_json"]))
                )
            except json.JSONDecodeError:
                merge_source_defaults = []
        project_defaults = normalize_application_project_defaults(data.get("project_defaults", {}))
        if merge_source_defaults and not project_defaults.get("compose_source_templates"):
            project_defaults["compose_source_templates"] = [
                {
                    key: item[key]
                    for key in ("angle_role", "pip_size_percent", "pip_x", "pip_y", "opacity")
                    if key in item
                }
                for item in merge_source_defaults
            ]
        settings_templates = _settings_templates_from_dict(data.get("settings_templates"))
        active_template_name = str(data.get("active_template_name", "Default") or "Default")
        layout_locked = data.get("layout_locked")
        layout_rail_width = data.get("layout_rail_width")
        layout_inspector_width = data.get("layout_inspector_width")
        layout_waveform_height = data.get("layout_waveform_height")

        def _optional_int(value: object) -> int | None:
            try:
                return None if value in {None, ""} else int(value)
            except (TypeError, ValueError):
                return None

        def _optional_bool(value: object) -> bool | None:
            if value in {None, ""}:
                return None
            if isinstance(value, str):
                return value.strip().lower() in {"1", "true", "yes", "on"}
            return bool(value)

        recent_projects = [str(item) for item in data.get("recent_projects", [])]
        settings = cls(
            detection_threshold=factory_threshold,
            shotml_defaults=shotml_defaults,
            default_match_type=str(data.get("default_match_type", "uspsa") or "uspsa")
            .strip()
            .lower(),
            default_stage_number=None,
            default_competitor_name="",
            default_competitor_place=None,
            overlay_position=OverlayPosition(
                str(data.get("overlay_position", OverlayPosition.BOTTOM.value))
            ),
            timer_badge=_badge_style_from_dict(data.get("timer_badge"), BadgeStyle()),
            shot_badge=_badge_style_from_dict(
                data.get("shot_badge"), BadgeStyle(background_color="#1D4ED8")
            ),
            current_shot_badge=_badge_style_from_dict(
                data.get("current_shot_badge"), BadgeStyle(background_color="#DC2626")
            ),
            hit_factor_badge=_badge_style_from_dict(
                data.get("hit_factor_badge"), BadgeStyle(background_color="#047857")
            ),
            overlay_custom_box_background_color=str(
                data.get("overlay_custom_box_background_color", "#000000") or "#000000"
            ),
            overlay_custom_box_text_color=str(
                data.get("overlay_custom_box_text_color", "#ffffff") or "#ffffff"
            ),
            overlay_custom_box_opacity=max(
                0.0, min(1.0, _float_or_default(data.get("overlay_custom_box_opacity"), 0.9))
            ),
            merge_layout=MergeLayout(str(data.get("merge_layout", MergeLayout.SIDE_BY_SIDE.value))),
            merge_pip_x=_float_or_default(data.get("merge_pip_x"), 1.0),
            merge_pip_y=_float_or_default(data.get("merge_pip_y"), 1.0),
            pip_size=PipSize(str(data.get("pip_size", PipSize.MEDIUM.value))),
            merge_source_defaults=[],
            export_quality=ExportQuality(str(data.get("export_quality", ExportQuality.HIGH.value))),
            export_preset=ExportPreset(str(data.get("export_preset", ExportPreset.SOURCE.value))),
            export_frame_rate=ExportFrameRate(
                str(data.get("export_frame_rate", ExportFrameRate.SOURCE.value))
            ),
            export_video_codec=ExportVideoCodec(
                str(data.get("export_video_codec", ExportVideoCodec.H264.value))
            ),
            export_audio_codec=ExportAudioCodec(
                str(data.get("export_audio_codec", ExportAudioCodec.AAC.value))
            ),
            export_color_space=ExportColorSpace(
                str(data.get("export_color_space", ExportColorSpace.BT709_SDR.value))
            ),
            export_two_pass=bool(data.get("export_two_pass", False)),
            export_ffmpeg_preset=str(data.get("export_ffmpeg_preset", "medium") or "medium"),
            badge_size=BadgeSize(str(data.get("badge_size", BadgeSize.M.value))),
            default_tool=str(data.get("default_tool", "project") or "project"),
            reopen_last_tool=bool(data.get("reopen_last_tool", True)),
            layout_locked=_optional_bool(layout_locked),
            layout_rail_width=_optional_int(layout_rail_width),
            layout_inspector_width=_optional_int(layout_inspector_width),
            layout_waveform_height=_optional_int(layout_waveform_height),
            marker_template=_popup_template_from_dict(data.get("marker_template")),
            review_text_boxes=review_text_boxes,
            project_defaults=project_defaults,
            active_template_name=active_template_name,
            settings_templates=settings_templates,
            recent_projects=recent_projects,
        )
        if not settings.active_template_name:
            settings.active_template_name = "Default"
        if not settings.settings_templates:
            settings.settings_templates = {
                settings.active_template_name: settings.template_snapshot()
            }
        elif settings.active_template_name not in settings.settings_templates:
            settings.settings_templates[settings.active_template_name] = (
                settings.template_snapshot()
            )
        return settings


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> AppSettings:
    ensure_app_dir()
    if not SETTINGS_PATH.exists():
        settings = AppSettings()
        settings.settings_templates = {settings.active_template_name: settings.template_snapshot()}
        save_settings(settings)
        return settings
    return AppSettings.from_dict(json.loads(SETTINGS_PATH.read_text()))


def save_settings(settings: AppSettings) -> None:
    ensure_app_dir()
    SETTINGS_PATH.write_text(json.dumps(settings.to_dict(), indent=2))


def folder_settings_path(project_path: str | Path | None) -> Path | None:
    if project_path in {None, ""}:
        return None
    return Path(project_path) / FOLDER_SETTINGS_FILENAME


def load_folder_settings(project_path: str | Path | None) -> AppSettings | None:
    path = folder_settings_path(project_path)
    if path is None or not path.exists():
        return None
    payload = tomllib.loads(path.read_text())
    return AppSettings.from_dict(payload)


def save_folder_settings(project_path: str | Path, settings: AppSettings) -> None:
    path = folder_settings_path(project_path)
    if path is None:
        raise ValueError("Project path is required for folder settings.")
    path.parent.mkdir(parents=True, exist_ok=True)
    data = settings.config_dict()

    def _toml_value(value: object) -> str:
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return json.dumps(str(value))

    lines = [f"detection_threshold = {data['detection_threshold']}"]
    lines.append(f"default_match_type = {json.dumps(str(data['default_match_type']))}")
    if data["default_stage_number"] is not None:
        lines.append(f"default_stage_number = {int(data['default_stage_number'])}")
    if data["default_competitor_name"]:
        lines.append(
            f"default_competitor_name = {json.dumps(str(data['default_competitor_name']))}"
        )
    if data["default_competitor_place"] is not None:
        lines.append(f"default_competitor_place = {int(data['default_competitor_place'])}")
    lines.extend(
        [
            f'overlay_position = "{data["overlay_position"]}"',
            f"merge_pip_x = {data['merge_pip_x']}",
            f"merge_pip_y = {data['merge_pip_y']}",
            f'merge_layout = "{data["merge_layout"]}"',
            f'pip_size = "{data["pip_size"]}"',
            f"merge_source_defaults_json = {json.dumps(json.dumps(data['merge_source_defaults']))}",
            f'export_quality = "{data["export_quality"]}"',
            f'export_preset = "{data["export_preset"]}"',
            f'export_frame_rate = "{data["export_frame_rate"]}"',
            f'export_video_codec = "{data["export_video_codec"]}"',
            f'export_audio_codec = "{data["export_audio_codec"]}"',
            f'export_color_space = "{data["export_color_space"]}"',
            f"export_two_pass = {'true' if data['export_two_pass'] else 'false'}",
            f"export_ffmpeg_preset = {json.dumps(str(data['export_ffmpeg_preset']))}",
            f'badge_size = "{data["badge_size"]}"',
            f'default_tool = "{data["default_tool"]}"',
            f"reopen_last_tool = {'true' if data['reopen_last_tool'] else 'false'}",
        ]
    )
    if data["layout_locked"] is not None:
        lines.append(f"layout_locked = {'true' if data['layout_locked'] else 'false'}")
    if data["layout_rail_width"] is not None:
        lines.append(f"layout_rail_width = {int(data['layout_rail_width'])}")
    if data["layout_inspector_width"] is not None:
        lines.append(f"layout_inspector_width = {int(data['layout_inspector_width'])}")
    if data["layout_waveform_height"] is not None:
        lines.append(f"layout_waveform_height = {int(data['layout_waveform_height'])}")
    for section_name in ("timer_badge", "shot_badge", "current_shot_badge", "hit_factor_badge"):
        style = data[section_name]
        if isinstance(style, dict):
            lines.append("")
            lines.append(f"[{section_name}]")
            for key in ("background_color", "text_color", "opacity"):
                lines.append(f"{key} = {_toml_value(style[key])}")
    shotml = data["shotml_defaults"]
    if isinstance(shotml, dict):
        lines.append("")
        lines.append("[shotml_defaults]")
        for key, value in shotml.items():
            lines.append(f"{key} = {_toml_value(value)}")
    marker_template = data["marker_template"]
    if isinstance(marker_template, dict):
        lines.append("")
        lines.append("[marker_template]")
        for key, value in marker_template.items():
            lines.append(f"{key} = {_toml_value(value)}")
    path.write_text("\n".join(lines) + "\n")


def delete_folder_settings(project_path: str | Path | None) -> None:
    path = folder_settings_path(project_path)
    if path is None or not path.exists():
        return
    path.unlink()
