"""Scoring helpers extracted from the UI controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from splitshot.domain.models import ScoreLetter
    from splitshot.ui.controller import ProjectController


def _controller_module():
    import splitshot.ui.controller as controller_module

    return controller_module


def assign_score(
    controller: ProjectController,
    shot_id: str,
    letter: ScoreLetter | None = None,
    penalty_counts: dict[str, float] | None = None,
) -> None:
    controller_module = _controller_module()
    normalized_penalty_counts = (
        None
        if penalty_counts is None
        else {
            str(key): max(0.0, float(value))
            for key, value in penalty_counts.items()
            if max(0.0, float(value)) > 0
        }
    )
    for shot in controller.project.analysis.shots:
        if shot.id == shot_id:
            if shot.score is None:
                shot.score = controller_module.default_score_mark_for_ruleset(
                    controller.project.scoring.ruleset
                )
            elif letter is not None:
                shot.score.letter = letter
            if normalized_penalty_counts is not None:
                shot.score.penalty_counts = normalized_penalty_counts
            break
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def restore_original_shot_score(controller: ProjectController, shot_id: str) -> None:
    controller_module = _controller_module()
    original = controller._original_shot_state_by_id.get(shot_id)
    if original is None:
        raise ValueError("Original score not found")
    for shot in controller.project.analysis.shots:
        if shot.id != shot_id:
            continue
        shot.score = (
            controller_module.default_score_mark_for_ruleset(controller.project.scoring.ruleset)
            if original.score is None
            else controller_module.deepcopy(original.score)
        )
        controller.update_hit_factor()
        controller._set_status("Restored original score.")
        controller.project.touch()
        controller.project_changed.emit()
        return
    raise ValueError("Shot not found")


def set_scoring_preset(controller: ProjectController, ruleset: str) -> None:
    controller_module = _controller_module()
    controller_module.apply_scoring_preset(controller.project, ruleset)
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def set_penalties(controller: ProjectController, penalties: float) -> None:
    controller.project.scoring.penalties = max(0.0, float(penalties))
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def set_penalty_counts(
    controller: ProjectController,
    penalty_counts: dict[str, float],
) -> None:
    controller.project.scoring.penalty_counts = {
        str(key): max(0.0, float(value)) for key, value in penalty_counts.items()
    }
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def set_scoring_enabled(controller: ProjectController, enabled: bool) -> None:
    controller.project.scoring.enabled = enabled
    controller.update_hit_factor()
    controller.project.touch()
    controller.project_changed.emit()


def update_hit_factor(controller: ProjectController) -> None:
    controller_module = _controller_module()
    controller.project.sort_shots()
    controller.project.scoring.hit_factor = controller_module.calculate_hit_factor(
        controller.project
    )
