"""Project/session lifecycle helpers extracted from the UI controller."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from splitshot.ui.services import practiscore_sync as practiscore_sync_service

if TYPE_CHECKING:
    from splitshot.config import AppSettings
    from splitshot.domain.models import Project
    from splitshot.ui.controller import ProjectController


def _controller_module():
    import splitshot.ui.controller as controller_module

    return controller_module


def new_project_with_settings_defaults(controller: ProjectController) -> Project:
    controller_module = _controller_module()
    effective = controller.effective_settings()
    project = controller_module.Project()
    controller._apply_effective_settings_to_project(project, effective, reset_tool=True)
    return project


def apply_effective_settings_to_project(
    controller: ProjectController,
    project: Project,
    effective: AppSettings,
    *,
    reset_tool: bool,
) -> None:
    controller_module = _controller_module()
    project.analysis.shotml_settings = controller_module.ShotMLSettings(
        **controller_module.asdict(effective.shotml_defaults)
    )
    project.analysis.detection_threshold = project.analysis.shotml_settings.detection_threshold
    project.scoring.match_type = ""
    try:
        normalized_match_type = controller_module.normalize_match_type(
            effective.default_match_type
        )
    except ValueError:
        normalized_match_type = ""
    if normalized_match_type:
        project.scoring.match_type = normalized_match_type
        controller_module.apply_scoring_preset(
            project,
            controller_module.default_ruleset_for_match_type(normalized_match_type),
        )
    project.scoring.stage_number = effective.default_stage_number
    project.scoring.competitor_name = effective.default_competitor_name
    project.scoring.competitor_place = effective.default_competitor_place
    project.overlay.position = effective.overlay_position
    project.overlay.badge_size = effective.badge_size
    if effective.badge_size != controller_module.BadgeSize.CUSTOM:
        project.overlay.font_size = controller_module._badge_font_size_from_enum(
            effective.badge_size
        )
    project.overlay.timer_badge = controller_module.deepcopy(effective.timer_badge)
    project.overlay.shot_badge = controller_module.deepcopy(effective.shot_badge)
    project.overlay.current_shot_badge = controller_module.deepcopy(
        effective.current_shot_badge
    )
    project.overlay.hit_factor_badge = controller_module.deepcopy(
        effective.hit_factor_badge
    )
    project.overlay.custom_box_background_color = (
        effective.overlay_custom_box_background_color
    )
    project.overlay.custom_box_text_color = effective.overlay_custom_box_text_color
    project.overlay.custom_box_opacity = effective.overlay_custom_box_opacity
    project.merge.layout = effective.merge_layout
    project.merge.pip_size = effective.pip_size
    project.merge.pip_size_percent = controller_module._pip_size_percent_from_enum(
        effective.pip_size
    )
    project.merge.pip_x = effective.merge_pip_x
    project.merge.pip_y = effective.merge_pip_y
    project.merge_sources = [
        controller_module._merge_source_from_dict(item)
        for item in effective.merge_source_defaults
        if isinstance(item, dict)
    ]
    controller_module._sync_secondary_video_from_merge_sources(project)
    analyzed_source = controller_module._first_analyzable_merge_source(project)
    if analyzed_source is not None:
        project.analysis.analyzed_secondary_source_id = analyzed_source.id
        project.analysis.sync_offset_ms = int(analyzed_source.sync_offset_ms)
    project.export.quality = effective.export_quality
    project.export.preset = effective.export_preset
    project.export.frame_rate = effective.export_frame_rate
    project.export.video_codec = effective.export_video_codec
    project.export.audio_codec = effective.export_audio_codec
    project.export.color_space = effective.export_color_space
    project.export.two_pass = effective.export_two_pass
    project.export.ffmpeg_preset = effective.export_ffmpeg_preset
    project.popup_template = controller_module.deepcopy(effective.marker_template)
    project.overlay.text_boxes = [
        controller_module.OverlayTextBox(**box)
        for box in effective.review_text_boxes
        if isinstance(box, dict)
    ]
    if effective.layout_locked is not None:
        project.ui_state.layout_locked = bool(effective.layout_locked)
    if effective.layout_rail_width is not None:
        project.ui_state.rail_width = max(
            84,
            min(104, int(effective.layout_rail_width)),
        )
    if effective.layout_inspector_width is not None:
        project.ui_state.inspector_width = max(
            320,
            min(4096, int(effective.layout_inspector_width)),
        )
    if effective.layout_waveform_height is not None:
        project.ui_state.waveform_height = max(
            112,
            min(4096, int(effective.layout_waveform_height)),
        )
    if reset_tool:
        project.ui_state.active_tool = (
            effective.default_tool if effective.reopen_last_tool else "project"
        )


def new_project(controller: ProjectController) -> None:
    controller.folder_settings = None
    controller.folder_settings_error = None
    controller.project = controller._new_project_with_settings_defaults()
    controller.project_path = None
    controller._clear_practiscore_source()
    controller._practiscore_sync_payload = (
        practiscore_sync_service.default_practiscore_sync_payload()
    )
    controller._set_status("Ready.")
    controller._saved_snapshot = _controller_module().project_to_dict(controller.project)
    controller._remember_original_shots()
    controller.editor_scope = "single"
    controller.active_stage_id = None
    controller._return_to_workspace_available = False


def has_unsaved_changes(controller: ProjectController) -> bool:
    controller_module = _controller_module()
    return controller_module.project_to_dict(controller.project) != controller._saved_snapshot


def ensure_project_output_path(
    controller: ProjectController,
    previous_project_path: Path | None = None,
) -> None:
    controller_module = _controller_module()
    if controller.project_path is None:
        return
    current_output_path = str(controller.project.export.output_path or "").strip()
    project_output_path = str(
        controller_module.default_project_output_path(controller.project_path)
    )
    previous_output_path = (
        str(controller_module.default_project_output_path(previous_project_path))
        if previous_project_path is not None
        else ""
    )
    if not current_output_path or (
        previous_output_path and current_output_path == previous_output_path
    ):
        controller.project.export.output_path = project_output_path


def remember_project(controller: ProjectController, path: Path) -> None:
    controller_module = _controller_module()
    entries = [
        str(path),
        *[item for item in controller.settings.recent_projects if item != str(path)],
    ]
    next_entries = entries[:10]
    if controller.settings.recent_projects == next_entries:
        return
    controller.settings.recent_projects = next_entries
    controller_module.save_settings(controller.settings)
    controller.settings_changed.emit()


def autosave_project_if_needed(controller: ProjectController) -> None:
    controller_module = _controller_module()
    if controller._autosave_in_progress or controller.project_path is None:
        return
    current_snapshot = controller_module.project_to_dict(controller.project)
    if current_snapshot == controller._saved_snapshot:
        return
    try:
        controller._autosave_in_progress = True
        controller_module.save_project(controller.project, controller.project_path)
        controller._save_stage_profiles(controller.project_path)
        controller._sync_project_to_library()
        if controller.project.scoring.practiscore_source_path:
            controller._restore_practiscore_source_from_project()
        controller._saved_snapshot = controller_module.project_to_dict(controller.project)
        controller._remember_project(controller.project_path)
    except Exception as exc:  # noqa: BLE001
        controller._set_status(f"Project autosave failed: {exc}")
    finally:
        controller._autosave_in_progress = False


def restore_media_sources_from_project(
    controller: ProjectController,
    *,
    secondary_video_is_explicitly_persisted: bool = False,
) -> bool:
    controller_module = _controller_module()
    candidates = controller._project_input_candidates()
    if not candidates:
        return False

    used_paths: set[Path] = set()
    changed = False
    explicit_secondary_video = (
        controller.project.secondary_video
        if secondary_video_is_explicitly_persisted
        else None
    )
    explicit_secondary_source_id = controller_module._merge_source_id_for_asset(
        controller.project,
        explicit_secondary_video,
    )

    recovered_primary = controller._recover_media_asset_from_project_folder(
        controller.project.primary_video,
        candidates,
        used_paths,
    )
    if recovered_primary is not None:
        controller.project.primary_video = recovered_primary
        changed = True

    for source in controller.project.merge_sources:
        recovered_asset = controller._recover_media_asset_from_project_folder(
            source.asset,
            candidates,
            used_paths,
        )
        if recovered_asset is None:
            continue
        source.asset = recovered_asset
        controller_module._sync_merge_source_trim_provenance(source)
        changed = True

    if controller.project.merge_sources:
        if secondary_video_is_explicitly_persisted:
            if explicit_secondary_video is None:
                controller.project.secondary_video = None
            elif explicit_secondary_source_id is not None:
                explicit_source = controller_module._merge_source_by_id(
                    controller.project,
                    explicit_secondary_source_id,
                )
                if explicit_source is not None:
                    controller.project.secondary_video = explicit_source.asset
            else:
                recovered_secondary = controller._recover_media_asset_from_project_folder(
                    explicit_secondary_video,
                    candidates,
                    used_paths,
                )
                if recovered_secondary is not None:
                    controller.project.secondary_video = recovered_secondary
                    changed = True
        else:
            controller_module._sync_secondary_video_from_merge_sources(controller.project)
    elif controller.project.secondary_video is not None:
        recovered_secondary = controller._recover_media_asset_from_project_folder(
            controller.project.secondary_video,
            candidates,
            used_paths,
        )
        if recovered_secondary is not None:
            controller.project.secondary_video = recovered_secondary
            changed = True

    return changed


def restore_practiscore_source_from_project(
    controller: ProjectController,
    *,
    emit_change: bool = True,
) -> bool:
    controller_module = _controller_module()
    stored_path = controller.project.scoring.practiscore_source_path.strip()
    stored_name = controller.project.scoring.practiscore_source_name.strip() or None
    resolved_path = Path(stored_path) if stored_path else None
    recovered_from_folder = False

    if resolved_path is None or not resolved_path.exists():
        recovered_path, recovered_name, recovered_from_folder = (
            controller._recover_practiscore_path_from_project_folder(
                stored_path,
                stored_name,
            )
        )
        if recovered_path is not None:
            resolved_path = recovered_path
            stored_name = recovered_name or resolved_path.name

    if resolved_path is None:
        controller._clear_practiscore_source()
        return False

    display_name = stored_name or resolved_path.name
    changed = False
    if controller.project.scoring.practiscore_source_path != str(resolved_path):
        controller.project.scoring.practiscore_source_path = str(resolved_path)
        changed = True
    if controller.project.scoring.practiscore_source_name != display_name:
        controller.project.scoring.practiscore_source_name = display_name
        changed = True
    if controller.project.scoring.imported_stage is not None:
        if controller.project.scoring.imported_stage.source_path != str(resolved_path):
            controller.project.scoring.imported_stage.source_path = str(resolved_path)
            changed = True
        if controller.project.scoring.imported_stage.source_name != display_name:
            controller.project.scoring.imported_stage.source_name = display_name
            changed = True

    try:
        options = controller_module.describe_practiscore_file(
            resolved_path,
            source_name=display_name,
        )
    except (OSError, ValueError):
        controller._practiscore_source_path = resolved_path
        controller._practiscore_source_name = display_name
        controller._practiscore_options = None
        return changed or recovered_from_folder

    controller._practiscore_source_path = resolved_path
    controller._practiscore_source_name = display_name
    controller._practiscore_options = options
    if controller.project.scoring.imported_stage is None:
        try:
            controller._import_practiscore_source(
                str(resolved_path),
                display_name,
                emit_change=emit_change,
            )
            return True
        except ValueError:
            return changed or recovered_from_folder
    return changed or recovered_from_folder


def save_project(controller: ProjectController, path: str | None = None) -> None:
    controller_module = _controller_module()
    previous_project_path = controller.project_path
    target_path = Path(path) if path else controller.project_path
    if target_path is None:
        raise ValueError("Project path is required")
    controller.project.touch()
    controller.project_path = controller_module.ensure_project_suffix(target_path)
    controller.folder_settings = controller._load_folder_settings_safe(controller.project_path)
    controller._ensure_project_output_path(previous_project_path=previous_project_path)
    controller_module.save_project(controller.project, controller.project_path)
    controller._save_stage_profiles(controller.project_path)
    controller._sync_project_to_library()
    controller._restore_practiscore_source_from_project()
    controller._saved_snapshot = controller_module.project_to_dict(controller.project)
    controller._remember_original_shots()
    controller._remember_project(controller.project_path)
    controller._ensure_project_workspace_membership(controller.project_path)
    controller._set_status(f"Project folder ready at {controller.project_path}.")
    controller.project_path_changed.emit(str(controller.project_path))
    controller.project_changed.emit()


def open_project(controller: ProjectController, path: str) -> None:
    controller_module = _controller_module()
    project_path = controller_module.ensure_project_suffix(path)
    raw_payload = controller_module._project_payload_from_disk(project_path)
    secondary_video_is_explicitly_persisted = (
        isinstance(raw_payload, dict) and "secondary_video" in raw_payload
    )

    controller.project = controller_module.load_project(project_path)
    controller.project_path = project_path
    controller.folder_settings = controller._load_folder_settings_safe(controller.project_path)
    controller._ensure_project_output_path()
    loaded_snapshot = controller_module.project_to_dict(controller.project)
    recovered_media = controller._restore_media_sources_from_project(
        secondary_video_is_explicitly_persisted=secondary_video_is_explicitly_persisted,
    )
    recovered_practiscore = controller._restore_practiscore_source_from_project(
        emit_change=False
    )
    if recovered_media or recovered_practiscore:
        controller.project.touch()
    controller._saved_snapshot = (
        loaded_snapshot
        if (recovered_media or recovered_practiscore)
        else controller_module.project_to_dict(controller.project)
    )
    controller._remember_original_shots()
    controller._remember_project(controller.project_path)
    controller._ensure_project_workspace_membership(controller.project_path)
    if recovered_media and recovered_practiscore and controller._practiscore_source_name:
        controller._set_status(
            f"Opened project folder {controller.project_path} and restored renamed project media and PractiScore from {controller._practiscore_source_name}."
        )
    elif recovered_media:
        controller._set_status(
            f"Opened project folder {controller.project_path} and restored renamed project media."
        )
    elif recovered_practiscore and controller._practiscore_source_name:
        controller._set_status(
            f"Opened project folder {controller.project_path} and restored PractiScore from {controller._practiscore_source_name}."
        )
    else:
        controller._set_status(f"Opened project folder {controller.project_path}.")
    controller._load_stage_profiles(controller.project_path)
    controller.project_path_changed.emit(str(controller.project_path))
    controller.project_changed.emit()


def delete_current_project(controller: ProjectController) -> None:
    controller_module = _controller_module()
    if controller.project_path is None:
        return
    controller_module.delete_project(controller.project_path)
    controller.new_project()
    controller._set_status("Deleted the saved project metadata file.")
