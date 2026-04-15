from __future__ import annotations

from dataclasses import asdict, dataclass, field

from splitshot.domain.models import ImportedStageScore, Project, ScoreLetter, ScoreMark, ShotEvent
from splitshot.timeline.model import raw_time_ms


@dataclass(frozen=True, slots=True)
class ScoringPreset:
    id: str
    name: str
    sport: str
    mode: str
    description: str
    point_map: dict[str, float]
    penalty_label: str
    score_penalty_map: dict[str, float] = field(default_factory=dict)
    score_options: tuple[str, ...] = field(default_factory=tuple)
    penalty_fields: tuple["PenaltyField", ...] = field(default_factory=tuple)


@dataclass(frozen=True, slots=True)
class PenaltyField:
    id: str
    label: str
    value: float
    unit: str
    description: str = ""


USPSA_IPSC_PENALTIES = (
    PenaltyField("procedural_errors", "Procedural Error", 10, "points", "Usually -10 points each."),
    PenaltyField("manual_no_shoots", "Extra No-Shoot", 10, "points", "Use for no-shoots not tied to a shot marker."),
    PenaltyField("manual_misses", "Extra Miss", 10, "points", "Use for misses not tied to a shot marker."),
)

IDPA_PENALTIES = (
    PenaltyField("non_threats", "Non-Threat", 5, "seconds", "+5 seconds each."),
    PenaltyField("procedural_errors", "Procedural Error", 3, "seconds", "+3 seconds each."),
    PenaltyField("flagrant_penalties", "Flagrant Penalty", 10, "seconds", "+10 seconds each."),
    PenaltyField("failures_to_do_right", "Failure To Do Right", 20, "seconds", "+20 seconds each."),
    PenaltyField("finger_pe", "Finger PE", 3, "seconds", "+3 seconds each."),
)

STEEL_PENALTIES = (
    PenaltyField("steel_misses", "Plate Miss", 3, "seconds", "+3 seconds each."),
    PenaltyField("stop_plate_failures", "Stop Plate Failure", 30, "seconds", "30 second string."),
)

GPA_PENALTIES = (
    PenaltyField("non_threats", "Non-Threat", 5, "seconds", "+5 seconds each."),
    PenaltyField("steel_not_down", "Steel Not Down", 10, "seconds", "+10 seconds each."),
)


SCORING_PRESETS: dict[str, ScoringPreset] = {
    "uspsa_minor": ScoringPreset(
        id="uspsa_minor",
        name="USPSA Minor",
        sport="USPSA",
        mode="hit_factor",
        description="Minor PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "uspsa_major": ScoringPreset(
        id="uspsa_major",
        name="USPSA Major",
        sport="USPSA",
        mode="hit_factor",
        description="Major PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 4,
            ScoreLetter.D.value: 2,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.MU.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "ipsc_minor": ScoringPreset(
        id="ipsc_minor",
        name="IPSC Minor",
        sport="IPSC",
        mode="hit_factor",
        description="Minor PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 3,
            ScoreLetter.D.value: 1,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "ipsc_major": ScoringPreset(
        id="ipsc_major",
        name="IPSC Major",
        sport="IPSC",
        mode="hit_factor",
        description="Major PF HF scoring with A, C, D, M, and NS.",
        point_map={
            ScoreLetter.A.value: 5,
            ScoreLetter.C.value: 4,
            ScoreLetter.D.value: 2,
            ScoreLetter.M.value: 0,
            ScoreLetter.NS.value: 0,
            ScoreLetter.M_NS.value: 0,
        },
        score_penalty_map={
            ScoreLetter.M.value: 10,
            ScoreLetter.NS.value: 10,
            ScoreLetter.M_NS.value: 20,
        },
        score_options=(
            ScoreLetter.A.value,
            ScoreLetter.C.value,
            ScoreLetter.D.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=USPSA_IPSC_PENALTIES,
        penalty_label="Penalty points",
    ),
    "idpa_time_plus": ScoringPreset(
        id="idpa_time_plus",
        name="IDPA - Time Plus",
        sport="IDPA",
        mode="time_plus",
        description="Time-plus scoring with PD, M, NS, PE, FP, FTDR, and FPE.",
        point_map={
            ScoreLetter.DOWN_0.value: 0,
            ScoreLetter.DOWN_1.value: 1,
            ScoreLetter.DOWN_3.value: 3,
            ScoreLetter.M.value: 5,
            ScoreLetter.NS.value: 5,
            ScoreLetter.M_NS.value: 10,
        },
        score_options=(
            ScoreLetter.DOWN_0.value,
            ScoreLetter.DOWN_1.value,
            ScoreLetter.DOWN_3.value,
            ScoreLetter.M.value,
            ScoreLetter.NS.value,
            ScoreLetter.M_NS.value,
        ),
        penalty_fields=IDPA_PENALTIES,
        penalty_label="Penalty seconds",
    ),
    "steel_challenge": ScoringPreset(
        id="steel_challenge",
        name="Steel Challenge",
        sport="Steel Challenge",
        mode="time_plus",
        description="Time scoring with PM and SPF.",
        point_map={
            ScoreLetter.STEEL_HIT.value: 0,
            ScoreLetter.M.value: 3,
            ScoreLetter.STEEL_STOP_FAIL.value: 30,
        },
        score_options=(
            ScoreLetter.STEEL_HIT.value,
            ScoreLetter.M.value,
            ScoreLetter.STEEL_STOP_FAIL.value,
        ),
        penalty_fields=STEEL_PENALTIES,
        penalty_label="Penalty seconds",
    ),
    "gpa_time_plus": ScoringPreset(
        id="gpa_time_plus",
        name="GPA 0.5 Scoring",
        sport="GPA",
        mode="time_plus",
        description="Time-plus scoring with PD x0.5, M, NT, and SND.",
        point_map={
            ScoreLetter.GPA_0.value: 0,
            ScoreLetter.GPA_1.value: 0.5,
            ScoreLetter.GPA_3.value: 1.5,
            ScoreLetter.GPA_10.value: 5,
            ScoreLetter.M.value: 5,
        },
        score_options=(
            ScoreLetter.GPA_0.value,
            ScoreLetter.GPA_1.value,
            ScoreLetter.GPA_3.value,
            ScoreLetter.GPA_10.value,
            ScoreLetter.M.value,
        ),
        penalty_fields=GPA_PENALTIES,
        penalty_label="Penalty seconds",
    ),
}


def scoring_presets_for_api() -> list[dict[str, object]]:
    return [
        asdict(preset)
        for preset in SCORING_PRESETS.values()
        if preset.id != "gpa_time_plus"
    ]


def get_scoring_preset(ruleset: str) -> ScoringPreset:
    return SCORING_PRESETS.get(ruleset, SCORING_PRESETS["uspsa_minor"])


def apply_scoring_preset(project: Project, ruleset: str) -> None:
    preset = get_scoring_preset(ruleset)
    project.scoring.ruleset = preset.id
    project.scoring.point_map = dict(preset.point_map)
    valid_fields = {field.id for field in preset.penalty_fields}
    project.scoring.penalty_counts = {
        key: value
        for key, value in project.scoring.penalty_counts.items()
        if key in valid_fields
    }


def _shot_score_total(project: Project) -> float:
    if project.scoring.imported_stage is not None:
        return float(project.scoring.imported_stage.aggregate_points)
    return sum(
        project.scoring.point_map.get(shot.score.letter.value, 0)
        for shot in project.analysis.shots
        if shot.score is not None
    )


def _shot_penalty_total(project: Project, preset: ScoringPreset) -> float:
    if project.scoring.imported_stage is not None:
        return float(project.scoring.imported_stage.shot_penalties)
    return sum(
        preset.score_penalty_map.get(shot.score.letter.value, 0)
        + sum(
            field.value * max(0.0, float(shot.score.penalty_counts.get(field.id, 0)))
            for field in preset.penalty_fields
        )
        for shot in project.analysis.shots
        if shot.score is not None
    )


def _field_penalty_total(project: Project, preset: ScoringPreset) -> float:
    return sum(
        max(0.0, float(project.scoring.penalty_counts.get(field.id, 0))) * field.value
        for field in preset.penalty_fields
    )


def total_penalties(project: Project, preset: ScoringPreset | None = None) -> float:
    active_preset = preset or get_scoring_preset(project.scoring.ruleset)
    return (
        float(project.scoring.penalties)
        + _shot_penalty_total(project, active_preset)
        + _field_penalty_total(project, active_preset)
    )


def _format_overlay_stat(value: float | None, *, decimals: int = 2) -> str:
    if value is None:
        return ""
    rounded = round(float(value))
    if abs(float(value) - rounded) < 1e-9:
        return str(int(rounded))
    return f"{float(value):.{decimals}f}".rstrip("0").rstrip(".")


def format_imported_stage_overlay_text(imported_stage: ImportedStageScore | None) -> str:
    if imported_stage is None:
        return ""

    lines = ["Official"]
    if imported_stage.raw_seconds is not None:
        lines.append(f"Raw {float(imported_stage.raw_seconds):.2f}")

    if imported_stage.match_type == "idpa":
        lines.append(f"PD {_format_overlay_stat(imported_stage.aggregate_points)}")
        if imported_stage.final_time is not None:
            lines.append(f"Final {float(imported_stage.final_time):.2f}")
        return "\n".join(lines)

    points_value = (
        float(imported_stage.total_points)
        if imported_stage.total_points is not None
        else float(imported_stage.aggregate_points)
    )
    lines.append(f"Points {_format_overlay_stat(points_value)}")

    hit_factor_value = imported_stage.hit_factor
    if hit_factor_value is None and imported_stage.total_points is not None and imported_stage.raw_seconds:
        raw_seconds = float(imported_stage.raw_seconds)
        if raw_seconds > 0:
            hit_factor_value = max(0.0, float(imported_stage.total_points)) / raw_seconds
    if hit_factor_value is not None:
        lines.append(f"HF {float(hit_factor_value):.4f}")
    return "\n".join(lines)


def calculate_hit_factor(project: Project) -> float | None:
    preset = get_scoring_preset(project.scoring.ruleset)
    raw_ms = raw_time_ms(project)
    imported_stage = project.scoring.imported_stage
    raw_seconds = (
        float(imported_stage.raw_seconds)
        if imported_stage is not None and imported_stage.raw_seconds is not None
        else None if raw_ms is None else raw_ms / 1000.0
    )
    if (
        not project.scoring.enabled
        or preset.mode != "hit_factor"
        or raw_seconds is None
        or raw_seconds <= 0
    ):
        return None
    if imported_stage is not None:
        if imported_stage.total_points is not None:
            return max(0.0, float(imported_stage.total_points)) / raw_seconds
        if imported_stage.hit_factor is not None:
            return float(imported_stage.hit_factor)

    adjusted_points = max(0.0, _shot_score_total(project) - total_penalties(project, preset))
    if adjusted_points == 0:
        return 0.0
    return adjusted_points / raw_seconds


def calculate_scoring_summary(project: Project) -> dict[str, object]:
    preset = get_scoring_preset(project.scoring.ruleset)
    raw_ms = raw_time_ms(project)
    imported_stage = project.scoring.imported_stage
    raw_seconds = (
        float(imported_stage.raw_seconds)
        if imported_stage is not None and imported_stage.raw_seconds is not None
        else None if raw_ms is None else raw_ms / 1000.0
    )
    shot_points = _shot_score_total(project)
    shot_penalties = _shot_penalty_total(project, preset)
    field_penalties = _field_penalty_total(project, preset)
    total_penalty_value = total_penalties(project, preset)
    hit_factor_value = calculate_hit_factor(project)
    summary: dict[str, object] = {
        "enabled": project.scoring.enabled,
        "ruleset": preset.id,
        "ruleset_name": preset.name,
        "sport": preset.sport,
        "mode": preset.mode,
        "description": preset.description,
        "penalty_label": preset.penalty_label,
        "score_options": list(preset.score_options),
        "score_values": dict(preset.point_map),
        "score_penalties": dict(preset.score_penalty_map),
        "penalty_fields": [
            {**asdict(field), "count": project.scoring.penalty_counts.get(field.id, 0)}
            for field in preset.penalty_fields
        ],
        "raw_seconds": raw_seconds,
        "shot_points": shot_points,
        "penalties": project.scoring.penalties,
        "shot_penalties": shot_penalties,
        "field_penalties": field_penalties,
        "total_penalties": total_penalty_value,
        "hit_factor": hit_factor_value,
        "final_time": None,
        "imported_stage": None if imported_stage is None else asdict(imported_stage),
        "imported_overlay_text": format_imported_stage_overlay_text(imported_stage),
        "display_label": "Hit Factor" if preset.mode == "hit_factor" else "Final",
        "display_value": "--",
    }
    if not project.scoring.enabled or raw_seconds is None:
        return summary
    if preset.mode == "hit_factor":
        value = hit_factor_value
        summary["display_value"] = "--" if value is None else f"{float(value):.2f}"
        return summary

    imported_final_time = (
        float(imported_stage.final_time)
        if imported_stage is not None and imported_stage.final_time is not None
        else None
    )
    final_time = imported_final_time if imported_final_time is not None else max(0.0, raw_seconds + shot_points + total_penalty_value)
    summary["final_time"] = final_time
    summary["display_value"] = f"{final_time:.2f}"
    return summary


def assign_score(
    shot: ShotEvent,
    letter: ScoreLetter | None = None,
    penalty_counts: dict[str, float] | None = None,
) -> None:
    if shot.score is None:
        shot.score = ScoreMark(letter=letter or ScoreLetter.A)
    elif letter is not None:
        shot.score.letter = letter
    if penalty_counts is not None and shot.score is not None:
        shot.score.penalty_counts = {
            str(key): max(0.0, float(value))
            for key, value in penalty_counts.items()
            if max(0.0, float(value)) > 0
        }


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
