from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass, field, fields
from pathlib import Path
import tomllib

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
    OverlayTextBox,
    PipSize,
    PopupTemplate,
    ShotMLSettings,
)

APP_DIR = Path.home() / ".splitshot"
SETTINGS_PATH = APP_DIR / "settings.json"
FOLDER_SETTINGS_FILENAME = "splitshot.conf"


def _serialize_popup_template(template: PopupTemplate) -> dict[str, object]:
    return {
        "enabled": template.enabled,
        "content_type": template.content_type,
        "text_source": template.text_source,
        "duration_ms": template.duration_ms,
        "quadrant": template.quadrant,
        "width": template.width,
        "height": template.height,
        "follow_motion": template.follow_motion,
        "background_color": template.background_color,
        "text_color": template.text_color,
        "opacity": template.opacity,
    }


def _float_or_default(value: object, default: float) -> float:
    if value is None or value == "":
        return default
    return float(value)


def _popup_template_from_dict(data: object) -> PopupTemplate:
    payload = data if isinstance(data, dict) else {}
    return PopupTemplate(
        enabled=bool(payload.get("enabled", True)),
        content_type=str(payload.get("content_type", "text") or "text"),
        text_source=str(payload.get("text_source", "score") or "score"),
        duration_ms=max(1, int(payload.get("duration_ms", 1000) or 1000)),
        quadrant=str(payload.get("quadrant", "middle_middle") or "middle_middle"),
        width=max(0, int(payload.get("width", 0) or 0)),
        height=max(0, int(payload.get("height", 0) or 0)),
        follow_motion=bool(payload.get("follow_motion", False)),
        background_color=str(payload.get("background_color", "#000000") or "#000000"),
        text_color=str(payload.get("text_color", "#ffffff") or "#ffffff"),
        opacity=max(0.0, min(1.0, _float_or_default(payload.get("opacity"), 0.9))),
    )


def _serialize_badge_style(style: BadgeStyle) -> dict[str, object]:
    return {
        "background_color": style.background_color,
        "text_color": style.text_color,
        "opacity": style.opacity,
    }


def _badge_style_from_dict(data: object, fallback: BadgeStyle | None = None) -> BadgeStyle:
    default = fallback or BadgeStyle()
    payload = data if isinstance(data, dict) else {}
    return BadgeStyle(
        background_color=str(payload.get("background_color", default.background_color) or default.background_color),
        text_color=str(payload.get("text_color", default.text_color) or default.text_color),
        opacity=max(0.0, min(1.0, _float_or_default(payload.get("opacity"), default.opacity))),
    )


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
    current_shot_badge: BadgeStyle = field(default_factory=lambda: BadgeStyle(background_color="#DC2626"))
    hit_factor_badge: BadgeStyle = field(default_factory=lambda: BadgeStyle(background_color="#047857"))
    overlay_custom_box_background_color: str = "#000000"
    overlay_custom_box_text_color: str = "#ffffff"
    overlay_custom_box_opacity: float = 0.9
    merge_layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    merge_pip_x: float = 1.0
    merge_pip_y: float = 1.0
    pip_size: PipSize = PipSize.MEDIUM
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
    marker_template: PopupTemplate = field(default_factory=PopupTemplate)
    review_text_boxes: list[dict[str, object]] = field(default_factory=list)
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
            "marker_template": _serialize_popup_template(self.marker_template),
            "review_text_boxes": deepcopy(self.review_text_boxes),
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
    def from_dict(cls, data: dict[str, object]) -> "AppSettings":
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
        settings_templates = _settings_templates_from_dict(data.get("settings_templates"))
        active_template_name = str(data.get("active_template_name", "Default") or "Default")
        default_stage_number = data.get("default_stage_number")
        default_competitor_place = data.get("default_competitor_place")
        try:
            parsed_default_stage_number = None if default_stage_number in {None, ""} else int(default_stage_number)
        except (TypeError, ValueError):
            parsed_default_stage_number = None
        try:
            parsed_default_competitor_place = (
                None if default_competitor_place in {None, ""} else int(default_competitor_place)
            )
        except (TypeError, ValueError):
            parsed_default_competitor_place = None
        recent_projects = [str(item) for item in data.get("recent_projects", [])]
        settings = cls(
            detection_threshold=factory_threshold,
            shotml_defaults=shotml_defaults,
            default_match_type=str(data.get("default_match_type", "uspsa") or "uspsa").strip().lower(),
            default_stage_number=parsed_default_stage_number,
            default_competitor_name=str(data.get("default_competitor_name", "") or ""),
            default_competitor_place=parsed_default_competitor_place,
            overlay_position=OverlayPosition(str(data.get("overlay_position", OverlayPosition.BOTTOM.value))),
            timer_badge=_badge_style_from_dict(data.get("timer_badge"), BadgeStyle()),
            shot_badge=_badge_style_from_dict(data.get("shot_badge"), BadgeStyle(background_color="#1D4ED8")),
            current_shot_badge=_badge_style_from_dict(data.get("current_shot_badge"), BadgeStyle(background_color="#DC2626")),
            hit_factor_badge=_badge_style_from_dict(data.get("hit_factor_badge"), BadgeStyle(background_color="#047857")),
            overlay_custom_box_background_color=str(data.get("overlay_custom_box_background_color", "#000000") or "#000000"),
            overlay_custom_box_text_color=str(data.get("overlay_custom_box_text_color", "#ffffff") or "#ffffff"),
            overlay_custom_box_opacity=max(0.0, min(1.0, _float_or_default(data.get("overlay_custom_box_opacity"), 0.9))),
            merge_layout=MergeLayout(str(data.get("merge_layout", MergeLayout.SIDE_BY_SIDE.value))),
            merge_pip_x=_float_or_default(data.get("merge_pip_x"), 1.0),
            merge_pip_y=_float_or_default(data.get("merge_pip_y"), 1.0),
            pip_size=PipSize(str(data.get("pip_size", PipSize.MEDIUM.value))),
            export_quality=ExportQuality(str(data.get("export_quality", ExportQuality.HIGH.value))),
            export_preset=ExportPreset(str(data.get("export_preset", ExportPreset.SOURCE.value))),
            export_frame_rate=ExportFrameRate(str(data.get("export_frame_rate", ExportFrameRate.SOURCE.value))),
            export_video_codec=ExportVideoCodec(str(data.get("export_video_codec", ExportVideoCodec.H264.value))),
            export_audio_codec=ExportAudioCodec(str(data.get("export_audio_codec", ExportAudioCodec.AAC.value))),
            export_color_space=ExportColorSpace(str(data.get("export_color_space", ExportColorSpace.BT709_SDR.value))),
            export_two_pass=bool(data.get("export_two_pass", False)),
            export_ffmpeg_preset=str(data.get("export_ffmpeg_preset", "medium") or "medium"),
            badge_size=BadgeSize(str(data.get("badge_size", BadgeSize.M.value))),
            default_tool=str(data.get("default_tool", "project") or "project"),
            reopen_last_tool=bool(data.get("reopen_last_tool", True)),
            marker_template=_popup_template_from_dict(data.get("marker_template")),
            review_text_boxes=review_text_boxes,
            active_template_name=active_template_name,
            settings_templates=settings_templates,
            recent_projects=recent_projects,
        )
        if not settings.active_template_name:
            settings.active_template_name = "Default"
        if not settings.settings_templates:
            settings.settings_templates = {settings.active_template_name: settings.template_snapshot()}
        elif settings.active_template_name not in settings.settings_templates:
            settings.settings_templates[settings.active_template_name] = settings.template_snapshot()
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

    lines = [f'detection_threshold = {data["detection_threshold"]}']
    lines.append(f'default_match_type = {json.dumps(str(data["default_match_type"]))}')
    if data["default_stage_number"] is not None:
        lines.append(f'default_stage_number = {int(data["default_stage_number"])}')
    if data["default_competitor_name"]:
        lines.append(f'default_competitor_name = {json.dumps(str(data["default_competitor_name"]))}')
    if data["default_competitor_place"] is not None:
        lines.append(f'default_competitor_place = {int(data["default_competitor_place"])}')
    lines.extend([
        f'overlay_position = "{data["overlay_position"]}"',
        f'merge_pip_x = {data["merge_pip_x"]}',
        f'merge_pip_y = {data["merge_pip_y"]}',
        f'merge_layout = "{data["merge_layout"]}"',
        f'pip_size = "{data["pip_size"]}"',
        f'export_quality = "{data["export_quality"]}"',
        f'export_preset = "{data["export_preset"]}"',
        f'export_frame_rate = "{data["export_frame_rate"]}"',
        f'export_video_codec = "{data["export_video_codec"]}"',
        f'export_audio_codec = "{data["export_audio_codec"]}"',
        f'export_color_space = "{data["export_color_space"]}"',
        f'export_two_pass = {"true" if data["export_two_pass"] else "false"}',
        f'export_ffmpeg_preset = {json.dumps(str(data["export_ffmpeg_preset"]))}',
        f'badge_size = "{data["badge_size"]}"',
        f'default_tool = "{data["default_tool"]}"',
        f'reopen_last_tool = {"true" if data["reopen_last_tool"] else "false"}',
    ])
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
