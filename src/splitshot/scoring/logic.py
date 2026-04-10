from __future__ import annotations

from splitshot.domain.models import Project, ScoreLetter, ScoreMark, ShotEvent


def calculate_hit_factor(project: Project) -> float | None:
    total_time_ms = project.analysis.shots[-1].time_ms if project.analysis.shots else None
    if not project.scoring.enabled or total_time_ms is None or total_time_ms <= 0:
        return None

    total_points = 0
    for shot in project.analysis.shots:
        if shot.score is None:
            continue
        total_points += project.scoring.point_map.get(shot.score.letter.value, 0)

    adjusted_points = max(0, total_points - project.scoring.penalties)
    if adjusted_points == 0:
        return 0.0
    return adjusted_points / (total_time_ms / 1000.0)


def assign_score(shot: ShotEvent, letter: ScoreLetter) -> None:
    shot.score = ScoreMark(letter=letter)


def set_score_position(shot: ShotEvent, x_norm: float, y_norm: float) -> None:
    if shot.score is None:
        shot.score = ScoreMark()
    shot.score.x_norm = x_norm
    shot.score.y_norm = y_norm


def current_shot_index(project: Project, position_ms: int) -> int | None:
    current_index = None
    for index, shot in enumerate(project.analysis.shots):
        if shot.time_ms <= position_ms:
            current_index = index
        else:
            break
    return current_index
