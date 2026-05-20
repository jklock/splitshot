from __future__ import annotations

import sys


WINDOWS_UI_FONT_FAMILY = "Segoe UI"
LEGACY_MAC_FONT_FAMILY = "Helvetica Neue"
WINDOWS_SANS_FONT_FAMILIES = (
    "Segoe UI",
    "Arial",
    "Verdana",
    "Tahoma",
    "Trebuchet MS",
)
WINDOWS_MONO_FONT_FAMILIES = (
    "Consolas",
    "Courier New",
    "Lucida Console",
)
WINDOWS_SERIF_FONT_FAMILIES = (
    "Georgia",
    "Cambria",
    "Times New Roman",
)


def is_windows_platform(platform_name: str | None = None) -> bool:
    platform_value = platform_name or sys.platform
    return str(platform_value).startswith("win")


def default_overlay_font_family(platform_name: str | None = None) -> str:
    if is_windows_platform(platform_name):
        return WINDOWS_UI_FONT_FAMILY
    return LEGACY_MAC_FONT_FAMILY


def resolve_overlay_font_family(font_family: str | None, platform_name: str | None = None) -> str:
    normalized = str(font_family or "").strip()
    if not normalized:
        return default_overlay_font_family(platform_name)
    if is_windows_platform(platform_name) and normalized == LEGACY_MAC_FONT_FAMILY:
        return WINDOWS_UI_FONT_FAMILY
    return normalized
