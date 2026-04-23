from __future__ import annotations

from splitshot.domain.models import Project
from splitshot.scoring.logic import (
    default_score_letter_for_ruleset,
    normalize_penalty_counts_for_ruleset,
    penalty_field_short_label,
)
from splitshot.timeline.model import sort_shots


POPUP_BUBBLE_QUADRANT_POINTS = {
    "top_left": (0.125, 0.125),
    "top_middle": (0.5, 0.125),
    "top_right": (0.875, 0.125),
    "middle_left": (0.125, 0.5),
    "middle_middle": (0.5, 0.5),
    "middle_right": (0.875, 0.5),
    "bottom_left": (0.125, 0.875),
    "bottom_middle": (0.5, 0.875),
    "bottom_right": (0.875, 0.875),
    "custom": (0.5, 0.5),
}


def _field(source: object, name: str, default: object = None) -> object:
    if isinstance(source, dict):
        return source.get(name, default)
    return getattr(source, name, default)


def _clamped_float(value: object, fallback: float = 0.5) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return fallback


def _popup_easing(value: object) -> str:
    easing = str(value or "linear").strip().lower()
    return easing if easing in {"linear", "hold", "ease_in", "ease_out", "ease_in_out"} else "linear"


def _apply_easing(easing: str, ratio: float) -> float:
    clamped = max(0.0, min(1.0, ratio))
    if easing == "hold":
        return 0.0 if clamped < 1.0 else 1.0
    if easing == "ease_in":
        return clamped * clamped
    if easing == "ease_out":
        return 1.0 - ((1.0 - clamped) * (1.0 - clamped))
    if easing == "ease_in_out":
        if clamped <= 0.5:
            return 2.0 * clamped * clamped
        return 1.0 - ((-2.0 * clamped + 2.0) ** 2) / 2.0
    return clamped


def format_popup_penalty_count(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def popup_bubble_time_ms(project: Project, popup: object) -> int:
    if _field(popup, "anchor_mode", "time") == "shot" and _field(popup, "shot_id", None):
        shot = next(
            (item for item in sort_shots(project.analysis.shots) if item.id == _field(popup, "shot_id")),
            None,
        )
        if shot is not None:
            return shot.time_ms
    try:
        return max(0, int(round(float(_field(popup, "time_ms", 0) or 0))))
    except (TypeError, ValueError):
        return 0


def popup_bubble_visible_window(project: Project, popup: object) -> tuple[int, int]:
    start_ms = popup_bubble_time_ms(project, popup)
    try:
        duration_ms = max(1, int(round(float(_field(popup, "duration_ms", 1000) or 1000))))
    except (TypeError, ValueError):
        duration_ms = 1000
    return start_ms, start_ms + duration_ms


def popup_bubble_is_visible_at(project: Project, popup: object, position_ms: int) -> bool:
    start_ms, end_ms = popup_bubble_visible_window(project, popup)
    return start_ms <= int(position_ms) <= end_ms


def popup_bubble_display_text(project: Project, popup: object) -> str:
    fallback_text = str(_field(popup, "text", "") or "").strip()
    if _field(popup, "anchor_mode", "time") != "shot" or not _field(popup, "shot_id", None):
        return fallback_text

    shot = next(
        (item for item in sort_shots(project.analysis.shots) if item.id == _field(popup, "shot_id")),
        None,
    )
    if shot is None:
        return fallback_text

    score = getattr(shot, "score", None)
    default_letter = default_score_letter_for_ruleset(project.scoring.ruleset).value
    score_letter = getattr(getattr(score, "letter", None), "value", getattr(score, "letter", None))
    score_value = str(score_letter or default_letter).strip()
    penalty_counts = normalize_penalty_counts_for_ruleset(
        project.scoring.ruleset,
        getattr(score, "penalty_counts", None),
    )
    penalty_text = ", ".join(
        f"{penalty_field_short_label(field_id)} x{format_popup_penalty_count(float(value))}"
        for field_id, value in penalty_counts.items()
        if float(value) > 0
    )
    parts = [score_value]
    if penalty_text:
        parts.append(penalty_text)
    return " | ".join(part for part in parts if part) or fallback_text


def popup_bubble_motion_path(popup: object) -> list[tuple[int, float, float, str]]:
    raw_path = _field(popup, "motion_path", None) or []
    points: list[tuple[int, float, float, str]] = []
    for item in raw_path:
        try:
            offset_ms = max(0, int(round(float(_field(item, "offset_ms", _field(item, "time_ms", 0)) or 0))))
        except (TypeError, ValueError):
            offset_ms = 0
        points.append((
            offset_ms,
            _clamped_float(_field(item, "x", 0.5)),
            _clamped_float(_field(item, "y", 0.5)),
            _popup_easing(_field(item, "easing", "linear")),
        ))
    points.sort(key=lambda point: point[0])

    deduped: list[tuple[int, float, float, str]] = []
    for point in points:
        if deduped and deduped[-1][0] == point[0]:
            deduped[-1] = point
        else:
            deduped.append(point)
    return deduped


def popup_bubble_point(project: Project, popup: object, position_ms: int | None = None) -> tuple[float, float]:
    quadrant = str(_field(popup, "quadrant", "middle_middle") or "middle_middle")
    if quadrant == "custom":
        base_point = (
            _clamped_float(_field(popup, "x", 0.5)),
            _clamped_float(_field(popup, "y", 0.5)),
        )
    else:
        base_point = POPUP_BUBBLE_QUADRANT_POINTS.get(quadrant, POPUP_BUBBLE_QUADRANT_POINTS["middle_middle"])

    if not bool(_field(popup, "follow_motion", False)) or position_ms is None:
        return base_point

    motion_path = popup_bubble_motion_path(popup)
    if not motion_path:
        return base_point

    elapsed_ms = max(0, int(position_ms) - popup_bubble_time_ms(project, popup))
    previous_offset, previous_x, previous_y = 0, base_point[0], base_point[1]
    for offset_ms, x, y, easing in motion_path:
        if elapsed_ms <= offset_ms:
            if offset_ms <= previous_offset:
                return x, y
            ratio = (elapsed_ms - previous_offset) / (offset_ms - previous_offset)
            eased_ratio = _apply_easing(easing, ratio)
            return (
                max(0.0, min(1.0, previous_x + ((x - previous_x) * eased_ratio))),
                max(0.0, min(1.0, previous_y + ((y - previous_y) * eased_ratio))),
            )
        previous_offset, previous_x, previous_y = offset_ms, x, y
    return previous_x, previous_y
