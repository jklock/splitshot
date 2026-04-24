from __future__ import annotations

import json
from dataclasses import dataclass, field, fields
from pathlib import Path
import tomllib

from splitshot.domain.models import (
    BadgeSize,
    ExportQuality,
    MergeLayout,
    OverlayPosition,
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
    }


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
    )


@dataclass(slots=True)
class AppSettings:
    detection_threshold: float = 0.35
    shotml_defaults: ShotMLSettings = field(default_factory=ShotMLSettings)
    overlay_position: OverlayPosition = OverlayPosition.BOTTOM
    merge_layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    pip_size: PipSize = PipSize.MEDIUM
    export_quality: ExportQuality = ExportQuality.HIGH
    badge_size: BadgeSize = BadgeSize.M
    default_tool: str = "project"
    reopen_last_tool: bool = True
    marker_template: PopupTemplate = field(default_factory=PopupTemplate)
    recent_projects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "detection_threshold": self.detection_threshold,
            "shotml_defaults": {
                item.name: getattr(self.shotml_defaults, item.name)
                for item in fields(ShotMLSettings)
            },
            "overlay_position": self.overlay_position.value,
            "merge_layout": self.merge_layout.value,
            "pip_size": self.pip_size.value,
            "export_quality": self.export_quality.value,
            "badge_size": self.badge_size.value,
            "default_tool": self.default_tool,
            "reopen_last_tool": self.reopen_last_tool,
            "marker_template": _serialize_popup_template(self.marker_template),
            "recent_projects": self.recent_projects,
        }

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
        # Keep the canonical threshold at the artifact-backed factory value instead of
        # treating a prior project's rerun threshold as a future app default.
        shotml_defaults.detection_threshold = factory_threshold
        return cls(
            detection_threshold=factory_threshold,
            shotml_defaults=shotml_defaults,
            overlay_position=OverlayPosition(str(data.get("overlay_position", OverlayPosition.BOTTOM.value))),
            merge_layout=MergeLayout(str(data.get("merge_layout", MergeLayout.SIDE_BY_SIDE.value))),
            pip_size=PipSize(str(data.get("pip_size", PipSize.MEDIUM.value))),
            export_quality=ExportQuality(str(data.get("export_quality", ExportQuality.HIGH.value))),
            badge_size=BadgeSize(str(data.get("badge_size", BadgeSize.M.value))),
            default_tool=str(data.get("default_tool", "project") or "project"),
            reopen_last_tool=bool(data.get("reopen_last_tool", True)),
            marker_template=_popup_template_from_dict(data.get("marker_template")),
            recent_projects=[str(item) for item in data.get("recent_projects", [])],
        )


def ensure_app_dir() -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> AppSettings:
    ensure_app_dir()
    if not SETTINGS_PATH.exists():
        settings = AppSettings()
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
    data = settings.to_dict()
    lines = [
        f'detection_threshold = {data["detection_threshold"]}',
        f'overlay_position = "{data["overlay_position"]}"',
        f'merge_layout = "{data["merge_layout"]}"',
        f'pip_size = "{data["pip_size"]}"',
        f'export_quality = "{data["export_quality"]}"',
        f'badge_size = "{data["badge_size"]}"',
        f'default_tool = "{data["default_tool"]}"',
        f'reopen_last_tool = {"true" if data["reopen_last_tool"] else "false"}',
    ]
    shotml = data["shotml_defaults"]
    if isinstance(shotml, dict):
        lines.append("")
        lines.append("[shotml_defaults]")
        for key, value in shotml.items():
            if isinstance(value, bool):
                encoded = "true" if value else "false"
            elif isinstance(value, (int, float)):
                encoded = str(value)
            else:
                encoded = json.dumps(str(value))
            lines.append(f"{key} = {encoded}")
    marker_template = data["marker_template"]
    if isinstance(marker_template, dict):
        lines.append("")
        lines.append("[marker_template]")
        for key, value in marker_template.items():
            if isinstance(value, bool):
                encoded = "true" if value else "false"
            elif isinstance(value, (int, float)):
                encoded = str(value)
            else:
                encoded = json.dumps(str(value))
            lines.append(f"{key} = {encoded}")
    path.write_text("\n".join(lines) + "\n")


def delete_folder_settings(project_path: str | Path | None) -> None:
    path = folder_settings_path(project_path)
    if path is None or not path.exists():
        return
    path.unlink()
