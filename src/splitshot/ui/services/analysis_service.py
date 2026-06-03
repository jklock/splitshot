"""Analysis, timing, and shot-mutation helpers extracted from the UI controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from splitshot.domain.models import TimingChangeProposal
    from splitshot.ui.controller import ProjectController


def _controller_module():
    import splitshot.ui.controller as controller_module

    return controller_module


def set_detection_threshold(controller: ProjectController, value: float) -> None:
    controller.set_shotml_settings({"detection_threshold": value}, rerun=True)


def analyze_primary(controller: ProjectController) -> None:
    controller_module = _controller_module()
    if not controller.project.primary_video.path:
        return
    selection_context = controller_module._shot_selection_context(
        controller.project,
        controller.project.ui_state.selected_shot_id,
        fallback_mode="time",
    )
    previous_shots = [
        controller_module.deepcopy(shot) for shot in controller.project.analysis.shots
    ]
    previous_events = [
        controller_module.deepcopy(event) for event in controller.project.analysis.events
    ]
    controller._set_status("Analyzing primary video for beep and shot detections...")
    result = controller_module._run_analyze_video_audio(
        controller.project.primary_video.path,
        controller.project.analysis.shotml_settings.detection_threshold,
        controller.project.analysis.shotml_settings,
    )
    controller.project.analysis.beep_time_ms_primary = result.beep_time_ms
    controller.project.analysis.waveform_primary = result.waveform
    controller.project.analysis.shots = controller_module._merge_reanalyzed_shots(
        previous_shots,
        result.shots,
        controller.project.analysis.shotml_settings,
    )
    controller.project.analysis.events = controller_module._reanchor_timing_events_for_shots(
        previous_events,
        previous_shots,
        controller.project.analysis.shots,
    )
    controller.project.analysis.detection_review_suggestions = [
        controller_module.asdict(suggestion) for suggestion in result.review_suggestions
    ]
    controller.project.analysis.detection_threshold = (
        controller.project.analysis.shotml_settings.detection_threshold
    )
    controller.project.analysis.timing_change_proposals = []
    controller.project.analysis.last_shotml_run_summary = {
        "video_path": controller.project.primary_video.path,
        "threshold": controller.project.analysis.shotml_settings.detection_threshold,
        "sample_rate": result.sample_rate,
        "beep_time_ms": result.beep_time_ms,
        "shot_count": len(result.shots),
        "review_suggestion_count": len(result.review_suggestions),
    }
    controller_module.ensure_default_shot_scores(controller.project)
    controller_module.normalize_project_timing_events(controller.project)
    controller_module._revalidate_timing_ui_state(controller.project, selection_context)
    controller._remember_original_shots()
    controller.update_hit_factor()
    controller._set_status(
        f"Primary analysis complete. Detected {len(result.shots)} shots"
        + ("" if result.beep_time_ms is None else f" and beep at {result.beep_time_ms} ms")
        + "."
    )
    controller.project.touch()
    controller.project_changed.emit()


def analyze_secondary(controller: ProjectController) -> None:
    controller_module = _controller_module()
    source = controller_module._first_analyzable_merge_source(controller.project)
    if source is None or not source.asset.path:
        controller_module._clear_secondary_analysis_state(
            controller.project,
            preserve_sync_offset=True,
        )
        controller.project.secondary_video = None
        return
    controller.project.secondary_video = source.asset
    controller.project.analysis.analyzed_secondary_source_id = source.id
    controller.project.analysis.secondary_analysis_status = "running"
    controller.project.analysis.secondary_analysis_message = "Analyzing PiP sync source."
    controller._set_status("Analyzing secondary video and computing sync offset...")
    result = controller_module._run_analyze_video_audio(
        source.asset.path,
        controller.project.analysis.shotml_settings.detection_threshold,
        controller.project.analysis.shotml_settings,
    )
    controller.project.analysis.beep_time_ms_secondary = result.beep_time_ms
    controller.project.analysis.waveform_secondary = result.waveform
    controller.project.analysis.sync_offset_ms = controller_module.compute_sync_offset(
        controller.project.analysis.beep_time_ms_primary,
        controller.project.analysis.beep_time_ms_secondary,
    )
    controller.project.analysis.secondary_sync_source = "auto"
    controller.project.analysis.secondary_analysis_status = (
        "ready" if result.beep_time_ms is not None else "no_beep"
    )
    controller.project.analysis.secondary_analysis_message = (
        "Secondary beep detected."
        if result.beep_time_ms is not None
        else "No secondary beep detected. Manual sync is still available."
    )
    source.sync_offset_ms = controller.project.analysis.sync_offset_ms
    controller._set_status(
        "Secondary analysis complete."
        + (
            ""
            if result.beep_time_ms is None
            else f" Sync offset: {controller.project.analysis.sync_offset_ms} ms."
        )
    )
    controller.project.touch()
    controller.project_changed.emit()


def set_shotml_settings(
    controller: ProjectController,
    updates: dict[str, object],
    *,
    rerun: bool = False,
    update_app_defaults: bool = False,
) -> None:
    controller_module = _controller_module()
    settings = controller.project.analysis.shotml_settings
    changed = False
    valid_fields = {
        item.name: item for item in controller_module.fields(controller_module.ShotMLSettings)
    }
    for key, raw_value in updates.items():
        field_info = valid_fields.get(str(key))
        if field_info is None:
            continue
        current_value = getattr(settings, field_info.name)
        try:
            if isinstance(current_value, bool):
                next_value = bool(raw_value)
            elif isinstance(current_value, int) and not isinstance(current_value, bool):
                next_value = int(raw_value)
            elif isinstance(current_value, float):
                next_value = float(raw_value)
            else:
                next_value = str(raw_value)
        except (TypeError, ValueError):
            continue
        if current_value != next_value:
            setattr(settings, field_info.name, next_value)
            changed = True

    controller.project.analysis.detection_threshold = settings.detection_threshold
    controller.project.analysis.shotml_settings = settings
    if update_app_defaults:
        persisted_defaults = controller_module.ShotMLSettings(**controller_module.asdict(settings))
        persisted_defaults.detection_threshold = (
            controller_module.ShotMLSettings().detection_threshold
        )
        controller.settings.detection_threshold = persisted_defaults.detection_threshold
        controller.settings.shotml_defaults = persisted_defaults
        controller_module.save_settings(controller.settings)
        controller.settings_changed.emit()
    if rerun and controller.project.primary_video.path:
        if changed:
            controller.project.analysis.timing_change_proposals = []
        controller.analyze_primary()
        if controller_module._first_analyzable_merge_source(controller.project) is not None:
            controller.analyze_secondary()
        return
    if changed:
        controller.project.analysis.timing_change_proposals = []
        controller._set_status("Updated ShotML settings.")
    else:
        controller._set_status("ShotML settings unchanged.")
    controller.project.touch()
    controller.project_changed.emit()


def reset_shotml_settings(controller: ProjectController) -> None:
    controller_module = _controller_module()
    controller.project.analysis.shotml_settings = controller_module.ShotMLSettings()
    controller.project.analysis.detection_threshold = (
        controller.project.analysis.shotml_settings.detection_threshold
    )
    controller.project.analysis.timing_change_proposals = []
    controller.settings.detection_threshold = (
        controller.project.analysis.shotml_settings.detection_threshold
    )
    controller.settings.shotml_defaults = controller_module.ShotMLSettings()
    controller_module.save_settings(controller.settings)
    controller.settings_changed.emit()
    controller._set_status("Reset ShotML settings to factory defaults.")
    controller.project.touch()
    controller.project_changed.emit()


def rerun_shotml(controller: ProjectController) -> None:
    controller_module = _controller_module()
    if controller.project.primary_video.path:
        controller.analyze_primary()
    if controller_module._first_analyzable_merge_source(controller.project) is not None:
        controller.analyze_secondary()
        return
    controller.project.touch()
    controller._set_status("ShotML settings saved.")
    controller.project_changed.emit()


def review_suggestion_objects(controller: ProjectController):
    controller_module = _controller_module()
    suggestions: list[controller_module.TimingReviewSuggestion] = []
    for item in controller.project.analysis.detection_review_suggestions:
        if not isinstance(item, dict):
            continue
        suggestions.append(
            controller_module.TimingReviewSuggestion(
                kind=str(item.get("kind", "")),
                severity=str(item.get("severity", "review")),
                message=str(item.get("message", "")),
                suggested_action=str(item.get("suggested_action", "")),
                shot_number=None
                if item.get("shot_number") in {None, ""}
                else int(item["shot_number"]),
                shot_time_ms=None
                if item.get("shot_time_ms") in {None, ""}
                else int(item["shot_time_ms"]),
                confidence=None
                if item.get("confidence") in {None, ""}
                else float(item["confidence"]),
                support_confidence=None
                if item.get("support_confidence") in {None, ""}
                else float(item["support_confidence"]),
                interval_ms=None
                if item.get("interval_ms") in {None, ""}
                else int(item["interval_ms"]),
            )
        )
    return suggestions


def generate_timing_change_proposals(controller: ProjectController) -> None:
    controller_module = _controller_module()
    proposals = controller_module.timing_change_proposals_from_review_suggestions(
        controller.project.analysis.shots,
        controller.project.analysis.beep_time_ms_primary,
        controller._review_suggestion_objects(),
    )
    existing_restore_ids = {
        proposal.shot_id
        for proposal in controller.project.analysis.timing_change_proposals
        if proposal.proposal_type == "restore_shot" and proposal.status == "pending"
    }
    for shot in controller.project.analysis.shots:
        original = controller._original_shot_state_by_id.get(shot.id)
        if original is None or original.time_ms == shot.time_ms or shot.id in existing_restore_ids:
            continue
        proposals.append(
            controller_module.TimingChangeProposal(
                proposal_type="restore_shot",
                shot_id=shot.id,
                shot_number=next(
                    (
                        index + 1
                        for index, candidate in enumerate(
                            controller_module.sort_shots(controller.project.analysis.shots)
                        )
                        if candidate.id == shot.id
                    ),
                    None,
                ),
                source_time_ms=shot.time_ms,
                target_time_ms=original.time_ms,
                message=(
                    "Restore ShotML's original timestamp for this edited shot "
                    f"({original.time_ms} ms)."
                ),
                evidence={"original_source": original.source.value},
            )
        )
    controller.project.analysis.timing_change_proposals = proposals
    controller._set_status(
        f"Generated {len(proposals)} ShotML timing proposal{'s' if len(proposals) != 1 else ''}."
    )
    controller.project.touch()
    controller.project_changed.emit()


def pending_proposal(
    controller: ProjectController,
    proposal_id: str,
) -> TimingChangeProposal:
    for proposal in controller.project.analysis.timing_change_proposals:
        if proposal.id == proposal_id and proposal.status == "pending":
            return proposal
    raise ValueError("Pending proposal not found")


def apply_timing_change_proposal(controller: ProjectController, proposal_id: str) -> None:
    controller_module = _controller_module()
    proposal = controller._pending_proposal(proposal_id)
    proposal.status = "applied"
    if proposal.proposal_type == "move_beep":
        if proposal.target_time_ms is None:
            raise ValueError("Proposal target time is required")
        controller.project.analysis.beep_time_ms_primary = max(0, int(proposal.target_time_ms))
    elif proposal.proposal_type == "move_shot":
        if proposal.shot_id is None or proposal.target_time_ms is None:
            raise ValueError("Proposal shot and target time are required")
        controller.move_shot(proposal.shot_id, int(proposal.target_time_ms))
        return
    elif proposal.proposal_type in {"suppress_shot", "choose_close_pair_survivor"}:
        if proposal.shot_id is None:
            raise ValueError("Proposal shot is required")
        controller.delete_shot(proposal.shot_id)
        return
    elif proposal.proposal_type == "restore_shot":
        if proposal.shot_id is None:
            raise ValueError("Proposal shot is required")
        controller.restore_original_shot_timing(proposal.shot_id)
        proposal.status = "applied"
        return
    else:
        raise ValueError(f"Unsupported proposal type: {proposal.proposal_type}")
    controller_module.normalize_project_timing_events(controller.project)
    controller_module._revalidate_timing_ui_state(controller.project)
    controller.update_hit_factor()
    controller._set_status("Applied ShotML timing proposal.")
    controller.project.touch()
    controller.project_changed.emit()


def discard_timing_change_proposal(controller: ProjectController, proposal_id: str) -> None:
    proposal = controller._pending_proposal(proposal_id)
    proposal.status = "discarded"
    controller._set_status("Discarded ShotML timing proposal.")
    controller.project.touch()
    controller.project_changed.emit()


def move_shot(
    controller: ProjectController,
    shot_id: str,
    time_ms: int,
    *,
    preserve_following_splits: bool = False,
) -> None:
    controller_module = _controller_module()
    if preserve_following_splits:
        shots = controller_module.sort_shots(controller.project.analysis.shots)
        shot_index = next(
            (index for index, shot in enumerate(shots) if shot.id == shot_id),
            None,
        )
        if shot_index is None:
            raise ValueError("Shot not found")
        shot = shots[shot_index]
        if shot.shotml_time_ms is None:
            shot.shotml_time_ms = shot.time_ms
        if shot.shotml_confidence is None:
            original = controller._original_shot_state_by_id.get(shot.id)
            shot.shotml_confidence = (
                original.confidence if original is not None else shot.confidence
            )
        lower_bound_ms = (
            controller.project.analysis.beep_time_ms_primary
            if shot_index == 0 and controller.project.analysis.beep_time_ms_primary is not None
            else (shots[shot_index - 1].time_ms if shot_index > 0 else 0)
        )
        target_time_ms = max(lower_bound_ms, time_ms)
        delta_ms = target_time_ms - shot.time_ms
        if delta_ms:
            for shifted_shot in shots[shot_index:]:
                if shifted_shot.shotml_time_ms is None:
                    shifted_shot.shotml_time_ms = shifted_shot.time_ms
                if shifted_shot.shotml_confidence is None:
                    original = controller._original_shot_state_by_id.get(shifted_shot.id)
                    shifted_shot.shotml_confidence = (
                        original.confidence if original is not None else shifted_shot.confidence
                    )
                shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
    else:
        for shot in controller.project.analysis.shots:
            if shot.id == shot_id:
                if shot.shotml_time_ms is None:
                    shot.shotml_time_ms = shot.time_ms
                if shot.shotml_confidence is None:
                    original = controller._original_shot_state_by_id.get(shot.id)
                    shot.shotml_confidence = (
                        original.confidence if original is not None else shot.confidence
                    )
                shot.time_ms = max(0, time_ms)
                if shot.source == controller_module.ShotSource.AUTO:
                    shot.source = controller_module.ShotSource.MANUAL
                    shot.confidence = None
                break
    controller.project.sort_shots()
    controller_module.normalize_project_timing_events(controller.project)
    controller_module._revalidate_timing_ui_state(controller.project)
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def delete_shot(controller: ProjectController, shot_id: str) -> None:
    controller_module = _controller_module()
    selection_context = (
        controller_module._shot_selection_context(
            controller.project,
            shot_id,
            fallback_mode="index",
        )
        if controller.project.ui_state.selected_shot_id == shot_id
        else None
    )
    controller.project.analysis.shots = [
        shot for shot in controller.project.analysis.shots if shot.id != shot_id
    ]
    controller._forget_original_shot(shot_id)
    controller_module.normalize_project_timing_events(controller.project)
    controller_module._revalidate_timing_ui_state(
        controller.project,
        selection_context,
    )
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def restore_original_shot_timing(
    controller: ProjectController,
    shot_id: str,
    *,
    preserve_following_splits: bool = False,
) -> None:
    controller_module = _controller_module()
    original = controller._original_shot_state_by_id.get(shot_id)
    if original is None:
        raise ValueError("Original split not found")
    shots = controller_module.sort_shots(controller.project.analysis.shots)
    for shot_index, shot in enumerate(shots):
        if shot.id != shot_id:
            continue
        restored_time_ms = max(
            0,
            shot.shotml_time_ms if shot.shotml_time_ms is not None else original.time_ms,
        )
        if preserve_following_splits:
            delta_ms = restored_time_ms - shot.time_ms
            if delta_ms:
                for shifted_shot in shots[shot_index:]:
                    if shifted_shot.shotml_time_ms is None:
                        shifted_shot.shotml_time_ms = shifted_shot.time_ms
                    if shifted_shot.shotml_confidence is None:
                        original_shifted = controller._original_shot_state_by_id.get(
                            shifted_shot.id
                        )
                        shifted_shot.shotml_confidence = (
                            original_shifted.confidence
                            if original_shifted is not None
                            else shifted_shot.confidence
                        )
                    shifted_shot.time_ms = max(0, shifted_shot.time_ms + delta_ms)
        else:
            shot.time_ms = restored_time_ms
        shot.source = original.source
        shot.confidence = (
            shot.shotml_confidence if shot.shotml_confidence is not None else original.confidence
        )
        controller.project.sort_shots()
        controller.update_hit_factor()
        controller._set_status("Restored original split.")
        controller.project.touch()
        controller.project_changed.emit()
        return
    raise ValueError("Shot not found")
