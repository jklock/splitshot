"""Settings defaults and template helpers extracted from the UI controller."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING

from splitshot.config import (
    AppSettings,
    delete_folder_settings,
    save_folder_settings,
    save_settings,
)
from splitshot.domain.models import (
    BadgeSize,
    ExportAudioCodec,
    ExportColorSpace,
    ExportFrameRate,
    ExportPreset,
    ExportQuality,
    ExportVideoCodec,
    MergeLayout,
    OverlayPosition,
    PipSize,
)
from splitshot.scoring.practiscore import normalize_match_type

if TYPE_CHECKING:
    from splitshot.ui.controller import ProjectController


def _badge_style_from_payload(style, payload: object) -> None:
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


def _normalize_popup_motion_mode(value: object, *, follow_motion: bool = False) -> str:
    normalized = str(value or "").strip().lower()
    if normalized in {"fixed", "guided", "manual", "auto"} and not (
        normalized == "fixed" and follow_motion
    ):
        return normalized
    return "manual" if follow_motion else "fixed"


def _popup_template_from_payload(template, payload: object) -> None:
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


def effective_settings(controller: ProjectController) -> AppSettings:
    if controller.folder_settings is None:
        return AppSettings.from_dict(controller.settings.to_dict())
    merged = controller.settings.config_dict()
    folder_payload = controller.folder_settings.config_dict()
    for key, value in folder_payload.items():
        merged[key] = value
    merged["recent_projects"] = controller.settings.recent_projects
    merged["active_template_name"] = controller.settings.active_template_name
    merged["settings_templates"] = deepcopy(controller.settings.settings_templates)
    return AppSettings.from_dict(merged)


def settings_layers(controller: ProjectController) -> dict[str, object]:
    return {
        "app": controller.settings.config_dict(),
        "folder": {}
        if controller.folder_settings is None
        else controller.folder_settings.config_dict(),
        "effective": effective_settings(controller).config_dict(),
        "project": {
            "path": "" if controller.project_path is None else str(controller.project_path),
            "folder_settings_error": controller.folder_settings_error or "",
            "popup_template": {
                "enabled": controller.project.popup_template.enabled,
                "content_type": controller.project.popup_template.content_type,
                "text_source": controller.project.popup_template.text_source,
                "duration_ms": controller.project.popup_template.duration_ms,
                "use_shot_split_duration": controller.project.popup_template.use_shot_split_duration,
                "quadrant": controller.project.popup_template.quadrant,
                "width": controller.project.popup_template.width,
                "height": controller.project.popup_template.height,
                "motion_mode": controller.project.popup_template.motion_mode,
                "follow_motion": controller.project.popup_template.follow_motion,
                "background_color": controller.project.popup_template.background_color,
                "text_color": controller.project.popup_template.text_color,
                "opacity": controller.project.popup_template.opacity,
                "style_type": controller.project.popup_template.style_type,
                "font_family": controller.project.popup_template.font_family,
                "font_size": controller.project.popup_template.font_size,
                "font_bold": controller.project.popup_template.font_bold,
                "font_italic": controller.project.popup_template.font_italic,
            },
            "review_text_boxes": [
                {
                    "id": box.id,
                    "enabled": box.enabled,
                    "lock_to_stack": box.lock_to_stack,
                    "source": box.source,
                    "text": box.text,
                    "quadrant": box.quadrant,
                    "x": box.x,
                    "y": box.y,
                    "background_color": box.background_color,
                    "text_color": box.text_color,
                    "opacity": box.opacity,
                    "width": box.width,
                    "height": box.height,
                    "style_type": box.style_type,
                    "font_family": box.font_family,
                    "font_size": box.font_size,
                    "font_bold": box.font_bold,
                    "font_italic": box.font_italic,
                }
                for box in controller.project.overlay.text_boxes
            ],
        },
    }


def select_settings_template(controller: ProjectController, template_name: str) -> None:
    template_name = str(template_name or "").strip()
    if not template_name:
        raise ValueError("Template name is required.")
    snapshot = controller._settings_template_snapshot(template_name)
    controller._apply_settings_template_snapshot(template_name, snapshot)
    controller._save_settings_and_emit()
    controller._set_status(f"Selected settings template {template_name}.")


def save_settings_template(
    controller: ProjectController,
    template_name: str,
    *,
    section: str | None = None,
) -> None:
    template_name = (
        str(template_name or "").strip() or controller.settings.active_template_name or "Default"
    )
    snapshot = controller._settings_template_snapshot(template_name)
    snapshot = controller._template_snapshot_from_current_project(snapshot, section=section)
    controller._apply_settings_template_snapshot(template_name, snapshot)
    controller._save_settings_and_emit()
    if section:
        controller._set_status(f"Saved {section} defaults to template {template_name}.")
    else:
        controller._set_status(f"Saved current project defaults to template {template_name}.")


def duplicate_settings_template(
    controller: ProjectController,
    template_name: str,
    duplicate_name: str,
) -> None:
    source_name = str(template_name or "").strip() or controller.settings.active_template_name
    duplicate_name = str(duplicate_name or "").strip()
    if not duplicate_name:
        raise ValueError("Duplicate template name is required.")
    snapshot = controller._settings_template_snapshot(source_name)
    controller._apply_settings_template_snapshot(duplicate_name, snapshot)
    controller._save_settings_and_emit()
    controller._set_status(f"Duplicated settings template {source_name} to {duplicate_name}.")


def delete_settings_template(controller: ProjectController, template_name: str) -> None:
    template_name = str(template_name or "").strip()
    if not template_name:
        return
    templates = deepcopy(controller.settings.settings_templates)
    if template_name not in templates:
        return
    if len(templates) <= 1:
        templates = {"Default": controller.settings.template_snapshot()}
        template_name = "Default"
    else:
        templates.pop(template_name, None)
    next_template_name = (
        controller.settings.active_template_name
        if template_name != controller.settings.active_template_name
        else next(iter(templates.keys()))
    )
    snapshot = templates.get(next_template_name) or next(iter(templates.values()))
    controller._apply_settings_template_snapshot(next_template_name, snapshot)
    controller.settings.settings_templates = templates
    controller._save_settings_and_emit()
    controller._set_status(f"Deleted settings template {template_name}.")


def set_settings_defaults(
    controller: ProjectController,
    payload: dict[str, object],
    *,
    scope: str = "app",
) -> None:
    template_action = str(payload.get("template_action") or "").strip().lower()
    if template_action:
        template_name = (
            str(
                payload.get("template_name")
                or controller.settings.active_template_name
                or "Default"
            ).strip()
            or "Default"
        )
        if template_action == "select":
            select_settings_template(controller, template_name)
            return
        if template_action == "save":
            save_settings_template(controller, template_name)
            return
        if template_action == "save_section":
            section = str(payload.get("section") or "").strip().lower()
            if not section:
                raise ValueError("section is required")
            save_settings_template(controller, template_name, section=section)
            return
        if template_action == "duplicate":
            duplicate_name = str(payload.get("duplicate_name") or "").strip()
            if not duplicate_name:
                raise ValueError("duplicate_name is required")
            duplicate_settings_template(controller, template_name, duplicate_name)
            return
        if template_action == "delete":
            delete_settings_template(controller, template_name)
            return
    base = (
        controller.folder_settings
        if scope == "folder" and controller.folder_settings is not None
        else controller.settings
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
        _badge_style_from_payload(
            target.current_shot_badge,
            payload.get("current_shot_badge"),
        )
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
            raw_value = payload.get("layout_locked")
            if raw_value in {None, ""}:
                target.layout_locked = None
            elif isinstance(raw_value, str):
                target.layout_locked = raw_value.strip().lower() in {"1", "true", "yes", "on"}
            else:
                target.layout_locked = bool(raw_value)
        if "layout_rail_width" in payload:
            raw_value = payload.get("layout_rail_width")
            target.layout_rail_width = (
                None if raw_value in {None, ""} else max(84, min(104, int(raw_value)))
            )
        if "layout_inspector_width" in payload:
            raw_value = payload.get("layout_inspector_width")
            target.layout_inspector_width = (
                None if raw_value in {None, ""} else max(320, min(4096, int(raw_value)))
            )
        if "layout_waveform_height" in payload:
            raw_value = payload.get("layout_waveform_height")
            target.layout_waveform_height = (
                None if raw_value in {None, ""} else max(112, min(4096, int(raw_value)))
            )
    if "detection_threshold" in payload:
        threshold = float(payload["detection_threshold"])
        target.detection_threshold = threshold
        target.shotml_defaults.detection_threshold = threshold
    marker_template_payload = payload.get("marker_template")
    if isinstance(marker_template_payload, dict):
        _popup_template_from_payload(target.marker_template, marker_template_payload)
    if scope == "folder":
        if controller.project_path is None:
            raise ValueError("Save the project before writing folder defaults.")
        controller.folder_settings = target
        controller.folder_settings_error = None
        save_folder_settings(controller.project_path, target)
    else:
        target.recent_projects = controller.settings.recent_projects
        target.active_template_name = controller.settings.active_template_name
        target.settings_templates = deepcopy(controller.settings.settings_templates)
        controller.settings = target
        controller._sync_active_settings_template()
        save_settings(controller.settings)
    controller.settings_changed.emit()
    controller._set_status(f"Updated {'folder' if scope == 'folder' else 'app'} defaults.")


def reset_settings_defaults(
    controller: ProjectController,
    *,
    scope: str = "app",
    section: str | None = None,
) -> None:
    if not section:
        restore_defaults(controller)
        return

    section_name = str(section or "").strip().lower()
    base = (
        controller.folder_settings
        if scope == "folder" and controller.folder_settings is not None
        else controller.settings
    )
    target = AppSettings.from_dict(base.to_dict())
    fallback = controller.settings if scope == "folder" else AppSettings()

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
        if controller.project_path is None:
            raise ValueError("Save the project before writing folder defaults.")
        if target.config_dict() == controller.settings.config_dict():
            delete_folder_settings(controller.project_path)
            controller.folder_settings = None
        else:
            controller.folder_settings = target
            save_folder_settings(controller.project_path, target)
        controller.folder_settings_error = None
    else:
        target.recent_projects = controller.settings.recent_projects
        target.active_template_name = controller.settings.active_template_name
        target.settings_templates = deepcopy(controller.settings.settings_templates)
        controller.settings = target
        controller._sync_active_settings_template()
        save_settings(controller.settings)
    controller.settings_changed.emit()
    controller._set_status(
        f"Reset {section_name} defaults for {'folder' if scope == 'folder' else 'app'} scope."
    )


def restore_defaults(controller: ProjectController) -> None:
    controller.settings = AppSettings()
    controller.settings.settings_templates = {
        controller.settings.active_template_name: controller.settings.template_snapshot()
    }
    save_settings(controller.settings)
    delete_folder_settings(controller.project_path)
    controller.folder_settings = None
    controller.folder_settings_error = None
    controller._apply_effective_settings_to_project(
        controller.project,
        effective_settings(controller),
        reset_tool=False,
    )
    controller.project.touch()
    controller._set_status("Restored SplitShot defaults.")
    controller.settings_changed.emit()
    controller.project_changed.emit()
