from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from splitshot.domain.models import BadgeSize, ExportQuality, MergeLayout, OverlayPosition, PipSize

APP_DIR = Path.home() / ".splitshot"
SETTINGS_PATH = APP_DIR / "settings.json"


@dataclass(slots=True)
class AppSettings:
    detection_threshold: float = 0.5
    overlay_position: OverlayPosition = OverlayPosition.BOTTOM
    merge_layout: MergeLayout = MergeLayout.SIDE_BY_SIDE
    pip_size: PipSize = PipSize.MEDIUM
    export_quality: ExportQuality = ExportQuality.HIGH
    badge_size: BadgeSize = BadgeSize.M
    recent_projects: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, object]:
        return {
            "detection_threshold": self.detection_threshold,
            "overlay_position": self.overlay_position.value,
            "merge_layout": self.merge_layout.value,
            "pip_size": self.pip_size.value,
            "export_quality": self.export_quality.value,
            "badge_size": self.badge_size.value,
            "recent_projects": self.recent_projects,
        }

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> "AppSettings":
        return cls(
            detection_threshold=float(data.get("detection_threshold", 0.5)),
            overlay_position=OverlayPosition(str(data.get("overlay_position", OverlayPosition.BOTTOM.value))),
            merge_layout=MergeLayout(str(data.get("merge_layout", MergeLayout.SIDE_BY_SIDE.value))),
            pip_size=PipSize(str(data.get("pip_size", PipSize.MEDIUM.value))),
            export_quality=ExportQuality(str(data.get("export_quality", ExportQuality.HIGH.value))),
            badge_size=BadgeSize(str(data.get("badge_size", BadgeSize.M.value))),
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
